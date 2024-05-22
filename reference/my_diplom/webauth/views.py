from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import UpdateView

from users.emails import send_verify_email
from users.services import get_user, get_user_fields_dict, save_old_user
from webauth.forms import AppAuthenticationForm, AppUserCreationForm, AppUserChangeForm
from webauth.services import verify_received_email

User = get_user_model()
OLD_VALUES = {}


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
    """
    template_verify = 'registration/email_verify_confirm.html'

    def get(self, request, key64, token):
        """ Проверяет корректность ссылки, полученной от пользователя.
        """
        global OLD_VALUES

        data = verify_received_email(request, key64, token, OLD_VALUES)

        OLD_VALUES.clear()
        return render(request, template_name=self.template_verify, context=data)


class UserRegisterView(View):
    """ Класс для создания нового пользователя и регистрации его в системе.
    """
    template_name = 'registration/register.html'
    message_template = 'registration/web_verify_email.html'
    done_url = 'web:email_verify_done'

    def get(self, request):
        data = {
            'form': AppUserCreationForm()
        }
        return render(request, template_name=self.template_name, context=data)

    def post(self, request):
        form = AppUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email')

            # user = authenticate(request, username=username, password=password)
            # При атрибуте 'is_active = False', пользователь не аутентифицируется.
            # Поэтому получаем пользователя из базы, по значению 'email'.
            user = get_user(email)

            send_verify_email(request, user, 'register', self.message_template)
            return redirect(self.done_url)

        # Если введённые значения не корректны, то возвращаем эти значения.
        data = {
            'form': form
        }
        return render(request, template_name=self.template_name, context=data)


class UserUpdateView(UpdateView):
    """ Контроллер, который изменяет персональные данные пользователя.
        (instance - "старый" объект, после валидации становится "новым" объектом,
        validated_data - "новые" значения полей объекта.)
    """
    template_update = 'webauth/user_update.html'
    template_complete = 'webauth/user_update_complete.html'
    message_template = 'registration/web_verify_email.html'
    done_url = 'web:email_verify_done'

    def get(self, request, *args, **kwargs):
        form = AppUserChangeForm(initial=get_user_fields_dict(request.user, FormClass=AppUserChangeForm))
        data = {'form': form}
        return render(request, template_name=self.template_update, context=data)

    def post(self, request, *args, **kwargs):
        """ Создаёт экземпляр формы с переданными переменными,
            а затем проверяет эти данные.
        """
        global OLD_VALUES

        form = AppUserChangeForm(request.POST, instance=get_user(request.user.pk))
        if form.has_changed():

            if form.is_valid():

                form.save()
                changed_list = form.changed_data
                if 'email' in changed_list:
                    form.instance.email_verify = False
                    form.save()

                    OLD_VALUES = save_old_user(request.user, changed_list)

                    send_verify_email(request, form.instance, 'update', self.message_template)
                    return redirect(self.done_url)

                return render(request, template_name=self.template_complete, context={'is_changed': True})

            # Если введённые значения не корректны, то возвратить эти значения.
            data = {
                'form': form
            }
            return render(request, template_name=self.template_update, context=data)

        return render(request, template_name=self.template_complete, context={'is_changed': False})


class UserInspectView(View):
    """ Класс для показа пользователей с ключём аутентификации.
    """
    template_name = "webauth/inspect.html"

    def get(self, request):
        """ Возвращает всех пользователей из БД.
        """
        users = User.objects.all()

        return render(request, template_name=self.template_name, context={'users': users})
