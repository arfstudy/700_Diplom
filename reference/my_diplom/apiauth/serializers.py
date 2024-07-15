from django.contrib.auth import get_user_model
from rest_framework import serializers

from apiauth.validators import validate_names_fields

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """ Сериализатор для работы с моделью пользователя.
    """

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'id': {'read_only': True},
        }

    def validate(self, attrs):
        """ Проверяет, чтобы при create() и update() поля 'first_name' и 'last_name' содержали
            буквы одного, и совпадающего между собой, алфавита.
        """
        user = getattr(self, 'instance', None)

        attrs, is_valid, errors = validate_names_fields(attrs, user)

        if not is_valid:
            raise serializers.ValidationError({'errors': errors})

        return attrs
