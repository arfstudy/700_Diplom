from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from backend import models, serializers
from backend.services import get_contacts, get_salesman_contacts

Salesman = get_user_model()


class ContactModelView(viewsets.ModelViewSet):
    """ Класс для создания, просмотра, изменения и удаления контакта пользователя.
    """
    serializer_class = serializers.ContactSerializer

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных (один или все).
        """
        pk = self.kwargs.get("pk", 0)
        return get_contacts(self.request.user, pk)


class ContactsListView(viewsets.GenericViewSet):
    """ Класс для просмотра контактов пользователя в сокращённом виде.
    """

    @staticmethod
    def list(request):
        """ Возвращает контакты пользователя, который выполнил запрос.
        """
        return Response(data=get_salesman_contacts(request.user, serializers), status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='all')
    def contacts_all_salesmans(self, request):
        """ Примечание: Только для администраторов и суперпользователей.
            Возвращает контакты всех пользователей
            по запросу: GET 'http://127.0.0.1:8000/api/v1/backend/short_contacts/all/'.
        """
        if bool(request.user and (request.user.is_staff or request.user.is_superuser)):
            salesmans_list = []
            for salesman in Salesman.objects.all().prefetch_related('contacts'):
                res = get_salesman_contacts(salesman, serializers)
                res['salesman'] += f', is_active={salesman.is_active}'
                salesmans_list.append(res)
            return Response(data=salesmans_list, status=status.HTTP_200_OK)

        raise NotFound('Page not found.')
