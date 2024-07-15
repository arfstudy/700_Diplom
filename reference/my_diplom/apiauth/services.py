from django.db.models import enums
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

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
    except TypeError:
        return False

    return True


def save_password(user, password):
    """ Сохраняет пароль.
    """
    try:
        user.set_password(password)
        user.save(update_fields=['password'])
    except Exception:
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
    context = {data['process']: data[data['process']]}
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


def exclude_invalid_fields(data, all_fields, obj):
    """ Отсеивает недопустимые поля.
    """
    attr = data.copy()
    ignored = dict()
    for field in data.keys():
        if hasattr(obj, field):
            if field not in all_fields:
                ignored[field] = ['Это поле не подлежит изменению.']
                del attr[field]
        else:
            ignored[field] = ['Неизвестное поле. Проигнорировано.']
            del attr[field]

    return attr, ignored


def get_choice_fields(obj):
    """ Находит поля перечисляемого типа в модели объекта 'obj'.
        Находит название типа.
        Возвращает словарь, название поля и его тип.
    """
    # 1. В объекте 'obj' находим названия полей choices-типа.
    choice_fields = dict()
    obj_class = obj.__class__
    for field in obj.__dict__:
        if hasattr(obj_class, field) and getattr(obj_class, field).field.choices is not None:
            choice_fields[field] = getattr(obj_class, field).field.choices
    if not choice_fields:
        return dict()

    # 2. В классе 'obj_class' находим ChoicesType-типы.
    choices_types = []
    choices_count = len(choice_fields)
    for e in dir(obj_class):
        if choices_count == 0:
            break
        if isinstance(getattr(obj_class, e), enums.ChoicesType):
            choices_types.append(getattr(obj_class, e))
            choices_count -= 1
    if len(choices_types) != len(choice_fields):
        raise ValidationError(f'Найдены не все типы для Choices-полей.\n{choice_fields=}\n{choices_types=}')

    # 3. Определяет соответствие полей 'choice_fields' имеющимся типам 'ChoicesType'.
    for key in choice_fields.keys():
        flag = False
        for choices_type in choices_types[:]:
            for name in choices_type.names:
                ch_name = getattr(choices_type, name, None)
                if bool(ch_name and (ch_name.value, ch_name.label) in choice_fields[key]):
                    choice_fields[key] = choices_type
                    choices_types.remove(choices_type)
                    flag = True
                break
            if flag:
                break
    if choices_types:
        raise ValidationError('Не для всех Choices-полей определены соответствующие типы.'
                              + f'\n{choice_fields=}\n{choices_types=}')

    return choice_fields


def verify_choices(value, choices_type):
    """ Проверяет, что полученное значение является элементом перечисляемого типа.
        Оно может быть именем значения, самим значением или человекочитаемым пояснением.
        (Синтаксис значения регистронезависимый.)
    """
    errors = dict()
    choice_names = choices_type.names
    if (
            value.upper() in choice_names
            or value.upper() in choices_type.values
            or value.capitalize() in choices_type.labels
    ):
        for name in choice_names:
            ch_name = getattr(choices_type, name, None)
            if bool(ch_name and
                    (value.upper() == name or value.upper() == ch_name.value or value.capitalize() == ch_name.label)):
                value = ch_name.value
                break
    else:
        acceptable = [e for z in zip(choice_names, choices_type.values, choices_type.labels) for e in z]
        msg = '`, `'.join(acceptable[:-1]) + '` или `' + acceptable[-1]
        errors = {'errors': f'Допустимые варианты только `{msg}`. (Регистронезависимые).'}

    return value, errors


def check_not_null_and_convert(validated_data, field, value, choices_type, validate_fun):
    """ Проверяет полученное значение choice-параметра.
    """
    # Проверяем, чтобы choice-поле не было пустым.
    errors = validate_fun(validated_data, [field])
    if errors:
        return value, ([errors[field], ' Задайте допустимое значение или не передавайте это'
                       + ' поле совсем, чтобы установилось значение по умолчанию.'])

    # Проверяем, чтобы choice-поле содержало допустимое значение.
    value, errors = verify_choices(value, choices_type)
    if errors:
        return value, [errors['errors']]

    return value, []


def change_residue(data, obj, null_fields):
    """ Заполняет пропущенные поля объекта пустыми значениями или значениями по умолчанию (для PUT-запроса).
    """
    res = data.copy()
    for field in null_fields:
        f = getattr(obj.__class__, field).field
        if f.null:
            res[field] = None
        elif f.default:
            res[field] = f.default
        else:
            res[field] = 'Ошибка. Требуется заполнять.'

    return res
