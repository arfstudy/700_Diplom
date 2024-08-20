from rest_framework import permissions

from backend.validators import not_salesman, validate_manager
from users.services import get_user


class IsAdminOrReadOnly(permissions.BasePermission):
    """ Класс для разрешения на просмотр всем авторизованным.
    """

    def has_permission(self, request, view):
        """ Проверяет клиента на то, что он является авторизованным или администратором.
        """
        if view.action in ['list', 'retrieve', 'head', 'options']:
            # Если полученный метод только на чтение, "безопасный", то права доступа предоставляются авторизованным.
            return bool(request.user and request.user.is_authenticated)

        # Иначе права доступа предоставляются администраторам или суперпользователям.
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class ShopPermission(permissions.BasePermission):
    """ Проверяет клиента на право доступа к магазину.
    """
    message = 'У вас недостаточно прав для выполнения данного действия.'

    def has_object_permission(self, request, view, obj):
        """ Проверяет обратившегося клиента.
        """
        if view.action == 'partial_update' and bool(request.user):
            is_staff = request.user.is_staff
            is_super = request.user.is_superuser
            if 'category_ids' in request.data.keys():
                # Поле 'category_ids' можно менять только администратору.
                self.message = 'Ваш статус не подходит для изменения поля `category_ids`.'
                return is_staff or is_super

            if 'name' in request.data.keys():
                # Поле 'name' можно менять только администратору.
                self.message = 'Ваш статус не подходит для изменения поля `name`.'
                return is_staff or is_super

            user = request.user
            self.message = 'Вы не занимаете подходящую должность для изменения поля '
            is_sl = bool(obj.seller) and user.id == obj.seller.id
            if 'state' in request.data.keys():
                # Поле 'state' можно менять Менеджеру по продажам своего магазина или администратору.
                self.message += '`state`.'
                return is_sl or is_staff or is_super

            is_br = bool(obj.buyer) and user.id == obj.buyer.id
            if 'filename' in request.data.keys():
                # Поле 'filename' можно менять Менеджеру по закупкам своего магазина или администратору.
                self.message += '`filename`.'
                return is_br or is_staff or is_super
            sl_v = 'seller' in request.data.keys()
            br_v = 'buyer' in request.data.keys()
            # В запросе должно передаваться только одно из полей 'buyer' или 'seller'.
            # Если передано оба поля, то разрешение выдаётся только администратору.
            if (sl_v or br_v) and (not sl_v or not br_v):
                manager, position, v_id, position_text, employee, errors, is_mg = None, '', '0', '', None, {}, False
                if sl_v:
                    # Поле 'seller' можно менять авторизованному пользователю, не Менеджеру,
                    # или Менеджеру по продажам своего магазина.
                    manager, position, v_id = obj.seller, 'seller', request.data['seller']
                    position_text, employee, is_mg = 'продажам', obj.buyer, is_sl

                elif br_v:
                    # Поле 'buyer' можно менять авторизованному пользователю, не Менеджеру,
                    # или Менеджеру по закупкам своего магазина.
                    manager, position, v_id = obj.buyer, 'buyer', request.data['buyer']
                    position_text, employee, is_mg = 'продажам', obj.seller, is_br

                value = get_user(v_id)
                if value:
                    validate_manager(manager, position, value, user, position_text, employee, errors)
                    if errors:
                        self.message = errors
                    else:
                        self.message += f'`{position}`.'
                else:
                    self.message = {position: f'Пользователь с id={v_id} не найден.'}

                return request.user.is_authenticated and not_salesman(request.user) or is_mg

        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class IsOwnerPermissions(permissions.BasePermission):
    """ Класс для разрешения на внесение исправлений в объекты только их авторам."""

    def has_object_permission(self, request, view, obj):
        """ Проверяет клиента на то, что он является автором объекта.
        """
        return bool(request.user and request.user == obj.customer)
