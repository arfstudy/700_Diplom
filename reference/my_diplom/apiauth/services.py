from rest_framework import status
from rest_framework.authtoken.models import Token


def get_or_create_token(user):
    """ Возвращает токен пользователя или создаёт, если его нет.
    """
    return Token.objects.get_or_create(user=user)    # (token, created)


def delete_token(user):
    """ Удаляет токен.
    """
    try:
        user.auth_token.delete()
    except TypeError:
        return False

    return True


def get_token_key(request, key_name):
    """ Выделяет ключ из полученного выражения.
    """
    key = key_name.lower()
    val = request.data.get(key, 'None')
    if val == 'None':
        return {key: f"Вы не передали ключ `{key}`."}, False

    res = val.split()
    if len(res) == 1:
        return {key: f"Неверный синтаксис ключа. Должно быть `{key_name} <key_value>`."}, False

    if len(res) > 2:
        return {key: f"Ключ `{key_name}` не должен содержать пробелы."}, False

    return {key: res[1]}, True


def get_received_keys(request):
    """ Выделяет ключи из полученного запроса.
    """
    errors = {}
    key64 = token = ''
    res, is_get = get_token_key(request, 'Key64')
    if is_get:
        key64 = res['key64']
    else:
        errors['key64'] = res['key64']

    res, is_get = get_token_key(request, 'Token')
    if is_get and errors == {}:
        token = res['token']
    elif not is_get:
        errors['token'] = res['token']

    return key64, token, errors


def complete_user_conversion(data, is_verify):
    """ Заканчивает необходимые преобразования пользователя в зависимости от результата подтверждения почты.
    """
    context = {data['process']: data[data['process']]}
    if is_verify:
        context['condition'] = status.HTTP_200_OK
        if data['process'] in ['login']:
            token, created = get_or_create_token(data['user'])
            if token is not None:
                context['token_key'] = token.key
                context['user'] = f'{data["user"]}'
            else:
                context['token_err'] = 'Ошибка. Не удалось получить токен.'
                context['condition'] = status.HTTP_417_EXPECTATION_FAILED
    else:
        context[data['process']][0] = 'Ошибка подтверждения почты.'
        context['condition'] = status.HTTP_400_BAD_REQUEST

    return context
