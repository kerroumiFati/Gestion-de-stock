"""frontoffice URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from frontoffice import views
from django.urls import re_path
from frontoffice.views_audit import audit_list

from frontoffice.views import LoginView, LogoutView

urlpatterns = [
    re_path(r'^$', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('admindash/', views.dashboard, name='admindash'),
    path('produits/', views.produit_all, name='produits'),
    path('page/<str:name>/', views.page, name='page'),

    # Users admin
    path('users-admin/', views.users_list, name='users_list'),
    path('users-admin/new/', views.user_create, name='user_create'),
    path('users-admin/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users-admin/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users-admin/<int:user_id>/reset-password/', views.user_reset_password_confirm, name='user_reset_password'),
    path('roles-admin/', views.roles_list, name='roles_list'),
    path('audit-logs/', audit_list, name='audit_list'),
]
