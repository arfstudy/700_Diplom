from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
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


def delete_tentative_user(user):
    """ Удаляет временного пользователя.
    """
    try:
        user.delete()
    except:
        return False

    return True


def get_user_fields_dict(user, changed_list=None, FormClass=None):
    """ Получает словарь из полей пользователя 'user'.
        Класс формы 'FormClass' передаю в функцию в виде параметра, чтобы избежать перекрёстного импорта
        между модулями 'reference/my_diplom/users/services.py' и 'reference/my_diplom/users/forms.py'.
    """
    if changed_list is None:
        form = FormClass()
        changed_list = form.Meta.fields
    fields_dict = {}
    for key in changed_list:
        fields_dict[key] = getattr(user, key, "")    # Здесь 'key: str'.

    return fields_dict


def save_old_user(user, changed_list):
    """ Сохраняет значения полей пользователя, полученные из списка 'changed_list' (подлежащие изменению).
    """
    user_fields = get_user_fields_dict(user, changed_list=changed_list)
    user_fields['changed_data'] = changed_list
    user_fields['pk'] = user.pk

    return user_fields


def is_restore_old_user(old_user_fields, user):
    """ Восстанавливает у пользователя его старое содержимое полей.
        Индекс в таблице БД 'pk', список изменённых полей 'changed_data' и сами
        значения этих полей получает из словаря 'old_user_fields'.
        Возвращает признак успешности выполненной операции.
    """
    changed_data = old_user_fields.pop('changed_data', [])
    pk = old_user_fields.pop('pk', 0)
    if not (changed_data and user.pk == pk):
        return False

    for key in changed_data:
        setattr(user, key, old_user_fields[key])
    user.save(update_fields=changed_data)
    return True


@transaction.atomic
def delete_user(user):
    """ Удаляет пользователя.
        Находит пользователя 'user' и, якобы, "удаляет" его,
        задав атрибутам 'is_active' и 'email_verify' значение 'False'.
        Если пользователь является менеджером магазина, то "увольняется".
    """
    if hasattr(user, 'seller'):
        user.seller = None
    if hasattr(user, 'buyer'):
        user.buyer = None

    user.is_active = False
    user.email_verify = False
    user.save()
    return
