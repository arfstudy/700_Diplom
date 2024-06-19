"""
URL configuration for users application.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.urls import path

from apiauth import views

app_name = 'api'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),

    path('verify/', views.EmailVerifyView.as_view(), name='verify'),
    path('token/', views.NewTokenCreateView.as_view(), name='token'),
    path('look_me/', views.UserLookView.as_view(), name='look_me'),

    path('register/', views.UserRegisterView.as_view(), name='register'),
]
