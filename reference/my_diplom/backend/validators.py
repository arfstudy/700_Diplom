from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from backend.models import Shop


def is_not_salesman(obj_ser, salesman):
    """ Проверяет, что пользователь активен и не является менеджером какого-нибудь магазина.
    """
    if salesman:
        if not salesman.is_active:
            raise ValidationError(f'Пользователь с id={salesman.id} был удалён. Обратитесь к администратору сайта.')

        msg = f'Пользователь с id={salesman.id} уже является Менеджером одного из магазинов.'
        if obj_ser.context['view'].action == 'create':
            if bool(salesman and Shop.objects.filter(Q(buyer=salesman) | Q(seller=salesman)).exists()):
                raise ValidationError(msg)

        elif obj_ser.context['view'].action in ['update', 'partial_update']:
            if Shop.objects.exclude(id=obj_ser.instance.id).filter(Q(buyer=salesman) | Q(seller=salesman)).exists():
                raise ValidationError(msg)

    return salesman


def validate_manager(manager, position, value, user, position_text, employee, errors):
    """ Проверяет пользователя на возможность вносить изменения в магазин.
    """
    # Проверяет пользователя.
    if user == manager or user == employee:
        errors[position] = ['Вы уже являетесь работником этого магазина.']
    elif Shop.objects.filter(Q(buyer=user) | Q(seller=user)).exists():
        errors[position] = ['Вы уже являетесь Менеджером одного из магазинов.']

    # Проверяет магазин.
    if value:
        if manager is not None:
            errors[position] = errors.get(position, []) + [f'В этом магазине уже есть Менеджер по {position_text}.']
        if user != value:
            errors[position] = errors.get(position, []) + ['Вы не можете назначить Менеджером другого человека'
                                                           ', только себя.']
    else:  # if value is None
        if bool(manager and user != manager):
            errors[position] = errors.get(position, []) + ['Вы можете уволить из Менеджеров только самого себя.']

    return


def is_permission_updated(obj_ser, attrs):
    """ Проверяет каждое поле, чтобы изменения вносили определённые категории пользователей:
        Создать или удалить магазин, изменить название может только администратор или суперпользователь;
        Записаться в "Менеджеры" может любой авторизованный, но только в случае, если "вакансия свободна";
        Удалиться из "Менеджеров" может действующий "Менеджер";
        Задать или изменить путь загрузочного файла может "Менеджер по закупкам";
        Изменить статус магазина может "Менеджер по продажам".
    """
    errors = dict()
    user = obj_ser.context['request'].user
    if bool(user and not (user.is_staff or user.is_superuser)) and user.is_authenticated:
        if 'name' in attrs.keys():
            errors['name'] = ['Ваш статус не подходит для изменения этого поля.']
        shop = obj_ser.instance
        if 'state' in attrs.keys() and user != shop.seller:
            errors['state'] = ['Вы не занимаете подходящую должность для изменения этого поля.']
        if 'filename' in attrs.keys() and user != shop.buyer:
            errors['filename'] = ['Вы не занимаете подходящую должность для изменения этого поля.']
        if 'seller' in attrs.keys():
            validate_manager(shop.seller, 'seller', attrs['seller'], user, 'продажам', shop.buyer, errors)
        if 'buyer' in attrs.keys():
            validate_manager(shop.buyer, 'buyer', attrs['buyer'], user, 'закупкам', shop.seller, errors)

    if errors:
        raise PermissionDenied(detail=errors)

    return


def not_salesman(user):
    """ Проверяет, что пользователь не является менеджером какого-нибудь магазина.
    """
    if Shop.objects.filter(Q(buyer=user) | Q(seller=user)).exists():
        return False

    return True
