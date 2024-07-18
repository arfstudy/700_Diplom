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


class Shop(models.Model):
    """ Магазин.
    """
    class Worked(models.TextChoices):
        """ Рабочее состояние магазина. """
        OPEN = 'OP', 'Открыт'
        CLOSE = 'CL', 'Закрыт'

    name = models.CharField(max_length=50, unique=True, verbose_name='Название')
    filename = models.URLField(null=True, blank=True, verbose_name='Загрузочный файл')
    seller = models.OneToOneField(to=Salesman, on_delete=models.SET_NULL, null=True, blank=True, related_name='seller',
                                  verbose_name='Менеджер по продажам')
    buyer = models.OneToOneField(to=Salesman, on_delete=models.SET_NULL, null=True, blank=True, related_name='buyer',
                                 verbose_name='Менеджер по закупкам')
    state = models.CharField(max_length=2, choices=Worked.choices, default=Worked.CLOSE, verbose_name='Приём заказов')

    objects = models.Manager()
    DoesNotExist = models.Manager

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """ Сохраняет состояние магазина.
            Если у магазина нет "Менеджера по продажам", то он не может торговать - он закрыт.
            Если есть "Менеджер по продажам" и не передаётся статус "Приём заказов", то устанавливается "Открыт".
        """
        if self.seller:
            if not self.state:
                self.state = Shop.Worked.OPEN
        else:
            self.state = Shop.Worked.CLOSE

        return super().save(*args, **kwargs)
