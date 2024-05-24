import re

from rest_framework import status

from apiauth.services import complete_user_conversion, delete_token, get_received_keys
from users.emails import describe_keys_verify_result, verify_received_keys


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

    actions = ['login', 'token', 'register']
    data, is_verify = verify_received_keys(request, key64, token, actions)
    if not is_verify:
        # Проверяет, что удалось распознать пользователя и его действие.
        context = {key: data[key] for key in ['process_err', 'user_err'] if key in data.keys()}
        if context:
            context['condition'] = status.HTTP_400_BAD_REQUEST
            return context

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
