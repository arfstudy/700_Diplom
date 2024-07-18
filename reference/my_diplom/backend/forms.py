from django import forms
from django.contrib.auth import get_user_model

from backend.models import Contact, Shop

Salesman = get_user_model()


class ContactHasDiffForm(forms.ModelForm):
    """ Форма для проверки полей контакта.
    """
    city = forms.EmailField(required=False)
    street = forms.CharField(required=False)
    house = forms.CharField(required=False)
    structure = forms.EmailField(required=False)
    building = forms.EmailField(required=False)
    apartment = forms.CharField(required=False)
    phone = forms.CharField(required=False)

    class Meta:
        model = Contact
        fields = ['city', 'street', 'house', 'structure', 'building', 'apartment', 'phone']


class ShopHasDiffForm(forms.ModelForm):
    """ Форма для проверки полей магазина.
    """
    name = forms.EmailField(required=False)
    state = forms.ChoiceField(required=False)
    seller = forms.ModelChoiceField(queryset=Salesman.objects.all(), required=False)
    buyer = forms.ModelChoiceField(queryset=Salesman.objects.all(), required=False)
    filename = forms.URLField(required=False)

    class Meta:
        model = Shop
        fields = ['name', 'state', 'seller', 'buyer', 'filename']
