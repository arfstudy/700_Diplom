from django.contrib import admin

from backend import models


@admin.register(models.Contact)
class ContactAdmin(admin.ModelAdmin):
    """ Класс для отображения контактов пользователей в административной панеле.
    """
    list_display = ['id', 'salesman', 'phone', 'city', 'street', 'house', 'structure', 'building', 'apartment']
    list_display_links = ['id', 'salesman']
    list_filter = ['salesman', 'city']
    search_fields = ['phone', 'city', 'street', 'house', 'structure', 'building', 'apartment']
    list_editable = ['street', 'house', 'structure', 'building', 'apartment']


@admin.register(models.Shop)
class ShopAdmin(admin.ModelAdmin):
    """ Класс для отображения магазинов в административной панеле.
    """
    list_display = ['id', 'name', 'state', 'seller', 'buyer', 'filename']
    list_display_links = ['id', 'name']
    list_filter = ['state']
    search_fields = ['name', 'filename']
    ordering = ['-id']
