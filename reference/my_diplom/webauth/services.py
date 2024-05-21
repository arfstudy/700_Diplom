from django.contrib.auth import login

from users.emails import verify_received_keys, describe_keys_verify_result


def verify_received_email(request, key64, token):
    """ Выполняет подтверждение электронной почты на основании ключа и токена
        из ссылки из контрольного письма пользователя.
    """
    actions = ['login']
    data, is_verify = verify_received_keys(request, key64, token, actions)

    data = describe_keys_verify_result(data, is_verify)

    context = {'msg': data[data['process']]}
    if is_verify:
        context['header'] = 'Электронная почта подтверждена'
        login(request, data['user'])
    else:
        context['header'] = 'Ошибка подтверждения почты'

    return context
