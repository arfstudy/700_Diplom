from rest_framework.authtoken.models import Token


def get_or_create_token(user):
    """ Возвращает токен пользователя или создаёт, если его нет.
    """
    return Token.objects.get_or_create(user=user)    # (token, created)
