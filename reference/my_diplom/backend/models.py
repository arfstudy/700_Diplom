from django.contrib.auth import get_user_model
from django.db import models

Salesman = get_user_model()


class Contact(models.Model):
    """ Контакты пользователя.
    """
    salesman = models.ForeignKey(
        to=Salesman, on_delete=models.CASCADE, related_name='contacts', verbose_name='Покупатель'
    )
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом')
    structure = models.CharField(max_length=15, null=True, blank=True, verbose_name='Корпус')
    building = models.CharField(max_length=15, null=True, blank=True, verbose_name='Строение')
    apartment = models.CharField(max_length=15, null=True, blank=True, verbose_name='Квартира')
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name='Телефон')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f'{self.id}: {self.city}, {self.street} {self.house}'

    def get_short_contact(self):
        """ Возвращает сокращённый контакт с телефоном.
        """
        return f'{self}. Phone {self.phone}'

    def get_contact_with_salesman(self):
        """ Возвращает контакт с 'id' пользователя.
        """
        return f'{self.get_short_contact()}. salesman_id: {self.salesman.id}'
