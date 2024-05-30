from rest_framework import status

from apiauth.services import complete_user_conversion, get_received_keys
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


def verify_received_email(request, old_user_values):
    """ Выполняет подтверждение электронной почты на основании ключа и токена,
        полученных от пользователя, и подготавливает соответствующий ответ.
    """
    key64, token, errors = get_received_keys(request)
    if errors:
        errors['condition'] = status.HTTP_400_BAD_REQUEST
        return errors

    actions = ['login']
    data, is_verify = verify_received_keys(request, key64, token, actions)
    if not is_verify:
        # Проверяет, что удалось распознать пользователя и его действие.
        context = {key: data[key] for key in ['process_err', 'user_err'] if key in data.keys()}
        if context:
            context['condition'] = status.HTTP_400_BAD_REQUEST
            return context

    data = describe_keys_verify_result(data, is_verify)

    return complete_user_conversion(data, is_verify)
