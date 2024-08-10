from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from backend import models, serializers
from backend.permissions import IsAdminOrReadOnly, ShopPermission, IsAuthenticatedPermissions, IsOwnerPermissions
from backend.services import get_contacts, get_short_contacts, get_shops, get_products_list, get_orders_list

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
    """ Класс для создания, просмотра, изменения и удаления Магазина.
    """
    queryset = models.Shop.objects.all()
    serializer_class = serializers.ShopSerializer

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных.
        """
        return get_shops(self)

    def get_permissions(self):
        """ Определяет разрешения в зависимости от действий.
        """
        # Просматривать могут авторизованные пользователи.
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]

        # Обновлять определённые поля могут определённые категории пользователей.
        if self.action == 'partial_update':
            return [ShopPermission()]

        # Остальные действия разрешены только администраторам.
        return [IsAdminUser()]

    @staticmethod
    def short_shop(shop):
        """ Отображает только часть полей магазина, и в компактном виде.
        """
        return [f"{shop['id']}: {shop['name']}, state={shop['state']}, seller={shop['seller']}, buyer={shop['buyer']}"]

    def list(self, request, *args, **kwargs):
        """ Возвращает список магазинов.
        """
        kwargs['many'] = True
        content = self.retrieve(request, *args, **kwargs)
        page = self.paginate_queryset(content)
        if page is not None:
            return self.get_paginated_response(data=page)

        return Response(data={'shops': content}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """ Возвращает один магазин или несколько, со всеми полями или в сокращённом виде.
        """
        is_many = kwargs.get('many', False)
        instance = self.get_queryset() if is_many else self.get_object()
        if self.request.user.is_staff:
            # Возвращает все поля магазина.
            shop_ser = serializers.ShopSerializer(instance=instance, many=is_many)
            if is_many:
                return shop_ser.data

            return Response(data=shop_ser.data, status=status.HTTP_200_OK)

        # Возвращает магазин в сокращённом виде.
        shop_ser = serializers.ShortShopSerializer(instance=instance, many=is_many)
        if is_many:
            return [self.short_shop(e) for e in shop_ser.data]

        return Response(data={'shop': self.short_shop(shop_ser.data)}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """ Удаляет магазин.
        """
        pk = kwargs.get('pk', None)
        shop = self.get_object()
        shop.delete()
        return Response(data={'detail': [f'Магазин с id={pk} удалён.']}, status=status.HTTP_204_NO_CONTENT)


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
