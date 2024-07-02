from django.contrib.auth import login

from users.emails import verify_received_keys, describe_keys_verify_result
from users.services import delete_tentative_user, is_restore_old_user


def verify_received_email(request, key64, token, old_user_values):
    """ Выполняет подтверждение электронной почты на основании ключа и токена из ссылки,
        из контрольного письма пользователя, и подготавливает соответствующий ответ.
    """
    actions = ['login', 'register', 'update']
    data, is_verify = verify_received_keys(request, key64, token, actions)

    # Восстанавливает старые значения пользователя.
    is_restore = False
    if not is_verify and data['process'] == 'update' and 'user' in data.keys():
        is_restore = is_restore_old_user(old_user_values, data['user'])
    old_user_values.clear()
    data['is_restore'] = is_restore

    data = describe_keys_verify_result(data, is_verify)

    context = {'msg': data[data['process']], 'not_verify': not is_verify, 'is_register': data['process'] == 'register',
               'is_update': data['process'] == 'update', 'is_restore': is_restore}
    if is_verify:
        context['header'] = 'Электронная почта подтверждена'
        if data['process'] in ['login', 'register']:
            login(request, data['user'])
    else:
        context['header'] = 'Ошибка подтверждения почты'
        if data['process'] == 'register' and 'user' in data.keys():
            delete_tentative_user(data['user'])

    return context
