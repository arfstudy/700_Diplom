from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

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
