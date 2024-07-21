from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apiauth.validators import pre_check_incoming_fields
from backend import models
from backend.forms import ContactHasDiffForm, ShopHasDiffForm
from backend.services import (get_transmitted_obj, join_choice_errors, replace_salesmans_errors,
                              get_category_by_name_and_catalog_number)
from backend.validators import is_not_salesman, is_permission_updated, is_validate_exists_shop

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
                  'seller', 'buyer']
        extra_kwargs = {
            'id': {'read_only': True},
            'condition': {'source': 'get_state_display', 'read_only': True},
            'state': {'write_only': True, 'required': False},
            'filename': {'required': False},
            'seller': {'write_only': True, 'required': False},
            'buyer': {'write_only': True, 'required': False},
        }

    def to_internal_value(self, validated_data):
        """ Добавляет собственные проверки: наличие обязательных полей, присутствие реальных изменений,
            отсеивание неликвидных полей, проверка и подготовка choice-параметров.
        """
        # Предварительная проверка полученных полей.
        required_fields = {'name'}
        additional_fields = {'state', 'filename', 'seller', 'buyer'}
        action, obj = get_transmitted_obj(self, required_fields)
        res, errors, choice_errors, warning, invalid_fields = pre_check_incoming_fields(validated_data, required_fields,
                                                additional_fields, action, obj, ShopHasDiffForm, 'магазина')
        if errors:
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
            raise ValidationError(detail={**errors, **invalid_fields})

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
            is_exists, errors_msg = is_validate_exists_shop(validated_data)
            if not is_exists:
                raise ValidationError(detail={'shops': errors_msg})

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
    """ Сериализатор для отображения и сохранения товара.
    """
    category = CategorySerializer(required=False)

    class Meta:
        model = models.Product
        fields = ['id', 'name', 'category']
        extra_kwargs = {
            'id': {'read_only': True},
        }


class ProductParameterSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения и сохранения характеристик товара.
    """
    parameter = serializers.StringRelatedField()

    class Meta:
        model = models.ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения и сохранения дополнительных сведений товара.
    """
    product = ProductSerializer(read_only=True)
    shop = serializers.StringRelatedField()
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = models.ProductInfo
        fields = ['id', 'model', 'catalog_number', 'product', 'shop', 'quantity', 'price_rrc', 'product_parameters']
        read_only_fields = ['id']


class ShortOrderItemSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения товара в сокращённом формате.
    """
    product = serializers.StringRelatedField(source='product_info', read_only=True)

    class Meta:
        model = models.OrderItem
        fields = ['product', 'quantity']


class OrderListSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения списка заказов.
    """
    state = serializers.CharField(source='get_state_display', read_only=True)
    ordered_items = ShortOrderItemSerializer(read_only=True, many=True)
    contact = ShortContactSerializer(read_only=True)

    class Meta:
        model = models.Order
        fields = ['id', 'state', 'updated_state', 'ordered_items', 'sum', 'contact', 'created_at']
        read_only_fields = ['id', 'updated_state', 'sum', 'created_at']
