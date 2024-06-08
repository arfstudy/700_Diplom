from rest_framework import viewsets

from backend import models, serializers
from backend.services import get_contacts


class ContactModelView(viewsets.ModelViewSet):
    """ Класс для создания, просмотра, изменения и удаления контакта пользователя.
    """
    serializer_class = serializers.ContactSerializer

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных (один или все).
        """
        pk = self.kwargs.get("pk", 0)
        return get_contacts(self.request.user, pk)
