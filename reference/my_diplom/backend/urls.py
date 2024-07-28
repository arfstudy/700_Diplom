"""
URL configuration for users application.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from backend import views

app_name = 'backend'

router = DefaultRouter()
router.register(prefix='contact', viewset=views.ContactModelView, basename='contact')
router.register(prefix=r'short_contacts', viewset=views.ContactsListView, basename='short_contacts')
router.register(prefix='shop', viewset=views.ShopView, basename='shop')
router.register(prefix='category', viewset=views.CategoryView, basename='category')
router.register(prefix='product', viewset=views.ProductView, basename='product')
router.register(prefix='prod_info', viewset=views.ProductInfoView, basename='prod_info')
router.register(prefix='orders', viewset=views.BasketView, basename='orders')

urlpatterns = [
    # Работает с контактом пользователя.                http://127.0.0.1:8000/api/v1/backend/contact/
    # Показывает контакты в сокращённом виде.           http://127.0.0.1:8000/api/v1/backend/short_contacts/
    # Работает с магазинами.                            http://127.0.0.1:8000/api/v1/backend/shop/
    # Работает с категориями.                           http://127.0.0.1:8000/api/v1/backend/category/
    # Работает с товарами.                              http://127.0.0.1:8000/api/v1/backend/product/
    # Работает с описанием товара.                      http://127.0.0.1:8000/api/v1/backend/prod_info/
    path('upload/', views.PartnerUpdate.as_view(), name='upload'),
    path('price/', views.PriceView.as_view(), name='price'),
    # Работает с корзиной и общим списком заказов.      http://127.0.0.1:8000/api/v1/backend/orders/
] + router.urls
