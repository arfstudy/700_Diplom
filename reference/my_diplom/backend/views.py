from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, MethodNotAllowed
from rest_framework.response import Response

from backend import models, serializers
from backend.permissions import IsAdminOrReadOnly, ShopPermissions, IsAuthenticatedPermissions, IsOwnerPermissions
from backend.services import get_contacts, get_short_contacts, get_list_shops, get_products_list, get_orders_list

Salesman = get_user_model()


class ContactModelView(viewsets.ModelViewSet):
    """ Класс для создания, просмотра, изменения и удаления Контакта пользователя.
    """
    serializer_class = serializers.ContactSerializer

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных (один или все).
        """
        pk = self.kwargs.get("pk", 0)
        return get_contacts(self.request.user, pk)


class ContactsListView(viewsets.GenericViewSet):
    """ Класс для просмотра Контактов пользователя в сокращённом виде.
    """
    permission_classes = [IsAdminOrReadOnly]

    @staticmethod
    def list(request):
        """ Возвращает Контакты пользователя, который выполнил запрос.
        """
        return Response(data=get_short_contacts(request.user, serializers), status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='all')
    def salesmans_all_contacts(self, request):
        """ Возвращает контакты всех пользователей
            по запросу: GET 'http://127.0.0.1:8000/api/v1/backend/short_contacts/all/'.
            Примечание: Только для администраторов и суперпользователей.
        """
        salesmans_list = []
        for salesman in Salesman.objects.all().prefetch_related('contacts'):
            res = get_short_contacts(salesman, serializers)
            res['salesman'] += f', is_active={salesman.is_active}'
            salesmans_list.append(res)

        page = self.paginate_queryset(salesmans_list)
        if page is not None:
            return self.get_paginated_response(data=page)

        return Response(data=salesmans_list, status=status.HTTP_200_OK)


class ShopView(viewsets.ModelViewSet):
    """ Класс для работы с моделью магазина.
    """
    queryset = models.Shop.objects.all()
    serializer_class = serializers.ShopSerializer
    permission_classes = [ShopPermissions]

    def list(self, request, *args, **kwargs):
        """ Возвращает список магазинов в сокращённом виде.
        """
        return Response(data=get_list_shops(self, serializers), status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """ Удаляет магазин.
        """
        pk = kwargs.get('pk', None)
        if not pk:
            raise MethodNotAllowed('Удаление не возможно.')
        try:
            shop = models.Shop.objects.get(pk=pk)
        except:
            raise NotFound(f'Магазин с id={pk} не найден.')

        shop.delete()
        return Response(data={'detail': f'Магазин с id={pk} удалён.'}, status=status.HTTP_204_NO_CONTENT)


class CategoryView(generics.ListAPIView):
    """ Класс для просмотра модели категорий.
    """
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAuthenticatedPermissions]


class ProductInfoView(generics.ListAPIView):
    """ Класс для просмотра списка товаров (прайса) с дополнительными сведениями.
    """
    queryset = models.ProductInfo.objects.all()
    serializer_class = serializers.ProductInfoSerializer
    permission_classes = [IsAuthenticatedPermissions]

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных с учётом фильтров.
        """
        return get_products_list(self)


class BasketView(viewsets.GenericViewSet):
    """ Класс для работы с корзиной пользователя.

        Methods:
        - get: Retrieve the items in the user's basket.
        - post: Add an item to the user's basket.
        - put: Update the quantity of an item in the user's basket.
        - delete: Remove an item from the user's basket.

        Attributes:
        - None
    """
    queryset = models.Order.objects.all()
    permission_classes = [IsOwnerPermissions]

    def list(self, request, *args, **kwargs):
        """ Возвращает заказы пользователя, который выполнил запрос.
        """
        return Response(data=get_orders_list(self, serializers), status=status.HTTP_200_OK)
