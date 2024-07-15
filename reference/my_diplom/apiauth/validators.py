import re

from rest_framework import status

from apiauth.services import (complete_user_conversion, delete_token, get_received_keys, exclude_invalid_fields,
                              get_choice_fields, check_not_null_and_convert, change_residue, save_password)
from users.emails import describe_keys_verify_result, verify_received_keys
from users.services import is_restore_old_user


def validate_required_fields(incoming_data, fields):
    """ Проверяет присутствие обязательных полей и наличие записей в них.
    """
    errors = {}
    data_keys = incoming_data.keys()
    for field in fields:
        if field not in data_keys:
            errors[field] = ['Отсутствует обязательное поле.']
        else:
            if incoming_data[field] == "":
                errors[field] = ['Данное поле не может быть пустым.']
            elif incoming_data[field].replace(" ", "") == "":
                errors[field] = ['Данное поле не может состоять из одних пробелов.']

    return errors


def verify_received_email(request, old_user_values, model_serializer):
    """ Выполняет подтверждение электронной почты на основании ключа и токена,
        полученных от пользователя, и подготавливает соответствующий ответ.
    """
    key64, token, errors = get_received_keys(request)
    if errors:
        errors['condition'] = status.HTTP_400_BAD_REQUEST
        return errors

    actions = ['login', 'token', 'register', 'update']
    data, is_verify = verify_received_keys(request, key64, token, actions)
    is_restore = True
    if not is_verify:
        # Проверяет, что удалось распознать пользователя и его действие.
        context = {key: data[key] for key in ['process_err', 'user_err'] if key in data.keys()}
        if context:
            context['condition'] = status.HTTP_400_BAD_REQUEST
            return context

        # Восстанавливает старые значения пользователя, если, при редактировании, почта не подтвердилась.
        if data['process'] == 'update' and 'user' in data.keys():
            is_restore = is_restore_old_user(old_user_values, data['user'])
            if is_restore:
                data['user'].email_verify = True
                data['user'].save(update_fields='email_verify')
    old_user_values.clear()
    data['is_restore'] = is_restore

    is_reassigned, old_process = False, ''
    if data['process'] == 'token':
        is_reassigned, old_process = True, data['process']
        data['process'] = 'login'
        if hasattr(data['user'], 'auth_token') and data['user'].auth_token is not None:
            delete_token(data['user'])

    data = describe_keys_verify_result(data, is_verify)

    context = complete_user_conversion(data, is_verify, model_serializer)
    if is_reassigned:
        context = {old_process: context[data['process']], **context}
        del context[data['process']]
        if is_verify and old_process == 'token':
            context[old_process][1] = 'Ваш токен успешно обновлён.'

    return context


def is_validate_text(text, pattern):
    """ Определяет принадлежность символов содержимого поля заданному алфавиту.
        (После удаления из содержимого поля всех символов заданного алфавита должна остаться пустая строка.)
    """
    result = re.sub(pattern=pattern, repl="", string=text, flags=re.IGNORECASE)
    return bool(result is not None and len(result) == 0)


def validate_name(name, alphabets):
    """ Определяет принадлежность символов содержимого поля к одному из алфавитов.
    """
    for alph_key in alphabets.keys():
        if is_validate_text(text=name, pattern=alphabets[alph_key]):
            return alph_key
    return 'None'


def validate_names(names, attributes_list, alphabets, user_obj=None):
    """ Проверяет имена на содержание символов одного и того же алфавита.
        Если заданы не все поля (при редактировании), то сравнивает ещё
        с одним полем из Базы Данных.
    """
    is_valid, other = True, attributes_list.copy()
    language_name = language_field = 'None'
    errors = {'warning': 'В вашем имени и фамилии должны быть только русские или только латинские буквы.'}
    for field_name in attributes_list:
        if field_name in names.keys():
            other.remove(field_name)
            alph = validate_name(names[field_name], alphabets)
            if alph != 'None':
                if language_name == 'None':
                    language_name, language_field = alph, field_name
                else:
                    if alph != language_name:
                        is_valid = False
                        errors['validate_names'] = f'Алфавиты полей `{language_field}` и `{field_name}` не совпадают.'
                        break
            else:
                is_valid, errors[field_name] = False, 'Буквы из разных алфавитов или недопустимые символы.'

    if user_obj is not None and is_valid and other:
        for field in other:
            alph = validate_name(getattr(user_obj, field, 'ЯZ'), alphabets)
            if alph != 'None':
                if alph != language_name:
                    is_valid = False
                    errors['validate_names'] = f'Алфавиты полей `{language_field}` и `{field}` не совпадают.'
            else:
                is_valid, errors[field] = False, 'Буквы из разных алфавитов или недопустимые символы.'
            break

    return errors, is_valid


def validate_names_fields(attrs, user_obj=None):
    """ Проверяет имена на содержание символов одного из заданных алфавитов.
    """
    alphabets = {                                   # Можно изменить, например добавить ещё какой-нибудь алфавит.
        'ru_pattern': r'[а-яё ]+',    # Для русского алфавита.
        'lat_pattern': r'[a-z ]+',    # Для латинского алфавита.
    }
    attributes_list = ['first_name', 'last_name']    # Можно изменить, например добавить ещё 'sur_name'.
    for field in attributes_list:
        if field in attrs.keys():

            errors, is_valid = validate_names(attrs, attributes_list, alphabets, user_obj)

            if is_valid:
                for attribute in attributes_list:
                    if attribute in attrs.keys():
                        attrs[attribute] = attrs[attribute].title()

            return attrs, is_valid, errors

    return attrs, True, {'warning': 'Нет полей для проверки.'}


def validate_choice_fields(data, obj):
    """ Находит поля Choice-типа и делает проверку.
    """
    choice_errors = dict()
    choice_fields = get_choice_fields(obj)
    for field in choice_fields.keys():
        if field in data.keys():
            data[field], errors_msg = check_not_null_and_convert(data, field, data[field], choice_fields[field],
                                                                 validate_required_fields)
            if errors_msg:
                choice_errors[field] = errors_msg

    return data, choice_errors


def compare_with_db(check_form, data, action, obj):
    """ Проверяет на совпадение переданных значений со значениями из БД.
        (Проверка выполняется при помощи формы Django.)
        Для PATCH-запроса останутся только те поля, которые, действительно, несут какие-то изменения.
        Для PUT-запроса вернутся все поля объекта, даже те (из необязательных), которые небыли переданы.
        Эти поля получат пустые значения или значения по умолчанию.
    """
    null_fields = []
    res = dict()
    if check_form.has_changed():
        changed_count = len(check_form.changed_data)
        for field in check_form.changed_data:
            if field in data.keys():
                res[field] = data[field]
            else:
                null_fields.append(field)
                changed_count -= 1
        if changed_count > 0:
            # Для PUT-запроса пропущенные поля заполняем пустыми значениями или значениями по умолчанию.
            if action in ['put', 'update']:
                res = change_residue(data, obj, null_fields)

            return res, {}

    return res, {'errors': ['Вы не передали ничего нового.', 'Выполнение прервано.']}


def pre_check_incoming_fields(data, required_fields, additional_fields, action, obj, form_class, obj_name='объекта'):
    """ Предварительно проверяет полученные поля на корректность.
    """
    action = action.lower()
    errors = dict()
    fields_content = []
    put_msg = dict()
    # 1. Отсеиваем поля, которые не входят в допустимые.
    res, invalid_fields = exclude_invalid_fields(data, {*required_fields, *additional_fields}, obj)

    # 2. Проверяем Choice-поля и подготавливаем к сохранению.
    res, choice_errors = validate_choice_fields(res, obj)

    # 3. Проверяем обязательные поля. Ошибки: пропущено или пусто.
    if action in ['post', 'create', 'put', 'update']:
        errors = validate_required_fields(res, required_fields)
        if errors:
            warning = {'warning': [f'Обязательные поля: `{"` `".join(required_fields)}`.',
                                   f'Дополнительные поля: `{"` `".join(additional_fields)}`.']}
            if action in ['put', 'update']:
                put_msg = {'PUT': [f'Для частичного изменения {obj_name} воспользуйтесь PATCH-запросом.']}
            return res, errors, choice_errors, warning, {**put_msg, **invalid_fields}

    # 4. Проверяем наличие хотя бы одного запланированного изменения.
    if action in ['put', 'update', 'patch', 'partial_update']:
        check_form = form_class(data=res, instance=obj)
        res, errors = compare_with_db(check_form, res, action, obj)
        if errors:
            if action in ['put', 'update']:
                fields_content = [f'Обязательные поля: `{"` `".join(required_fields)}`.',
                                  f'Дополнительные поля: `{"` `".join(additional_fields)}`.']
            else:
                fields_content = [f'Допустимые поля: `{"` `".join({*required_fields, *additional_fields})}`.']

    warning = {'warning': fields_content} if fields_content else {}
    return res, errors, choice_errors, warning, {**put_msg, **invalid_fields}


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
