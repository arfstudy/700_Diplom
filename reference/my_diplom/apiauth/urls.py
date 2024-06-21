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
]
