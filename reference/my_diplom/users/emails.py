from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from users.services import decoding_key64

User = get_user_model()


def send_verify_email(request, user, process, message_template):
    """ Отправляет контрольное письмо с ключом и токеном,
        для подтверждения электронной почты пользователя.
    """
    use_https = False
    current_site = get_current_site(request)
    uid64 = urlsafe_base64_encode(force_bytes(user.pk))
    context = {  # данные для добавления в текст письма.
        "user": user,
        "protocol": "https" if use_https else "http",
        "domain": current_site.domain,
        "key64": process + uid64,
        "token": token_generator.make_token(user),
    }
    message = render_to_string(template_name=message_template, context=context)
    letter = EmailMessage(
        subject='Подтверждение почты',
        body=message,
        from_email=settings.EMAIL_HOST_USER,  # по умолчанию
        to=[user.email],
    )
    letter.send(fail_silently=False)  # fail_silently=False - по умолчанию

    return


def verify_received_keys(request, key64, token, actions):
    """ Выполняет проверку полученного ключа и токена из контрольного письма пользователя.
    """
    data, is_success = decoding_key64(request, key64, actions)
    if not is_success:
        return data, False

    user = data['user']
    is_verify = token_generator.check_token(user, token)
    if is_verify:
        update_fields_list = []
        if data['process'] == 'register':
            user.is_active = True
            update_fields_list.append('is_active')
        user.email_verify = True
        update_fields_list.append('email_verify')
        user.save(update_fields=update_fields_list)

    return data, is_verify


def describe_keys_verify_result(data, is_verify):
    """ Описывает результат проверки полученных ключей.
    """
    msg1 = ['Ваша электронная почта подтверждена.']
    msg2 = 'Вы успешно вошли в систему.'
    if is_verify:
        if data['process'] == 'register':
            msg2 = 'Вы успешно зарегистрированы.'
        elif data['process'] == 'update':
            msg2 = 'Ваши данные успешно изменены.'
    else:
        msg1 = [('Ссылка для подтверждения почты оказалась недействительной, возможно, потому'
                 ', что она уже использовалась.')]
        if data['process'] in ['login', 'register']:
            msg2 = 'Попробуйте ещё раз.'
        elif data['process'] == 'update':
            msg2 = 'Все изменения отменены.'
            if 'is_restore' in data.keys() and not data['is_restore']:
                msg1 = ['Внимание! Возможно, что Ваши данные изменились по ошибке.', ('Если Вы внесли какие-либо '
                        'изменения в поля формы, то они сохранились в БД, несмотря на то, что почта оказалась '
                         'недействительной.')]
                msg2 = 'Вам необходимо обратиться к администратору сайта.'

    msg1.append(msg2)
    data[data['process']] = msg1
    return data
