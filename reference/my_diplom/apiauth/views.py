from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import status
from rest_framework.exceptions import NotFound, AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apiauth.serializers import UserSerializer
from apiauth.services import get_or_create_token, delete_token, save_password
from apiauth.validators import validate_required_fields, verify_received_email
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

        data = verify_received_email(request, OLD_VALUES, UserSerializer)

        condition = data.pop('condition', status.HTTP_200_OK)
        return Response(data=data, status=condition)


class UserLogoutView(APIView):
    """ Класс для выполнения выхода из системы.
    """

    @staticmethod
    def post(request):
        """ Удаляет токен.
        """
        if delete_token(request.user):
            return Response(data={'logout': 'Успешный выход из системы.'}, status=status.HTTP_204_NO_CONTENT)

        return Response(data={'logout': 'Ошибка удаления токена.'}, status=status.HTTP_417_EXPECTATION_FAILED)


class NewTokenCreateView(UserLoginView):
    """ Класс для обновления токена.
    """

    def post(self, request):
        """ Обновляет скомпрометированный токен.
        """
        data = self.process_login_parameters(request, 'token')
        if 'user' not in data.keys():
            return Response(data=data)

        if hasattr(data['user'], 'auth_token') and data['user'].auth_token is not None:
            # Удаляет старый токен.
            delete_token(data['user'])

        token, created = get_or_create_token(user=data['user'])
        return Response(data={'token': 'Ваш токен успешно обновлён.', 'token_key': token.key})


class UserRegisterView(APIView):
    """ Класс для создания нового пользователя.
    """
    message_template = 'registration/api_email_verify.html'

    def post(self, request):
        """ Создаёт нового пользователя.
        """
        # Проверяем обязательные аргументы.
        required_fields = {'first_name', 'last_name', 'email', 'password1', 'password2'}
        errors = validate_required_fields(request.data, required_fields)
        if errors:
            raise ValidationError({'detail': errors})

        if request.data['password1'] != request.data['password2']:
            raise ValidationError({'detail': 'Пароли не совпадают.'})

        try:    #    Проверяем пароль на сложность.
            validate_password(request.data['password1'])
        except Exception as password_error:
            error_array = []
            # Noinspection PyTypeChecker
            for item in password_error:
                error_array.append(item)
            raise ValidationError({'password_err': error_array})

        # Проверяем данные для уникальности имени пользователя
        request.data._mutable = True
        request.data.update({})
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid(raise_exception=True):
            # Сохраняем пользователя
            tentative_user = user_serializer.save()
            save_password(tentative_user, request.data['password1'])

            send_verify_email(request, tentative_user, 'register', self.message_template)
            return Response(data={
                'register': 'Требуется дополнительное действие.',
                'email': 'Необходимо подтвердить электронную почту. Мы отправили Вам письмо с инструкциями.',
            })

        raise ValidationError({'errors': user_serializer.errors})


class UserLookView(APIView):
    """ Класс для отображения пользователя.
    """

    @staticmethod
    def get(request):
        """ Выводит данные обратившегося пользователя.
        """
        look_user = request.user
        if not look_user:
            raise ValidationError('Недопустимый токен.')

        return Response(data={'user': UserSerializer(instance=look_user).data}, status=status.HTTP_200_OK)
