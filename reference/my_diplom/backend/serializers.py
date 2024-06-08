from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apiauth.validators import pre_check_incoming_fields
from backend.forms import ContactHasDiffForm
from backend import models
from backend.services import get_transmitted_obj
from backend.validators import to_internal_value_after_pre_check


class ContactSerializer(serializers.ModelSerializer):
    """ Сериализатор для отображения и сохранения отдельного контакта пользователя.
    """
    salesman_id = serializers.CharField(source='salesman.id', read_only=True)
    salesman = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = models.Contact
        fields = ['id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone', 'salesman_id',
                  'salesman']
        read_only_fields = ['id']

    def to_internal_value(self, validated_data):
        """ Добавляет собственные проверки: наличие обязательных полей, присутствие реальных изменений,
            отсеивание неликвидных полей, проверка и подготовка choice-параметров.
        """
        # Проверяем полученных поля на корректность.
        required_fields = {'city', 'street', 'house'}
        additional_fields = {'structure', 'building', 'apartment', 'phone'}
        action, obj = get_transmitted_obj(self, required_fields)
        res, errors, choice_errors, warning, invalid_fields = pre_check_incoming_fields(validated_data, required_fields,
                                                additional_fields, action, obj, ContactHasDiffForm, 'контакта')
        if errors:
            instance = ({'contact': ContactSerializer(instance=obj).data}
                        if action in ['update', 'partial_update'] else {})
            raise ValidationError(detail={**errors, **warning, **instance, **invalid_fields})

        # Проверяем полученных поля на корректность значений.
        ret, errors = to_internal_value_after_pre_check(self, res)

        if errors:
            raise ValidationError(detail={**errors, **invalid_fields})

        return ret
