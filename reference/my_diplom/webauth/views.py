from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.views import View

from users.emails import send_verify_email
from webauth.forms import AppAuthenticationForm
from webauth.services import verify_received_email

User = get_user_model()


class UserLoginView(LoginView):
    """ Класс для выполнения входа в систему пользователем.
    """
    form_class = AppAuthenticationForm
    message_template = 'registration/web_verify_email.html'
    done_url = 'web:email_verify_done'
    home_url = 'home'

    def post(self, request, *args, **kwargs):
        """ Создаёт экземпляр формы с переданными переменными из POST-запроса,
            проверяет их и регистрирует пользователя в системе.
        """
        form = self.get_form()

        if form.is_valid():
            email = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, email=email, password=password)

            # Проверка подтверждённости почты.
            if not user.email_verify:
                send_verify_email(request, user, 'login', self.message_template)
                return redirect(self.done_url)

            login(request, user)
            return redirect(self.home_url)

        # Если введённые значения не корректны, то возвратить эти значения.
        data = {
            'form': form
        }
        return render(request, template_name=self.template_name, context=data)


class UserLogoutView(LogoutView):
    """ Класс для выхода из системы.
        Шаблон выхода: 'reference/netology_pd_diplom/templates/registration/logout.html'

        Присутствие шаблона 'logged_out.html' в папке 'reference/netology_pd_diplom/templates/registration/'
        перехватывает корректный выход из административной панели - 'admin/logout/'.
    """
    template_name = "registration/logout.html"


class UserEmailVerifyView(View):
    """ Класс для подтверждения email.
        Проверяет корректность ссылки, полученной от пользователя.
    """
    template_verify = 'registration/email_verify_confirm.html'

    def get(self, request, key64, token):

        data = verify_received_email(request, key64, token)

        return render(request, template_name=self.template_verify, context=data)


class UserInspectView(View):
    """ Класс для показа пользователей с ключём аутентификации.
    """
    template_name = "webauth/inspect.html"

    def get(self, request):
        """ Возвращает всех пользователей из БД.
        """
        users = User.objects.all()

        return render(request, template_name=self.template_name, context={'users': users})
