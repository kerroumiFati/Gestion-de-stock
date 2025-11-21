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
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from frontoffice import views
from django.urls import re_path
from frontoffice.views_audit import audit_list
from frontoffice import views_reports
from frontoffice.test_i18n import test_translation

from frontoffice.views import LoginView, LogoutView, change_password

urlpatterns = [
    re_path(r'^$', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('admindash/', login_required(views.dashboard), name='admindash'),
    # Distribution module direct pages via dedicated views
    path('admindash/livreurs/', login_required(views.livreurs_page), name='livreurs_page'),
    path('admindash/tournees/', login_required(views.tournees_page), name='tournees_page'),
    path('admindash/distribution/', login_required(views.distribution_page), name='distribution_dashboard_page'),
    path('admindash/config-clients-chauffeurs/', login_required(views.config_clients_chauffeurs_page), name='config_clients_chauffeurs_page'),
    path('admindash/commandes-mobile/', login_required(views.commandes_clients_mobile), name='commandes_clients_mobile'),
    path('livreur/app/', login_required(views.livreur_app_page), name='livreur_app'),
    path('produits/', views.produit_all, name='produits'),
    path('caisse/', views.caisse, name='caisse'),
    path('test-translation/', test_translation, name='test-translation'),
    path('page/<str:name>/', views.page, name='page'),

    # Exports de rapports (nouvelles routes simplifiées)
    path('reports/stock-valuation/', views_reports.export_stock_valuation, name='export-stock-valuation'),
    path('reports/sales/', views_reports.export_sales_report, name='export-sales-report'),
    path('reports/inventory/', views_reports.export_inventory_report, name='export-inventory-report'),

    # Users admin (nouvelle interface moderne)
    path('admin-users/', views.admin_users, name='admin_users'),

    # Users admin (anciennes routes - à garder pour compatibilité)
    path('users-admin/', views.users_list, name='users_list'),
    path('users-admin/new/', views.user_create, name='user_create'),
    path('users-admin/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users-admin/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users-admin/<int:user_id>/reset-password/', views.user_reset_password_confirm, name='user_reset_password'),
    path('roles-admin/', views.roles_list, name='roles_list'),
    path('roles-admin/new/', views.role_create, name='role_create'),
    path('roles-admin/<int:role_id>/edit/', views.role_edit, name='role_edit'),
    path('roles-admin/<int:role_id>/delete/', views.role_delete, name='role_delete'),
    path('roles-admin/<int:role_id>/permissions/', views.role_edit_permissions, name='role_edit_permissions'),
    path('audit-logs/', audit_list, name='audit_list'),
    path('change-password/', change_password, name='change_password'),

    # Gestion de stock - Interfaces personnalisées
    path('stock/entrepots/', login_required(views.entrepots_list), name='entrepots_list'),
    path('stock/stocks/', login_required(views.stocks_list), name='stocks_list'),
    path('stock/transferts/', login_required(views.transferts_list), name='transferts_list'),
    path('stock/charger-van/', login_required(views.charger_van), name='charger_van'),
    path('stock/dashboard-vans/', login_required(views.stock_dashboard), name='stock_dashboard'),
]
