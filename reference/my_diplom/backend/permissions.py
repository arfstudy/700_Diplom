from rest_framework import permissions


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


class ShopPermissions(permissions.BasePermission):
    """ Класс для разрешения на создание и удаление магазинов только администраторам или суперпользователям.
        Просмотр списка магазинов, изменение отдельных полей всем авторизованным.
    """

    def has_permission(self, request, view):
        """ Проверяет клиента на то, что он является администратором или суперпользователем или авторизованным.
        """
        if request.method in permissions.SAFE_METHODS or request.method == 'PATCH':
            # Если полученный метод безопасный или 'PATCH', то права доступа предоставляются авторизованным.
            return bool(request.user and request.user.is_authenticated)

        # POST-метод предоставляется администраторам или суперпользователям.
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))

    def has_object_permission(self, request, view, obj):
        """ Проверяет клиента на то, что он является авторизованным.
        """
        if request.method in permissions.SAFE_METHODS or request.method == 'PATCH':
            # Если полученный метод безопасный или 'PATCH', то права доступа предоставляются авторизованным.
            return bool(request.user and request.user.is_authenticated)

        # PUT и DELETE-методы предоставляется администраторам или суперпользователям.
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))


class IsAuthenticatedPermissions(permissions.BasePermission):
    """ Класс для разрешения на просмотр всем авторизованным.
    """

    def has_permission(self, request, view):
        """ Проверяет клиента на то, что он является авторизованным.
        """
        return bool(request.user and request.user.is_authenticated)


class IsOwnerPermissions(permissions.BasePermission):
    """ Класс для разрешения на внесение исправлений в объекты только их авторам."""

    def has_object_permission(self, request, view, obj):
        """ Проверяет клиента на то, что он является автором объекта.
        """
        return bool(request.user and request.user == obj.user)
