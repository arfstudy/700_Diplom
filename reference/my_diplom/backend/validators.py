from collections import OrderedDict
from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.fields import get_error_detail, SkipField
from rest_framework.settings import api_settings

from backend.models import Shop


def to_internal_value_after_pre_check(serializer_obj, validated_data):
    """ Переопределяет встроенный генератор выбора полей, которые могут работать на запись.
        Добавляет собственную проверку choice-параметров (например 'position' и т.п.) так,
        чтобы она выполнялась раньше стандартной 'field.run_validation(primitive_value)'.
    """
    if not isinstance(validated_data, Mapping):
        message = serializer_obj.error_messages['invalid'].format(
            datatype=type(validated_data).__name__
        )
        raise ValidationError({
            api_settings.NON_FIELD_ERRORS_KEY: [message]
        }, code='invalid')

    ret = OrderedDict()
    errors = OrderedDict()
    fields = serializer_obj._writable_fields

    for field in fields:
        validate_method = getattr(serializer_obj, 'validate_' + field.field_name, None)
        primitive_value = field.get_value(validated_data)
        try:
            validated_value = field.run_validation(primitive_value)
            if validate_method is not None:
                validated_value = validate_method(validated_value)
        except ValidationError as exc:
            errors[field.field_name] = exc.detail
        except DjangoValidationError as exc:
            errors[field.field_name] = get_error_detail(exc)
        except SkipField:
            pass
        else:
            serializer_obj.set_value(ret, field.source_attrs, validated_value)

    return ret, errors


def validate_manager(manager, position, value, user, position_text, errors):
    """ Проверяет пользователя на причастность к магазинам.
    """
    if value:
        if Shop.objects.filter(Q(buyer=user) | Q(seller=user)).exists():
            errors[position] = ['Вы уже являетесь Менеджером одного из магазинов.']
        if manager is not None:
            errors[position] = errors.get(position, []) + [f'В этом магазине уже есть Менеджер по {position_text}.']
        if value != user:
            errors[position] = errors.get(position, []) + ['Вы не можете назначить Менеджером другого человека.']
    else:  # if value is None
        if bool(manager and manager != user):
            errors[position] = ['Вы можете уволить из Менеджеров только самого себя.']

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
            errors['state'] = ['Ваша должность не подходит для изменения этого поля.']
        if 'filename' in attrs.keys() and user != shop.buyer:
            errors['filename'] = ['Ваша должность не подходит для изменения этого поля.']
        if 'seller' in attrs.keys():
            validate_manager(shop.seller, 'seller', attrs['seller'], user, 'продажам', errors)
        if 'buyer' in attrs.keys():
            validate_manager(shop.buyer, 'buyer', attrs['buyer'], user, 'закупкам', errors)

    if errors:
        raise PermissionDenied(detail=errors)

    return
