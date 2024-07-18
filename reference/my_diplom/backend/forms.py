from django import forms

from backend.models import Contact


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
