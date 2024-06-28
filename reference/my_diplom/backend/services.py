from django.db.models import Q
from rest_framework.exceptions import NotFound, ValidationError

from backend.models import Contact, Shop


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


def get_salesman_contacts(salesman, serializers_modul):
    """ Возвращает контакты пользователя из БД и отображает в сокращённом виде.
    """
    salesman_serializer = serializers_modul.ShortSalesmanSerializer(instance=salesman)
    contacts = salesman.contacts.all()
    contacts_serializer = serializers_modul.ShortContactSerializer(instance=contacts, many=True)
    return {'salesman': salesman_serializer.data['salesman'],
            'contacts': [e[k] for e in contacts_serializer.data for k in e.keys()]}


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


def is_not_salesman(obj_ser, salesman):
    """ Проверяет, что пользователь активен и не является менеджером какого-нибудь магазина.
    """
    if salesman:
        if not salesman.is_active:
            raise ValidationError(f'Пользователь с id={salesman.id} был удалён. Обратитесь к администратору сайта.')

        msg = f'Пользователь с id={salesman.id} уже является менеджером одного из магазинов.'
        if obj_ser.context['view'].action == 'create':
            if bool(salesman and Shop.objects.filter(Q(buyer=salesman) | Q(seller=salesman)).exists()):
                raise ValidationError(msg)

        elif obj_ser.context['view'].action in ['update', 'partial_update']:
            if Shop.objects.exclude(id=obj_ser.instance.id).filter(Q(buyer=salesman) | Q(seller=salesman)).exists():
                raise ValidationError(msg)

    return salesman


def get_list_shops(shop_view, serializers_modul):
    """ Возвращает список магазинов в сокращённом виде.
    """
    queryset = shop_view.queryset
    if 'state' in shop_view.request.GET.keys():
        if shop_view.request.GET['state'] == 'open':
            queryset = queryset.filter(state=Shop.Worked.OPEN)
        elif shop_view.request.GET['state'] == 'close':
            queryset = queryset.filter(state=Shop.Worked.CLOSE)

    shop_serializer = serializers_modul.ShortShopSerializer(instance=queryset, many=True)
    return {'shops': [[f"{e['id']}: {e['name']}, state={e['state']}, seller={e['seller']}, buyer={e['buyer']}"]
                  for e in shop_serializer.data]}
