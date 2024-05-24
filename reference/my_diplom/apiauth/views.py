from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.exceptions import NotFound, AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apiauth.services import get_or_create_token, verify_received_email
from apiauth.validators import validate_required_fields
from users.emails import send_verify_email
from users.services import get_user

OLD_VALUES = {}


class UserLoginView(APIView):
    """ Класс для выполнения входа в систему.
    """
    message_template = 'registration/api_email_verify.html'

    def process_login_parameters(self, request, process):
        """ Проверяет полученные параметры и определяет пользователя.
        """
        # Проверяем обязательные аргументы.
        required_fields = {'email', 'password'}
        errors = validate_required_fields(request.data, required_fields)
        if errors:
            raise ValidationError({'detail': errors})  # Статус ошибки - status=status.HTTP_400_BAD_REQUEST

        email = request.data.get('email')
        tentative_user = get_user(email)
        if tentative_user is None:
            # User matching query does not exist. Статус ошибки - status=status.HTTP_404_NOT_FOUND
            raise NotFound('Пользователь с такой электронной почтой не найден.')

        if not tentative_user.is_active:
            # This user has been deleted. Contact the site administrator.
            raise NotFound('Этот пользователь был удалён. Обратитесь к администратору сайта.')

        password = request.data.get('password')
        user = authenticate(request, username=email, password=password)
        if user is None:
            # Please enter the correct email address and password. Note that both fields may be case-sensitive.
            # Статус ошибки - status=status.HTTP_401_UNAUTHORIZED
            raise AuthenticationFailed(
                ('Пожалуйста введите корректные адрес электронной почты и пароль. Обратите внимание, '
                 'что оба поля могут зависеть от регистра символов.')
            )

        # Если электронная почта неподтверждённая, то отправляет письмо пользователю.
        if not user.email_verify:
            send_verify_email(request, tentative_user, process, self.message_template)
            return {process: 'Требуется дополнительное действие.',
                    'email': 'Необходимо подтвердить электронную почту. Мы отправили Вам письмо с инструкциями.'}

        return {'user': user}

    def post(self, request):
        """ Выполняет вход в систему.
        """
        data = self.process_login_parameters(request, 'login')
        if 'user' not in data.keys():
            return Response(data=data)

        content = {'login': 'Вы успешно вошли в систему.'}
        if hasattr(data['user'], 'auth_token') and data['user'].auth_token is not None:
            content['login'] = 'Вы уже находитесь в системе.'  # You are logged in the system.

        token, created = get_or_create_token(user=data['user'])
        return Response(data={**content, 'token_key': token.key, 'user': f'{data["user"]}'})


class EmailVerifyView(APIView):
    """ Класс для подтверждения email.
    """

    @staticmethod
    def post(request):
        """ Проверяет корректность ключей, полученных от пользователя.
        """
        global OLD_VALUES
        # Проверяем обязательные аргументы.
        required_fields = {'key64', 'token'}
        errors = validate_required_fields(request.data, required_fields)
        if errors:
            raise ValidationError({'detail': errors})

        data = verify_received_email(request, OLD_VALUES)

        condition = data.pop('condition', status.HTTP_200_OK)
        return Response(data=data, status=condition)
