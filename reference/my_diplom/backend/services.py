from django.contrib.auth import get_user_model
from django.core.exceptions import MultipleObjectsReturned
from django.db.models import Q
from rest_framework.exceptions import NotFound, ValidationError

from apiauth.services import verify_choices
from backend.models import Contact, Shop, ProductInfo, Order, Category

Salesman = get_user_model()


def get_contacts(user, pk=0):
    """ Возвращает контакты пользователя из БД.
    """
    if pk == 0:
        return Contact.objects.filter(salesman__id=user.id)

    contact = Contact.objects.filter(salesman__id=user.id).filter(pk=pk)
    if not contact:
        raise NotFound(f'У Вас нет контакта с id={pk}.')

    return contact


def get_transmitted_obj(obj_ser, obj_fields):
    """ Возвращает объект заданного класса, реальный или абстрактный с пустыми значениями.
    """
    obj = None
    action = obj_ser.context['view'].action
    if action == 'create':
        obj_data = {e: 'None' for e in obj_fields}
        obj = obj_ser.Meta.model(**obj_data)
    elif action in ['update', 'partial_update']:
        obj = obj_ser.instance

    return action, obj


def get_short_contacts(salesman, serializers_modul):
    """ Возвращает контакты пользователя из БД и отображает в сокращённом виде.
    """
    salesman_serializer = serializers_modul.ShortSalesmanSerializer(instance=salesman)
    contacts = salesman.contacts.all()
    contacts_serializer = serializers_modul.ShortContactSerializer(instance=contacts, many=True)
    return {'customer': salesman_serializer.data['customer'],
            'contacts': [e[k] for e in contacts_serializer.data for k in e.keys()]}


def get_shops(shop_view):
    """ Возвращает магазины в зависимости от запроса.
    """
    if 'pk' in shop_view.kwargs.keys():
        queryset = shop_view.queryset.filter(pk=shop_view.kwargs['pk'])
        if not queryset:
            raise NotFound(f'Магазин с id={shop_view.kwargs['pk']} не найден.')
        return queryset

    queryset = shop_view.queryset.filter(state=Shop.Worked.OPEN)
    if 'shop' in shop_view.request.GET.keys():
        if shop_view.request.GET['shop'] == 'all':
            queryset = shop_view.queryset
        elif shop_view.request.GET['shop'] == 'close':
            queryset = shop_view.queryset.filter(state=Shop.Worked.CLOSE)

    category_id = shop_view.request.GET.get('category_id', '')
    category_number = shop_view.request.GET.get('category_number', '')
    category_name = shop_view.request.GET.get('category_name', '')
    if category_id:
        return queryset.filter(categories__id=category_id)

    if category_number:
        return queryset.filter(categories__catalog_number=category_number)

    if category_name:
        return queryset.filter(categories__name__icontains=category_name)

    return queryset


def get_shop(param):
    """ Возвращает объект магазина по ключам 'pk' или 'name'.
    """
    try:
        shop = Shop.objects.get(pk=param)
    except (TypeError, ValueError, OverflowError, Shop.DoesNotExist, ValidationError):
        pass
    else:
        return shop
    try:
        shop = Shop.objects.get(name=param)
    except (TypeError, ValueError, OverflowError, Shop.DoesNotExist, ValidationError):
        return None

    return shop


def join_choice_errors(errors, choice_errors):
    """ Объединяет тексты ошибок Choice-полей.
    """
    for key in choice_errors.keys():
        if key in errors.keys():
            errors[key] += choice_errors[key]
        else:
            errors[key] = choice_errors[key]

    return


def replace_salesmans_errors(errors, res):
    """ Заменяет тексты ошибок продавцов.
    """
    for field in ['seller', 'buyer']:
        if field in errors.keys():
            if errors[field][0].startswith('Магазин с таким ') and errors[field][0].endswith(' уже существует.'):
                errors[field] = [f'Пользователь с id={res[field]} уже является менеджером одного из магазинов.']

            if errors[field][0].startswith('Недопустимый пер') and errors[field][0].endswith('т не существует.'):
                errors[field] = [f'Пользователь с id={res[field]} не найден.']
    return


def get_category(param):
    """ Возвращает объект категории по ключам 'pk' или 'name'.
        Но НЕ 'catalog_number', поля должны быть разных типов. Тип 'int' занят 'pk'.
    """
    try:
        category = Category.objects.get(pk=param)
    except (TypeError, ValueError, OverflowError, Category.DoesNotExist, MultipleObjectsReturned, ValidationError):
        pass
    else:
        return category
    try:
        category = Category.objects.get(name=param)
    except (TypeError, ValueError, OverflowError, Category.DoesNotExist, MultipleObjectsReturned, ValidationError):
        return None

    return category


def get_category_by_name_and_catalog_number(name='', catalog_number=0):
    """ Находит категорию с полученными значениями полей 'name' и 'catalog_number' или одному из них.
        Попутно проверяется корректность сочетания этих полей, если переданы оба параметра.
    """
    if not name and not catalog_number:
        raise ValidationError(detail={'errors': ['Необходимо передать хотя бы один из параметров `name`'
                                                 ' или `catalog_number`.']})

    error_msg = [f'Категория с названием `{name}` не соответствует номеру по каталогу `{catalog_number}`.']
    if name and Category.objects.filter(name=name).exists():
        category = Category.objects.get(name=name)
        if catalog_number != 0 and catalog_number != category.catalog_number:
            raise ValidationError(detail={'errors': error_msg})

        return category

    if catalog_number != 0 and Category.objects.filter(catalog_number=catalog_number).exists():
        if name:
            raise ValidationError(detail={'errors': error_msg})

        return Category.objects.get(catalog_number=catalog_number)

    return None


def get_category_by_catalog_number(validated_data):
    """ Возвращает категорию, если передан её номер по каталогу 'catalog_number'.
    """
    data = validated_data.copy()
    category = data.pop('category', {})
    if category:
        category_obj = get_category_by_name_and_catalog_number(catalog_number=category['catalog_number'])
        return category_obj, data

    return None, validated_data


def get_products_list(self):
    """ Возвращает Прайс, список товаров.
        Регулирует перечень возвращаемых данных в зависимости от запрошенных параметров.
    """
    query = Q(shop__state=Shop.Worked.OPEN) & Q(quantity__gt=0)
    shop_id = self.request.GET.get('shop_id')
    category_id = self.request.GET.get('category_id')

    if shop_id:
        query = query & Q(shop_id=shop_id)

    if category_id:
        query = query & Q(product__category_id=category_id)

    # Фильтруем и отбрасываем дубликаты.
    queryset = ProductInfo.objects.filter(query).select_related('shop', 'product__category').prefetch_related(
        'product_parameters__parameter').distinct()

    return queryset


def get_orders_list(order_view, serializers_modul):
    """ Возвращает список заказов.
        Регулирует перечень возвращаемых данных в зависимости от запрошенных параметров.
    """
    query = Q(customer=order_view.request.user)
    # Возможные варианты состояния заказа: 'basket', 'new', 'confirmed', 'assembled', 'sent', 'canceled', 'received'.
    # Так же возможны значения, сохраняемые в БД, и человеко читаемые значения - все регистронезависимые.
    if 'state' in order_view.request.GET.keys():
        value = order_view.request.GET['state']
        # Проверяем query-параметр 'state' на принадлежность к значениям перечисляемого типа.
        value, errors = verify_choices(value, Order.Status)
        if errors:
            errors = {'errors': [f'Неправильное значение query-параметра `state={value}`.'] + [errors['errors']]}
            raise ValidationError(detail=errors)

        query = query & Q(state=value)

    queryset = Order.objects.filter(query).select_related('contact').prefetch_related(
        'ordered_items', 'ordered_items__product_info').distinct()

    items_serializer = serializers_modul.OrderListSerializer(instance=queryset, many=True)

    return items_serializer.data
