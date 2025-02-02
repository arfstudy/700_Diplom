from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound, ErrorDetail

from apiauth.validators import pre_check_incoming_fields
from backend import models
from backend.forms import ContactHasDiffForm, ShopHasDiffForm
from backend.services import (get_transmitted_obj, join_choice_errors, replace_salesmans_errors,
                              get_category_by_name_and_catalog_number, get_category, get_category_by_catalog_number,
                              get_shop, get_or_create_parameter, set_new_category)
from backend.validators import (is_not_salesman, is_permission_updated, is_validate_exists,
                                get_or_create_product_with_category, add_parameters, is_enough_products)

Salesman = get_user_model()


class ContactSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания, отображения и изменения Контакта покупателя.
    """
    user = serializers.StringRelatedField(source='salesman', read_only=True)
    salesman = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.Contact
        fields = ['id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone', 'user',
                  'salesman']
        read_only_fields = ['id']

    def to_internal_value(self, validated_data):
        """ Добавляет собственные проверки: наличие обязательных полей, присутствие реальных изменений,
            отсеивание неликвидных полей, (проверка и подготовка choice-параметров модели 'Contact' лишняя).
        """
        # Проверяем полученные поля на корректность.
        required_fields = {'city', 'street', 'house'}
        additional_fields = {'structure', 'building', 'apartment', 'phone'}
        action, obj = get_transmitted_obj(self, required_fields)
        res, errors, choice_errors, warning, invalid_fields = pre_check_incoming_fields(validated_data, required_fields,
                                                additional_fields, action, obj, ContactHasDiffForm, 'контакта')
        if errors:
            instance = ({'contact': ContactSerializer(instance=obj).data}
                        if action in ['update', 'partial_update'] else {})
            raise ValidationError(detail={**errors, **warning, **instance, **invalid_fields})

        # Встроенная проверка Django полученных полей на корректность.
        try:
            ret = super().to_internal_value(res)
        except ValidationError as e:
            errors = {k: [str(v[0])] for k, v in e.detail.items()}
            raise ValidationError(detail={**errors, **invalid_fields})

        return ret


class ShortSalesmanSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения Покупателя в сокращённом формате.
    """
    customer = serializers.CharField(source='__str__', read_only=True)

    class Meta:
        model = Salesman
        fields = ['customer']


class ShortContactSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения Контакта в сокращённом формате.
    """
    contact = serializers.CharField(source='get_short_contact', read_only=True)

    class Meta:
        model = models.Contact
        fields = ['contact']


class ShortShopSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения Магазина в сокращённом формате.
    """
    state = serializers.CharField(source='get_state_display', read_only=True)

    class Meta:
        model = models.Shop
        fields = ['id', 'name', 'state', 'seller', 'buyer']
        read_only_fields = ['id', 'name', 'seller', 'buyer']


class ShopSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания, отображения и изменения Магазина.
    """
    user_seller = serializers.StringRelatedField(source='seller', read_only=True)
    user_buyer = serializers.StringRelatedField(source='buyer', read_only=True)
    categories = serializers.StringRelatedField(read_only=True, many=True)

    class Meta:
        model = models.Shop
        fields = ['id', 'name', 'condition', 'state', 'filename', 'user_seller', 'user_buyer', 'categories',
                  'seller', 'buyer', 'category_ids']
        extra_kwargs = {
            'id': {'read_only': True},
            'condition': {'source': 'get_state_display', 'read_only': True},
            'state': {'write_only': True, 'required': False},
            'filename': {'required': False},
            'seller': {'write_only': True, 'required': False},
            'buyer': {'write_only': True, 'required': False},
            'category_ids': {'source': 'categories', 'required': False, 'write_only': True, 'many': True}
        }

    def to_internal_value(self, validated_data):
        """ Добавляет собственные проверки: наличие обязательных полей, присутствие реальных изменений,
            отсеивание неликвидных полей, проверка и подготовка choice-параметров.
        """
        # Проверяет категории на существующие и несуществующие, очищает от повторяющихся.
        errors_msg, categories, ret = [], [], {}
        if 'category_ids' in validated_data.keys():
            is_exists, errors_msg = is_validate_exists(validated_data, 'category_ids', models.Category,
                                                       'Категория')
            if not is_exists:
                raise NotFound(detail={'categories': errors_msg})
            category_ids = validated_data.pop('category_ids')
            categories = [get_category(c) for c in category_ids]

        # Предварительная проверка полученных полей.
        required_fields = {'name'}
        additional_fields = {'state', 'filename', 'seller', 'buyer'}
        action, obj = get_transmitted_obj(self, required_fields)
        res, errors, choice_errors, warning, invalid_fields = pre_check_incoming_fields(validated_data, required_fields,
                                                additional_fields, action, obj, ShopHasDiffForm, 'магазина')
        if errors and not (errors['errors'][0].startswith('Вы не передали ничего нового') and categories):
            instance = ({'shop': ShopSerializer(instance=obj).data}
                        if action in ['update', 'partial_update'] else {})
            raise ValidationError(detail={**errors, **warning, **instance, **invalid_fields})

        # Встроенная проверка Django полученных полей на корректность.
        try:
            ret = super().to_internal_value(res)
        except ValidationError as e:
            errors = {k: [str(v[0])] for k, v in e.detail.items()}
            if choice_errors:
                join_choice_errors(errors, choice_errors)
            if 'seller' in errors.keys() or 'buyer' in errors.keys():
                replace_salesmans_errors(errors, res)
            if errors_msg:
                errors = {**errors, 'categories': errors_msg}
            raise ValidationError(detail={**errors, **invalid_fields})

        if categories:
            ret['categories'] = categories
        return ret

    def validate_seller(self, value):
        """ Проверяет, что пользователь 'seller' не является менеджером какого-нибудь магазина.
        """
        is_not_salesman(self, value)

        return value

    def validate_buyer(self, value):
        """ Проверяет, что пользователь 'buyer' не является менеджером какого-нибудь магазина.
        """
        is_not_salesman(self, value)

        return value

    def validate(self, attrs):
        """ Проверяет все поля на возможность быть изменёнными.
        """
        if self.context['view'].action == 'partial_update':
            is_permission_updated(self, attrs)

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        """ Вносит изменения в Магазин.
            Связи с новыми категориями добавляются к старым, а не замещают их.
        """
        instance.name = validated_data.get('name', instance.name)
        instance.state = validated_data.get('state', instance.state)
        instance.filename = validated_data.get('filename', instance.filename)
        instance.seller = validated_data.get('seller', instance.seller)
        instance.buyer = validated_data.get('buyer', instance.buyer)
        categories = validated_data.pop('categories', [])
        if categories:
            instance.categories.add(*categories)
        instance.save()
        return instance


class CategorySerializer(serializers.ModelSerializer):
    """ Сериализатор для создания, отображения и изменения Категории товара.
    """
    stores = serializers.StringRelatedField(source='shops', read_only=True, many=True)

    class Meta:
        model = models.Category
        fields = ['id', 'name', 'catalog_number', 'stores', 'shops']
        extra_kwargs = {
            'id': {'read_only': True},
            'shops': {'required': False, 'write_only': True, 'many': True}
        }

    def to_internal_value(self, validated_data):
        """ Добавляет собственные предварительные проверки.
        """
        # Проверяет магазины на существующие и несуществующие, очищает от повторяющихся.
        errors_msg = ''
        if 'shops' in validated_data.keys() and validated_data['shop']:
            is_exists, errors_msg = is_validate_exists(validated_data, 'shops', models.Shop, 'Магазин')
            if not is_exists:
                raise NotFound(detail={'shops': errors_msg})

        if not self.instance:
            # Получает Категорию, если она существует.
            name = validated_data.get('name', '')
            catalog_number = int(validated_data.get('catalog_number', 0))
            category = get_category_by_name_and_catalog_number(name, catalog_number)
            if category:
                self.instance = category
            # Переходит в режим 'update'.

        # Встроенная проверка Django полученных полей на корректность.
        try:
            ret = super().to_internal_value(validated_data)
        except ValidationError as e:
            errors = {k: [str(v[0])] for k, v in e.detail.items()}
            if errors_msg:
                errors = {**errors, 'shops': errors_msg}
            raise ValidationError(detail=errors)

        if errors_msg:
            # Передаёт предупреждение во "вьюшку", какие магазины оказались несуществующими.
            self.context['warning'] = {'shops': errors_msg}

        return ret

    @transaction.atomic
    def update(self, instance, validated_data):
        """ Вносит изменения в Категорию.
            Связи с новыми магазинами добавляются к старым, а не замещают их.
        """
        instance.name = validated_data.get('name', instance.name)
        instance.catalog_number = validated_data.get('catalog_number', instance.catalog_number)
        shops = validated_data.pop('shops')
        if shops:
            instance.shops.add(*shops)
        instance.save()
        return instance


class ProductSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания, отображения и изменения Товара.
    """
    category = serializers.StringRelatedField(read_only=True)
    category_number = serializers.CharField(source='category.catalog_number', write_only=True, required=False)
    shops = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Product
        fields = ['id', 'name', 'category', 'category_number', 'shops']
        read_only_fields = ['id']

    @staticmethod
    def get_shops(obj):
        shops = models.Shop.objects.filter(categories__products=obj).distinct()
        return [str(s) for s in shops]

    @staticmethod
    def validate_category_number(value):
        """ Проверяет, что существует категория с заданным номером.
        """
        if not models.Category.objects.filter(catalog_number=value).exists():
            raise NotFound(f'Категория с номером catalog_number={value} не найдена.')

        return value

    @transaction.atomic
    def create(self, validated_data):
        """ Создаёт новый товар.
        """
        category, data = get_category_by_catalog_number(validated_data)

        product = super().create(data)
        if category:
            product.category = category
            product.save(update_fields=['category'])

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        """ Вносит изменения в товар.
        """
        category_obj, data = get_category_by_catalog_number(validated_data)

        instance.name = validated_data.get("name", instance.name)
        if category_obj and category_obj != instance.category:
            set_new_category(instance, category_obj)

        return instance


class ParameterAndValueSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания и отображения Названия характеристики и его Значения внутри Описания товара.
    """
    parameter = serializers.CharField(source='parameter.name')

    class Meta:
        model = models.ProductParameter
        fields = ['parameter', 'value']

    def validate_value(self, value):
        """ Проверяет поле 'value' на наличие содержимого. (Только при создании нового Описания.)
            При изменении, пустое значение поля 'value' приводит к удалению соответствующей Характеристики
            из Описания товара.
        """
        if self.context['view'].action == 'create' and (not value or value.replace(" ", "") == ""):
            raise ValidationError(detail=['Это поле не может иметь пустое значение `null` или пустую строку ``.'])

        return value

    def validate(self, attrs):
        """ Проверяет обязательное присутствие поля 'value'.
            Присутствие поля 'parameter' проверяется в 'to_internal_value()'.
        """
        if 'value' not in attrs.keys():
            raise ValidationError(detail={'value': ['Обязательное поле.']})

        return attrs


class ProductInfoSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания, отображения и изменения Описания товара.
    """
    product = serializers.StringRelatedField(read_only=True)
    name = serializers.CharField(source='product.name', write_only=True)
    product_parameters = ParameterAndValueSerializer(required=False, many=True)
    category_number = serializers.CharField(source='product.category.catalog_number', write_only=True)
    category = serializers.StringRelatedField(source='product.category', read_only=True)
    shop_name = serializers.CharField(source='shop.name', write_only=True)
    shop = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = models.ProductInfo
        fields = ['info_id', 'product', 'name', 'model', 'external_id', 'quantity', 'price', 'price_rrc',
                  'product_parameters', 'category_number', 'category', 'shop_name', 'shop']
        extra_kwargs = {
            'info_id': {'source': 'id', 'read_only': True},
            'external_id': {'source': 'catalog_number'}
        }

    @staticmethod
    def validate_shop_name(value):
        """ Проверяет, что существует магазин с заданным названием.
        """
        if not models.Shop.objects.filter(name=value).exists():
            raise NotFound(f'Магазин с таким названием `{value}` не существует.')

        return value

    @staticmethod
    def validate_category_number(value):
        """ Проверяет, что существует категория с заданным номером.
        """
        if not models.Category.objects.filter(catalog_number=value).exists():
            raise NotFound(f'Категория с номером по каталогу catalog_number={value} не существует.')

        return value

    def validate(self, attrs):
        """ Предостерегает от повторного внесения Товара в Магазин.
            При изменении Описания товара такую проверку проводить не требуется.
        """
        if (self.context['view'].action == 'create'
            and models.ProductInfo.objects.filter(catalog_number=attrs['catalog_number'],
                                                  product__name=attrs['product']['name'],
                                                  shop__name=attrs['shop']['name']
                                                  ).exists()):
            raise ValidationError(detail={'prod_info_err': 'Товар с таким Номером по каталогу и Описанием уже'
                                                           ' существует в этом Магазине.'},)

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """ Создаёт новое Описание.
        """
        validated_data['shop'] = get_shop(param=validated_data['shop']['name'])
        get_or_create_product_with_category(validated_data)
        self.context['created'] = validated_data.pop('created')
        validated_data['shop'].categories.add(validated_data.pop('category'))
        product_parameters = validated_data.pop('product_parameters', [])

        prod_info = super().create(validated_data)
        for item in product_parameters:
            parameter, created = get_or_create_parameter(item['parameter']['name'])
            prod_info.parameters.add(parameter, through_defaults={'value': item['value']})

        return prod_info

    @transaction.atomic
    def update(self, instance, validated_data):
        """ Вносит изменения в Описание товара.
        """
        instance.model = validated_data.get('model', instance.model)
        instance.catalog_number = validated_data.get('catalog_number', instance.catalog_number)
        instance.quantity = validated_data.get('quantity', instance.quantity)
        instance.price = validated_data.get('price', instance.price)
        instance.price_rrc = validated_data.get('price_rrc', instance.price_rrc)

        if 'shop' in validated_data.keys():
            instance.shop = get_shop(validated_data['shop']['name'])

        if 'product' in validated_data.keys():
            get_or_create_product_with_category(validated_data, instance.product.name)
            instance.product = validated_data['product']
            self.context['created'] = validated_data.pop('created')

        if 'product_parameters' in validated_data.keys():
            add_parameters(instance, validated_data['product_parameters'])

        instance.save()
        return instance


class PriceSerializer(serializers.ModelSerializer):
    """ Сериализатор для просмотра Прайса товаров.
    """
    product = serializers.StringRelatedField(read_only=True)
    product_parameters = ParameterAndValueSerializer(read_only=True, many=True)
    category = serializers.StringRelatedField(source='product.category', read_only=True)
    shop = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = models.ProductInfo
        fields = ['info_id', 'product', 'model', 'external_id', 'quantity', 'price', 'product_parameters',
                  'category', 'shop']
        extra_kwargs = {
            'info_id': {'source': 'id', 'read_only': True},
            'model': {'read_only': True},
            'external_id': {'source': 'catalog_number', 'read_only': True},
            'quantity': {'read_only': True},
            'price': {'source': 'price_rrc', 'read_only': True}
        }


class ShortOrderItemSerializer(serializers.ModelSerializer):
    """ Сериализатор для добавления и отображения Товара в Заказе.
    """
    info_id = serializers.CharField(source='product_info.id')
    product = serializers.StringRelatedField(source='product_info.product', read_only=True)
    external_id = serializers.CharField(source='product_info.catalog_number', read_only=True)
    price = serializers.CharField(source='product_info.price_rrc', read_only=True)
    shop = serializers.StringRelatedField(source='product_info.shop', read_only=True)
    shop_id = serializers.CharField(source='product_info.shop.id', write_only=True)

    class Meta:
        model = models.OrderItem
        fields = ['info_id', 'product', 'external_id', 'quantity', 'price', 'shop', 'shop_id']

    def to_internal_value(self, validated_data):
        """ Заменяет сообщение при отрицательном количестве товара в заказе.
        """
        # Встроенная проверка Django полученных полей на корректность.
        try:
            ret = super().to_internal_value(validated_data)
        except ValidationError as e:
            if 'quantity' in e.args[0] and e.args[0]['quantity'][0].code == 'min_value':
                e.args[0]['quantity'][0] = ErrorDetail(
                    string='Заказываемое количества Товара должно быть больше 0.', code='min_value')
            raise ValidationError(detail=e.args[0])

        return ret

    @staticmethod
    def validate_info_id(value):
        """ Проверяет существование Описания товара с номером 'info_id'.
        """
        if not models.ProductInfo.objects.filter(id=value).exists():
            raise ValidationError(f'Описание товара с info_id={value} не найдено.')

        return value

    @staticmethod
    def validate_quantity(value):
        """ Проверяет, чтобы количество заказываемого Товара было положительным числом.
        """
        if value <= 0:
            raise ValidationError('Заказываемое количества Товара должно быть больше 0.')

        return value

    @staticmethod
    def validate_shop_id(value):
        """ Проверяет существование Магазина с номером 'shop_id'.
        """
        if not models.Shop.objects.filter(id=value).exists():
            raise ValidationError(f'Магазин с shop_id={value} не найден.')

        return value

    def validate(self, attr):
        """ Проверяет, чтобы Товар имелся в указанном Магазине и был в достаточном количестве.
        """
        info_id, quantity, shop_id = attr['product_info']['id'], attr['quantity'], attr['product_info']['shop']['id']
        if not models.ProductInfo.objects.filter(id=info_id, shop__id=shop_id).exists():
            err_msg = f'Описание товара с info_id={info_id} в Магазине с shop_id={shop_id} не найдено.'
            raise ValidationError(detail={'info_id': err_msg})

        remainder = models.ProductInfo.objects.get(id=info_id, shop__id=shop_id).quantity
        if quantity > remainder:
            err_msg = (f"Вы пытаетесь добавить в корзину Описание товара с info_id={info_id} в количестве {quantity}"
                       f" шт, превышающем остаток в Магазине с shop_id={shop_id}, где {remainder} шт.")
            raise ValidationError(detail={'quantity': err_msg})

        return attr


class OrderSerializer(serializers.ModelSerializer):
    """ Сериализатор для создания и отображения Заказа.
    """
    ordered_items = ShortOrderItemSerializer(many=True)
    count = serializers.SerializerMethodField(read_only=True)
    state = serializers.CharField(source='get_state_display', read_only=True)
    updated_state = serializers.SerializerMethodField(read_only=True)
    created_at = serializers.SerializerMethodField(read_only=True)
    customer = serializers.StringRelatedField(read_only=True)
    user = serializers.HiddenField(source='customer', default=serializers.CurrentUserDefault())
    contact = serializers.CharField(source='contact.get_short_contact', read_only=True)
    contact_id = serializers.CharField(source='contact.id', write_only=True)

    class Meta:
        model = models.Order
        fields = ['id', 'ordered_items', 'count', 'sum', 'state', 'updated_state', 'created_at', 'customer', 'user',
                  'contact', 'contact_id']
        read_only_fields = ['id', 'sum']

    @staticmethod
    def get_count(obj):
        """ Подсчитывает количество Товаров в Заказе.
        """
        return obj.ordered_items.all().count()

    @staticmethod
    def get_updated_state(obj):
        """ Отображает время изменения в нужном формате.
        """
        return obj.updated_state.strftime("%Y-%m-%d %H:%M")

    @staticmethod
    def get_created_at(obj):
        """ Отображает время создания в нужном формате.
        """
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    def to_internal_value(self, validated_data):
        """ Добавляет собственные предварительные проверки.
        """
        # Проверяет наличие товаров в заказе.
        items = validated_data.get('ordered_items', [])
        if self.context['view'].action == 'create' and not items:
            raise ValidationError(detail={'ordered_items': 'Вы не можете создать пустой заказ.'})

        # Проверяет на отсутствие повторяющихся Товаров.
        infos = [i['info_id'] for i in items if 'info_id' in i]
        if len(infos) == len(items) and len(set(infos)) < len(items):
            raise ValidationError(detail={'ordered_items': 'Имеются повторяющиеся товары.'})

        # Встроенная проверка Django полученных полей на корректность.
        try:
            ret = super().to_internal_value(validated_data)
        except ValidationError as e:
            raise ValidationError(detail=e.args[0])

        return ret

    def validate_contact_id(self, value):
        """ Проверяет существование Контакта с номером 'contact_id'.
        """
        if not models.Contact.objects.filter(salesman=self.context['request'].user, id=value).exists():
            raise ValidationError(f'У Вас нет контакта с contact_id={value}.')

        return value

    @transaction.atomic
    def create(self, validated_data):
        """ Создаёт новый Заказ.
        """
        items = validated_data.pop('ordered_items')
        validated_data['contact'] = models.Contact.objects.get(id=validated_data.pop('contact')['id'])

        order = super().create(validated_data)
        for item in items:
            shop = models.Shop.objects.get(id=item['product_info']['shop']['id'])
            product = models.ProductInfo.objects.get(id=item['product_info']['id'], shop=shop)
            order.product_infos.add(product, through_defaults={'quantity': item['quantity']})

        return order
