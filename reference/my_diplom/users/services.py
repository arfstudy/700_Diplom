from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_decode

User = get_user_model()


def get_user(param):
    """ Получает пользователя 'user' по ключам 'pk' или 'email'.
    """
    try:
        user = User.objects.get(pk=param)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
        pass
    else:
        return user
    try:
        user = User.objects.get(email=param)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
        return None

    return user


def get_user_uidb64(uidb64):
    """ Получает пользователя 'user' по ключу 'uidb64'.
    """
    #   urlsafe_base64_decode() decodes to bytestring
    try:
        user_id = urlsafe_base64_decode(uidb64).decode()
    except (UnicodeDecodeError, TypeError, ValueError, OverflowError, ValidationError):
        return None

    return get_user(param=user_id)


def decoding_key64(request, key_64, actions):
    """ Выделяет действие, вызвавшее отправку электронного письма.
        Определяет пользователя, по ключу.
    """
    process, key64 = 'process_err', 'key64'
    for act in actions:
        if key_64.startswith(act):
            process = act
            key64 = key_64.replace(act, '')
            break

    data = {'process': process}
    if process == 'process_err':
        data['process_err'] = 'Ваше действие нераспознано (неправильный ключ Key64).'
        data['user_err'] = 'Определение пользователя прервано (неправильный ключ Key64).'
        return data, False

    user = get_user_uidb64(key64)
    if user is None:
        data['user_err'] = 'Вас не удалось идентифицировать (неправильный ключ Key64).'
        return data, False

    data['user'] = user
    return data, True
