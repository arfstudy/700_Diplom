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


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    """ Класс для отображения категорий товаров в административной панеле.
    """
    list_display = ['id', 'name', 'catalog_number']
    list_display_links = ['id', 'name']
    search_fields = ['name', 'catalog_number']
    ordering = ['-id']


@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    """ Класс для отображения товаров в административной панеле.
    """
    list_display = ['id', 'name', 'category']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    ordering = ['-id']


@admin.register(models.ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """ Класс для отображения описания товаров в административной панеле.
    """
    list_display = ['id', 'product', 'model', 'catalog_number', 'shop', 'quantity', 'price', 'price_rrc']
    list_display_links = ['id', 'model']
    search_fields = ['model', 'catalog_number']
    ordering = ['-id']


@admin.register(models.Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """ Класс для отображения характеристик товаров в административной панеле.
    """
    list_display = ['id', 'name']
    list_display_links = ['id', 'name']
    search_fields = ['name']
    ordering = ['-id']


@admin.register(models.ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """ Класс для отображения значений характеристики товара в административной панеле.
    """
    list_display = ['id', 'parameter', 'value', 'product_info']
    list_filter = ['parameter', 'product_info']
    search_fields = ['value']
    list_editable = ['value']
    ordering = ['-id']


class OrderItemInLine(admin.TabularInline):
    """ Класс для отображения товаров из заказа в административной панеле.
        Промежуточная таблица с дополнительными полями, встраиваемая в отображение ведущей.
    """
    model = models.OrderItem
    extra = 0


@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    """ Класс для отображения заказов в административной панеле.
    """
    list_display = ['id', 'state', 'updated_state', 'contact', 'customer', 'created_at']
    list_display_links = ['id', 'updated_state', 'created_at']
    list_filter = ['state', 'customer']
    search_fields = ['updated_state', 'created_at']
    ordering = ['-id']
    inlines = [OrderItemInLine]
