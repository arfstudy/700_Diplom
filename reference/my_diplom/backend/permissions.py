from rest_framework import permissions


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
