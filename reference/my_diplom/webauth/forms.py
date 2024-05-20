from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from rest_framework.exceptions import ValidationError

from users.services import get_user


class AppAuthenticationForm(AuthenticationForm):
    """ Форма аутентификации.
        Добавляет выделенную проверку поля 'is_active', с указанием понятной ответной фразы.
    """
    error_messages = {
        "is_deleted": "This user has been deleted. Contact the site administrator.",
        # "is_active": "This user has not been found. Contact the site administrator.",    # -> "is_deleted"
        "invalid_login": (
            "Please enter the correct email address and password. Note that both fields may be case-sensitive."
        ),
    }

    def clean(self):
        email = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if email is not None and password:
            user_obj = get_user(email)
            if user_obj is not None:
                if not user_obj.is_active:
                    raise ValidationError(
                        self.error_messages["is_deleted"],
                        code="is_deleted",
                    )
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()

        return self.cleaned_data
