from collections import OrderedDict
from collections.abc import Mapping

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail, SkipField
from rest_framework.settings import api_settings


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
