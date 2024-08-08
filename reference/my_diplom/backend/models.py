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


class Category(models.Model):
    """ Категория товара.
    """
    name = models.CharField(max_length=40, unique=True, verbose_name='Название')
    catalog_number = models.IntegerField(verbose_name='Номер по каталогу')
    shops = models.ManyToManyField(to=Shop, blank=True, related_name='categories', verbose_name='Магазины')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Список категорий'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    """ Продукт.
    """
    name = models.CharField(max_length=80, unique=True, verbose_name='Название')
    category = models.ForeignKey(to=Category, on_delete=models.CASCADE, null=True, blank=True, related_name='products',
                                 verbose_name='Категория')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = "Список продуктов"
        ordering = ('name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """ Описание товара.
    """
    model = models.CharField(max_length=80, verbose_name='Модель')
    catalog_number = models.PositiveIntegerField(verbose_name='Номер по каталогу')
    product = models.ForeignKey(to=Product, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='product_infos', verbose_name='Продукт')
    shop = models.ForeignKey(to=Shop, on_delete=models.CASCADE, null=True, blank=True, related_name='product_infos',
                             verbose_name='Магазин')
    quantity = models.PositiveIntegerField(null=True, blank=True, verbose_name='Количество')
    price = models.PositiveIntegerField(null=True, blank=True, verbose_name='Закупочная цена')
    price_rrc = models.PositiveIntegerField(null=True, blank=True, verbose_name='Рекомендуемая розничная цена')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Информационный список о продуктах"
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'catalog_number'], name='unique_product_info'),
        ]

    def __str__(self):
        return f'{self.product.name} {self.model}'


class Parameter(models.Model):
    """ Параметр товара.
    """
    name = models.CharField(max_length=40, unique=True, verbose_name='Название параметра')
    products = models.ManyToManyField(to=ProductInfo, through='ProductParameter', blank=True,
                                      related_name='parameters', verbose_name='Магазины')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Имя параметра'
        verbose_name_plural = "Список имён параметров"
        ordering = ('name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """ Значение параметра товара.
    """
    product_info = models.ForeignKey(to=ProductInfo, on_delete=models.CASCADE, related_name='product_parameters',
                                     verbose_name='Описание товара')
    parameter = models.ForeignKey(to=Parameter, on_delete=models.CASCADE, related_name='product_parameters',
                                  verbose_name='Название параметра')
    value = models.CharField(max_length=100, verbose_name='Значение параметра')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Значение параметра'
        verbose_name_plural = "Список значений параметров"
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
        ]


class Order(models.Model):
    """ Заказ.
    """
    class Status(models.TextChoices):
        """ Статусы состояния заказа. """
        BASKET = 'BS', 'В корзине'
        NEW = 'NE', 'Новый'
        """ 1) На данный момент Вам недоступно изменение заказа. Нужно отменить заказ.
            2) Ваш заказ отменён.
        """
        CONFIRMED = 'CF', 'Подтверждён'
        ASSEMBLED = 'AS', 'Собран'
        SENT = 'SN', 'Отправлен'
        CANCELED = 'CN', 'Отменён'
        # DELIVERED = 'DV', 'Доставлен'    # Заменил на "Получен".
        RECEIVED = 'RC', 'Получен'

    customer = models.ForeignKey(to=Salesman, on_delete=models.CASCADE, related_name='orders',
                                 verbose_name='Покупатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    state = models.CharField(max_length=2, choices=Status.choices, default=Status.BASKET, verbose_name='Статус')
    updated_state = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')
    contact = models.ForeignKey(to=Contact, on_delete=models.CASCADE, null=True, blank=True,
                                related_name='orders', verbose_name='Адрес доставки')
    product_infos = models.ManyToManyField(to=ProductInfo, through='OrderItem', related_name='orders',
                                          verbose_name='Магазины')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказов"
        ordering = ['-created_at']

    def __str__(self):
        return str(self.id)

    @property
    def sum(self):
        # Вычисляет сумму заказа.
        return self.ordered_items.aggregate(
            total=models.Sum(models.F('product_info__price_rrc')*models.F('quantity')))['total']


class OrderItem(models.Model):
    """ Позиция заказа.
    """
    order = models.ForeignKey(to=Order, on_delete=models.CASCADE, related_name='ordered_items', verbose_name='Заказ')
    product_info = models.ForeignKey(to=ProductInfo, on_delete=models.CASCADE, related_name='ordered_items',
                                verbose_name='Продукт')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    objects = models.Manager()

    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'product_info'], name='unique_order_item'),
        ]
