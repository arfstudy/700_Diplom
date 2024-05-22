"""
URL configuration for users application.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.urls import path
from django.views.generic import TemplateView

from webauth import views

app_name = 'web'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path(
        'email_verify/done/',
        TemplateView.as_view(template_name='registration/email_verify_done.html'),
        name='email_verify_done',
    ),
    path(
        'verify/<key64>/<token>/',
        views.UserEmailVerifyView.as_view(),
        name='email_verify_confirm',
    ),
    path('register/', views.UserRegisterView.as_view(), name='register'),
    path(
        'user_editing/',
        TemplateView.as_view(template_name='webauth/editing_personal_data.html'),
        name='user_editing',
    ),
    path('user_update/', views.UserUpdateView.as_view(), name='user_update'),
    path('user_delete/',TemplateView.as_view(template_name='webauth/user_delete.html'),name='user_delete',),
    path('user_delete_confirm/', views.UserDeleteView.as_view(), name='user_delete_confirm',),
    path(
        'delete/complete/',
        TemplateView.as_view(template_name='webauth/user_delete_complete.html'),
        name='user_delete_complete',
    ),

    path('inspect/', views.UserInspectView.as_view(), name='inspect'),
]
