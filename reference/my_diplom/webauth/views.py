from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from webauth.forms import AppAuthenticationForm

User = get_user_model()


class UserLoginView(LoginView):
    """ Класс для выполнения входа в систему пользователем.
    """
    form_class = AppAuthenticationForm

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

            login(request, user)
            return redirect('home')

        # Если введённые значения не корректны, то возвратить эти значения.
        data = {
            'form': form
        }
        return render(request, template_name=self.template_name, context=data)


class UserLogoutView(LogoutView):
    """ Класс для выхода из системы.
        Шаблона выхода: 'reference/netology_pd_diplom/templates/registration/logout.html'
    """
    # Присутствие шаблона 'logged_out.html' в папке 'reference/netology_pd_diplom/templates/registration/'
    # перехватывает корректный выход из административной панели - 'admin/logout/'.
    template_name = "registration/logout.html"
