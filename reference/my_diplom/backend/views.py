from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import viewsets, status, generics, views
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from backend import models, serializers
from backend.permissions import IsAdminOrReadOnly, ShopPermission, IsBuyer, IsOwnerPermissions
from backend.services import (get_contacts, get_short_contacts, get_shops, get_shop, get_category, get_products,
                              get_product_infos, converting_categories_data, converting_products_data,
                              get_price, get_orders_list)
from backend.validators import validate_categories, delete_product_info, load_yaml_data, get_shop_obj

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

    @action(methods=['patch'], detail=True, url_path='drop_category')
    def drop_category(self, request, pk):
        """ Отвязывает указанные категории от магазина
            по запросу: PATCH 'http://127.0.0.1:8000/api/v1/backend/shop/<pk>/drop_category/'.
            Ключ 'category_ids' со списком отвязываемых категорий передаются в теле запроса 'body'.
        """
        shop = self.get_object()
        # Находим подходящие категории.
        categories, errors_msg = validate_categories(request, shop)
        yes_remove, not_remove, content, state = [], [], dict(), status.HTTP_200_OK
        if categories:
            for category in categories:
                # Проверяет, что в Магазине нет Товаров выбранной Категории.
                if models.Product.objects.filter(category=category, product_infos__shop=shop).exists():
                    not_remove.append(category)
                else:
                    yes_remove.append(category)

            if yes_remove:
                shop.categories.remove(*yes_remove)
                content = {**content, 'Из этого Магазина удалены Категории': [str(c) for c in yes_remove]}

            if not_remove:
                content = {**content,
                           'Из этого Магазина нельзя удалить Категории, так как у них есть зависимые Товары.':
                               [str(c) for c in not_remove]}
        else:
            content = {'error': 'Нету категорий, которые можно удалить.'}
            state = status.HTTP_400_BAD_REQUEST

        if errors_msg:
            content = {**content, 'not_found_categories': errors_msg}

        return Response(data={**content, 'shop': serializers.ShopSerializer(instance=shop).data}, status=state)


class CategoryView(viewsets.ModelViewSet):
    """ Класс для создания, просмотра, изменения и удаления Категории.
    """
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    # Показывает категории определённого магазина. Команда: '.../?shop_name=<shop_name>'.
    search_fields = ['shops__name']
    SearchFilter.search_param = 'shop_name'

    def create(self, request, *args, **kwargs):
        """ Создаёт новую категорию.
        """
        category_ser = serializers.CategorySerializer(data=request.data)
        category_ser.is_valid(raise_exception=True)
        category_ser.save()
        # Получает предупреждение, если не все магазины оказались существующими.
        warning = category_ser.context.pop('warning', {})
        return Response(data={**category_ser.data, **warning}, status=status.HTTP_201_CREATED)

    @action(methods=['patch'], detail=True, url_path='drop_shop')
    def drop_shop(self, request, pk):
        """ Отвязывает категорию от указанного магазина
            по запросу: PATCH 'http://127.0.0.1:8000/api/v1/backend/category/<pk>/drop_shop/'.
            'id' отвязываемого магазина передаётся в теле запроса 'body'.
        """
        category = get_category(pk)
        if not category:
            raise NotFound(detail={'category': [f'Категория с id={pk} не существует.']})

        shop_id = int(request.data.get('shop_id', 0))
        shop = get_shop(shop_id)
        if not shop:
            raise NotFound(detail={'shop': [f'Магазин с id={shop_id} не существует.']})

        # Проверяет, что в Магазине нет Товаров выбранной Категории.
        if models.Product.objects.filter(category=category, product_infos__shop=shop).exists():
            content = {'detail':
                           f'Эту Категорию нельзя удалить из Магазина `{shop.name}`, так как есть зависимые Товары.'}
            state = status.HTTP_405_METHOD_NOT_ALLOWED
        else:
            category.shops.remove(shop)
            content = {'detail': f'Эта Категория удалена из Магазина `{shop.name}`.'}
            state = status.HTTP_200_OK

        return Response(data={**content, 'category': serializers.CategorySerializer(instance=category).data},
                        status=state)


class ProductView(viewsets.ModelViewSet):
    """ Класс для создания, просмотра, изменения и удаления Товара.
    """
    queryset = models.Product.objects.all()
    serializer_class = serializers.ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных.
        """
        return get_products(self)

    def destroy(self, request, *args, **kwargs):
        """ Удаляет Товар.
        """
        pk = kwargs.get('pk', None)
        prod = self.get_object()
        if  prod.product_infos.exists():
            return Response(data={'detail': [
                                    f'Нельзя удалить Товар с id={pk}, так как у него есть зависимые Описания товара.',
                                    'Удаление Товара так же происходит при удалении последнего Описания.']},
                            status=status.HTTP_405_METHOD_NOT_ALLOWED)
        prod.delete()
        return Response(data={'detail': [f'Товар с id={pk} удалён.']}, status=status.HTTP_204_NO_CONTENT)


class ProductInfoView(viewsets.ModelViewSet):
    """ Класс для создания, просмотра, изменения и удаления Описания товара.
    """
    queryset = models.ProductInfo.objects.all()
    serializer_class = serializers.ProductInfoSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных.
        """
        return get_product_infos(self)

    def destroy(self, request, *args, **kwargs):
        """ Удаляет Описание товара.
        """
        with transaction.atomic():
            result = delete_product_info(self.get_object())
        content = [f'Описание товара с id(info_id)={result['id']} удалено.']
        if 'product' in result.keys():
            content += [f'Товар `{result['product']}` удалён.']
        if 'category' in result.keys():
            content += [f'В Категорию `{result['category']}` больше не входит ни один Товар.']

        return Response(data={'detail': content}, status=status.HTTP_204_NO_CONTENT)


class PartnerUpdate(views.APIView):
    """ Класс для обновления прайса от поставщика.
    """
    permission_classes = [IsBuyer]

    def post(self, request, *args, **kwargs):
        """ Загружает новый товар.
        """
        data = load_yaml_data(request)

        shop_obj = get_shop_obj(request, data['shop'])
        shop_obj.filename = request.data.get('url')
        shop_obj.save(update_fields=['filename'])
        if 'categories' in data.keys():
            # Выделяет Категории, которых нет, подготавливает данные и сохраняет через сериализатор.
            categories_data = converting_categories_data(data['categories'])
            if categories_data:
                category_ser = serializers.CategorySerializer(data=categories_data, many=True)
                category_ser.is_valid(raise_exception=True)
                category_ser.save()

        setattr(self, 'action', 'create')
        # Подготавливает данные к сохранению Описания товара через сериализатор.
        products_data = converting_products_data(data['goods'], shop_obj.name)
        products, all_num, new_num, skip_num, errors = [], len(products_data), 0, 0, {}
        for prod_data in products_data:
            # Товары сохраняются в БД по одному.
            # При ошибке пропустится сохранение только одного, ошибочного, Товара, а не всего пакета.
            product_ser = serializers.ProductInfoSerializer(data=prod_data, context={'view': self})
            if product_ser.is_valid():
                try:
                    product_ser.save()
                except ValidationError as e:
                    errors[f'{prod_data['external_id']}'] = str(e)
                    skip_num += 1
                else:
                    products.append(product_ser.data)
                    new_num += 1 if product_ser.context.pop('created', False) else 0
            else:
                if product_ser.errors['external_id'][0].code == 'unique':
                    errors[f'{prod_data['external_id']}'] = product_ser.errors['external_id']
                else:
                    errors[f'{prod_data['external_id']}'] = product_ser.errors
                skip_num += 1

        if all_num == 0:
            return Response(data=[{'detail': ['У этого источника пустой список товаров.']}],
                            status=status.HTTP_204_NO_CONTENT)

        msg = [f'Получено товаров `{all_num}`', f'Пропущено `{skip_num}`', f'Загружено `{new_num}`']
        if all_num == skip_num:
            return Response(data=[{'detail': ['Возможно, этот файл уже загружен.'] + msg}] + [errors],
                            status=status.HTTP_208_ALREADY_REPORTED)

        return Response(data=[{'detail': ['Загрузка выполнена.'] + msg}] + products, status=status.HTTP_201_CREATED)


class PriceView(generics.ListAPIView):
    """ Класс для просмотра Прайса (списка товаров с дополнительными сведениями).
    """
    queryset = models.ProductInfo.objects.all()
    serializer_class = serializers.PriceSerializer
    permission_classes = [IsAuthenticated]
    # Находит Товары определённого названия (сочетания символов в названии). Команда: '.../?prod_name=<prod_name>'.
    search_fields = ['product__name']
    SearchFilter.search_param = 'prod_name'

    def get_queryset(self):
        """ Изменяет перечень возвращаемых данных с учётом фильтров,
            сортирует отображение.
        """
        return get_price(self)


class OrderView(viewsets.ModelViewSet):
    """ Класс для просмотра Заказа.
    """
    queryset = models.Order.objects.all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ Возвращает Пользователю список его Заказов, кроме удалённых.
            Администраторам доступны Заказы всех Пользователей, в том числе, удалённые.
        """
        queryset = (self.queryset if self.request.user.is_staff
                    else self.queryset.exclude(state=models.Order.Status.DELETE).filter(customer=self.request.user))

        pk = int(self.kwargs.get("pk", 0))
        if pk > 0:
            queryset = self.queryset.filter(pk=pk)
            if not queryset:
                raise NotFound(f'У Вас нет Заказа с id={pk}.')

        return queryset
