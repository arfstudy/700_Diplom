from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class UserHasDiffForm(forms.ModelForm):
    """ Форма для изменения персональных данных пользователя.
    """
    email = forms.EmailField(required=False)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
