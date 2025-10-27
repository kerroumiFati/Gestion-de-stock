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

urlpatterns = [
    path('admin/', admin.site.urls),
    path('API/', include('API.urls')),
    path('', include('frontoffice.urls')),

    # Temporary endpoints for admin management
    path('create-first-admin/', create_first_admin, name='create_first_admin'),
    path('check-admins/', check_existing_admins, name='check_admins'),

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

]
