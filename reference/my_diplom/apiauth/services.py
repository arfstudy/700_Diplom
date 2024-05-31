from rest_framework import status
from rest_framework.authtoken.models import Token

from users.emails import verify_received_keys
from users.services import delete_tentative_user


def get_or_create_token(user):
    """ Возвращает токен пользователя или создаёт, если его нет.
    """
    return Token.objects.get_or_create(user=user)    # (token, created)


def delete_token(user):
    """ Удаляет токен.
    """
    try:
        user.auth_token.delete()
    except:
        return False

    return True


def save_password(user, password):
    """ Сохраняет пароль.
    """
    try:
        user.set_password(password)
        user.save(update_fields=['password'])
    except:
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


def complete_user_conversion(data, is_verify, model_serializer):
    """ Заканчивает необходимые преобразования пользователя в зависимости от результата подтверждения почты.
    """
    context = {data['process']: data[data['process']] }
    if is_verify:
        context['condition'] = status.HTTP_200_OK
        if data['process'] in ['login', 'register']:
            if data['process'] == 'register':
                context['condition'] = status.HTTP_201_CREATED
            token, created = get_or_create_token(data['user'])
            if token is not None:
                context['token_key'] = token.key
                if data['process'] == 'login':
                    context['user'] = f'{data["user"]}'
                elif data['process'] == 'register':
                    context['user'] = model_serializer(instance=data["user"]).data
            else:
                context['token_err'] = 'Ошибка. Не удалось получить токен.'
                context['condition'] = status.HTTP_400_BAD_REQUEST
        elif data['process'] == 'update':
            context['user'] = model_serializer(instance=data["user"]).data
    else:
        context[data['process']][0] = 'Ошибка подтверждения почты.'
        context['condition'] = status.HTTP_400_BAD_REQUEST
        if data['process'] == 'register' and 'user' in data.keys():
            is_delete = delete_tentative_user(data['user'])
            if not is_delete:
                context['register_err'] = 'Ошибка. Информация о временном пользователе осталась в Базе Данных.'

    return context


def get_choice_fields(obj):
    """ Находит поля перечисляемого типа в модели объекта 'obj'.
    """
    choice_fields = []
    obj_parent = obj.__class__
    for field in obj.__dict__:
        if hasattr(obj_parent, field):
            if getattr(obj_parent, field).field.choices is not None:
                choice_fields.append(field)

    return choice_fields


def verify_password_reset_keys(request):
    """ Выполняет проверку полученного ключа и токена и присваивает новый пароль.
    """
    key64, token, errors = get_received_keys(request)
    if errors:
        errors['condition'] = status.HTTP_400_BAD_REQUEST
        return errors

    actions = ['reset']
    data, is_verify = verify_received_keys(request, key64, token, actions)
    if is_verify:
        save_password(data['user'], request.data['password1'])
        context = {'reset': ['Ваш пароль сохранён.', 'Теперь вы можете войти.'], 'condition': status.HTTP_200_OK}
        delete_token(data['user'])

    else:
        # Определяет, что не удалось распознать пользователя и его действие (ключ Key64) или токен (ключ Token).
        context = {key: data[key] for key in ['process_err', 'user_err'] if key in data.keys()}
        if not context:
            context = {'reset': ['Ошибка подтверждения ключей.', 'Попробуйте ещё раз.']}
        context['condition'] = status.HTTP_400_BAD_REQUEST

    return context
