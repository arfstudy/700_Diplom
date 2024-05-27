from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import status
from rest_framework.exceptions import NotFound, AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apiauth.serializers import UserSerializer
from apiauth.services import get_or_create_token, delete_token, save_password
from apiauth.validators import validate_incoming_fields, verify_received_email, comparison_incoming_data
from users.emails import send_verify_email
from users.services import get_user, save_old_user as retain_old_values_user

User = get_user_model()
OLD_VALUES = {}


class UserLoginView(APIView):
    """ Класс для выполнения входа в систему.
    """
    message_template = 'registration/api_email_verify.html'

    def processing_login_parameters(self, request, process):
        """ Проверяет полученные параметры и определяет пользователя.
        """
        # Проверяем обязательные аргументы.
        required_fields = {'email', 'password'}
        res, is_incoming = validate_incoming_fields(request.data, required_fields)
        if not is_incoming:
            raise ValidationError({'detail': res})    # Статус ошибки - status=status.HTTP_400_BAD_REQUEST

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

    def post(self, request, *args, **kwargs):
        """ Выполняет вход в систему.
        """
        data = self.processing_login_parameters(request, 'login')
        if 'user' not in data.keys():
            return Response(data=data)

        content = {'login': 'Вы успешно вошли в систему.'}
        if hasattr(data['user'], 'auth_token') and data['user'].auth_token is not None:
            # You are logged in the system.
            content['login'] = 'Вы уже находитесь в системе.'

        token, created = get_or_create_token(user=data['user'])
        return Response(data={**content, 'token_key': token.key, 'user': f'{data["user"]}'})


class EmailVerifyView(APIView):
    """ Класс для подтверждения email.
    """

    def post(self, request, *args, **kwargs):
        """ Проверяет корректность ключей, полученных от пользователя.
        """
        global OLD_VALUES
        # Проверяем обязательные аргументы.
        required_fields = {'key64', 'token'}
        res, is_incoming = validate_incoming_fields(request.data, required_fields)
        if not is_incoming:
            raise ValidationError({'detail': res})

        data = verify_received_email(request, OLD_VALUES, UserSerializer)

        condition = data.pop('condition', status.HTTP_200_OK)
        return Response(data=data, status=condition)


class UserLogoutView(APIView):
    """ Класс для выполнения выхода из системы.
    """

    def post(self, request, *args, **kwargs):
        """ Удаляет токен.
        """
        if delete_token(request.user):
            return Response(data={'logout': 'Успешный выход из системы.'}, status=status.HTTP_204_NO_CONTENT)

        return Response(data={'logout': 'Ошибка удаления токена.'}, status=status.HTTP_417_EXPECTATION_FAILED)


class CreateNewTokenView(UserLoginView):
    """ Класс для обновления токена.
    """

    def post(self, request, *args, **kwargs):
        """ Обновляет скомпрометированный токен.
        """
        data = self.processing_login_parameters(request, 'token')
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

    def post(self, request, *args, **kwargs):
        """ Создаёт нового пользователя.
        """
        # Проверяем обязательные аргументы.
        required_fields = {'first_name', 'last_name', 'email', 'password1', 'password2'}
        res, is_incoming = validate_incoming_fields(request.data, required_fields)
        if not is_incoming:
            raise ValidationError({'detail': res})

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


class LookUserView(APIView):
    """ Класс для отображения пользователя.
    """

    def get(self, request):
        """ Выводит данные обратившегося пользователя.
        """
        look_user = request.user
        if look_user is None:
            raise ValidationError({'detail': 'Недопустимый токен.'})

        return Response(data={'user': UserSerializer(instance=look_user).data}, status=status.HTTP_200_OK)


class UserUpdateView(APIView):
    """ Класс для изменения персональных данных пользователя.
    """
    email_message_template = 'registration/api_email_verify.html'
    writable_fields = ['email', 'first_name', 'last_name']

    def put(self, request, *args, **kwargs):
        """ Изменяет все поля пользователя.
        """
        put_msg = {'put': 'Или воспользуйтесь PATCH-запросом.'}
        content = self.update_user(request, self.writable_fields, put_msg)
        return Response(data=content, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        """ Изменяет переданные поля пользователя.
        """
        # Проверяем на присутствие хотя бы одного переданного поля.
        changed_list = [k for k in request.data.keys() if k in self.writable_fields]
        if not changed_list:
            raise ValidationError({'detail': 'Вы не передали ни одного поля для изменений.',
                                   'patch': f'Допустимые поля: `{"` `".join(self.writable_fields)}`.'})

        content = self.update_user(request, changed_list, {})
        return Response(data=content, status=status.HTTP_200_OK)

    def update_user(self, request, changed_list, put_msg):
        """ Изменяет пользователя.
        """
        global OLD_VALUES
        # Проверяем наличие аргументов.
        res, is_incoming = validate_incoming_fields(request.data, changed_list)
        if not is_incoming:
            data = {'detail': res}
            if put_msg:
                data = {**data, **put_msg}
            raise ValidationError(detail=data)

        # Проверяем переданные поля на совпадение со значениями из БД.
        res, warning = comparison_incoming_data(request.data, self.writable_fields, request.user)
        if 'warning' in warning.keys():
            warning_msg = {'warning': warning.pop('warning'), 'contact': UserSerializer(instance=request.data).data}
            raise ValidationError(detail={**warning_msg, **warning})

        changed_list = [k for k in res.keys()]
        OLD_VALUES = retain_old_values_user(request.user, changed_list)
        user_serializer = UserSerializer(instance=request.user, data=res, partial=True)
        if user_serializer.is_valid(raise_exception=True):
            # сохраняем пользователя
            user = user_serializer.save()
            if 'email' in changed_list:
                user.email_verify = False
                user.save(update_fields=['email_verify'])

                send_verify_email(request, user, 'update', self.email_message_template)
                email_msg = {
                    'update': 'Требуется дополнительное действие.',
                    'email': 'Необходимо подтвердить электронную почту. Мы отправили Вам письмо с инструкциями.'
                }
                return {**email_msg, **warning} if warning else email_msg

            update_msg = {'update': 'Ваши данные успешно изменены.', 'user': UserSerializer(instance=user).data}
            return {**update_msg, **warning} if warning else update_msg

        raise ValidationError({'detail': user_serializer.errors})
