from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from users.forms import AdminCreationUserForm

User = get_user_model()


@admin.register(User)
class UserAdmin(UserAdmin):
    """ Класс для работы с пользователями в административной панеле.
        Переопределены настройки с учётом отсутствия поля "username":
        "fieldsets", "add_fieldsets", "list_display" и "search_fields".
    """
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "email_verify",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None,
        {
            "classes": ("wide",),
            # Поля, отображаемые при создании пользователя.
            "fields": ("email", "password1", "password2", 'first_name', 'last_name'),
        },
    ),)
    add_form = AdminCreationUserForm

    list_display = ['id', 'email', 'first_name', 'last_name', 'email_verify', 'is_active', 'position', 'company']
    list_filter = ['email_verify', 'is_active', 'position']
    list_display_links = ['id', 'email']
    search_fields = ['email', 'first_name', 'last_name']
    list_editable = ['first_name', 'last_name']    # Поля, которые можно редактировать прямо в общем списке.
    ordering = ["-date_joined", 'first_name', 'last_name']
