from django.contrib import admin
from .models import *

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['default_warehouse']
    fields = ['default_warehouse']
    help_texts = { 'default_warehouse': 'Entrepôt par défaut utilisé pour les ventes si aucun n\'est spécifié' }
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Client)
admin.site.register(Fournisseur)
admin.site.register(Produit)
admin.site.register(Achat)

# Configuration pour les Ventes
class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 1
    fields = ['produit', 'designation', 'quantite', 'prixU_snapshot']

@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ['numero', 'date_vente', 'client', 'statut', 'type_paiement', 'total_ttc']
    list_filter = ['statut', 'type_paiement', 'date_vente']
    search_fields = ['numero', 'client__nom', 'client__prenom']
    readonly_fields = ['total_ht', 'total_ttc']
    inlines = [LigneVenteInline]
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        obj.recompute_totals()
        obj.save()

admin.site.register(LigneVente)