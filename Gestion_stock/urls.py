"""Gestion_stock URL Configuration

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
from django.urls import re_path
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from django.views.generic import TemplateView
from frontoffice.create_admin import create_first_admin
from frontoffice.check_admin import check_existing_admins
from frontoffice.views_company import create_company_view, list_companies_view, delete_company_view
from API.map_view import livreurs_map_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('API/', include('API.urls')),
    path('', include('frontoffice.urls')),

    # Gestion des Companies/Sessions
    path('companies/', list_companies_view, name='list_companies'),
    path('companies/create/', create_company_view, name='create_company'),
    path('companies/delete/<int:company_id>/', delete_company_view, name='delete_company'),

    # Temporary endpoints for admin management
    path('create-first-admin/', create_first_admin, name='create_first_admin'),
    path('check-admins/', check_existing_admins, name='check_admins'),

    # Distribution module explicit routes (ensure availability regardless of frontoffice/urls)
    path('admindash/livreurs/', login_required(TemplateView.as_view(template_name='frontoffice/master_page.html')), name='livreurs_page'),
    path('admindash/tournees/', login_required(TemplateView.as_view(template_name='frontoffice/master_page.html')), name='tournees_page'),
    path('admindash/distribution/', login_required(TemplateView.as_view(template_name='frontoffice/master_page.html')), name='distribution_dashboard_page'),
    path('admindash/livreurs-map/', login_required(livreurs_map_view), name='livreurs_map'),
    path('livreur/app/', TemplateView.as_view(template_name='frontoffice/page/livreur_mobile.html'), name='livreur_app'),

    # Legacy SPA routes
    re_path(r'^admindash/$', login_required(TemplateView.as_view(template_name='frontoffice/master_page.html'))),
    re_path(r'^admindash/statistiques$', TemplateView.as_view(template_name='frontoffice/page/statistiques.html')),
    re_path(r'^admindash/rapports$', TemplateView.as_view(template_name='frontoffice/page/rapports.html')),
    re_path(r'^admindash/produits$', TemplateView.as_view(template_name='frontoffice/page/produit.html')),
    re_path(r'^admindash/clients$', TemplateView.as_view(template_name='frontoffice/page/client.html')),
    re_path(r'^admindash/fournisseurs$', TemplateView.as_view(template_name='frontoffice/page/fournisseur.html')),
    re_path(r'^admindash/achats$', TemplateView.as_view(template_name='frontoffice/page/achat.html')),
    re_path(r'^admindash/factures$', TemplateView.as_view(template_name='frontoffice/page/facture.html')),
    re_path(r'^admindash/inventaires$', TemplateView.as_view(template_name='frontoffice/page/inventaire.html')),
    re_path(r'^admindash/mouvements$', TemplateView.as_view(template_name='frontoffice/page/mouvements.html')),
    re_path(r'^admindash/entrepots$', TemplateView.as_view(template_name='frontoffice/page/entrepots.html')),
    re_path(r'^admindash/ventes$', TemplateView.as_view(template_name='frontoffice/page/vente.html')),
    re_path(r'^admindash/categories$', TemplateView.as_view(template_name='frontoffice/page/categorie.html')),

    # Module de Distribution - routes centralisées dans frontoffice/urls.py

]
