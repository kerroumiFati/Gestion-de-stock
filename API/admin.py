from django.contrib import admin
from django.contrib.auth.models import User
from .models import (
    Company, UserProfile, SystemConfig,
    Client, Fournisseur, Produit, Achat,
    Vente, LigneVente
)

# ===========================
# Multi-Tenancy Models
# ===========================

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'email', 'telephone', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'email', 'tax_id']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Informations principales', {
            'fields': ('name', 'code', 'is_active')
        }),
        ('Contact', {
            'fields': ('email', 'telephone', 'adresse')
        }),
        ('Informations fiscales', {
            'fields': ('tax_id',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_username', 'company', 'role', 'created_at']
    list_filter = ['role', 'company', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name', 'company__name']
    readonly_fields = ['created_at']

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Nom d\'utilisateur'

# ===========================
# System Configuration
# ===========================

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['default_warehouse']
    fields = ['default_warehouse']
    help_texts = {
        'default_warehouse': 'Entrepôt par défaut utilisé pour les ventes si aucun n\'est spécifié'
    }

# ===========================
# Business Models
# ===========================

admin.site.register(Client)
admin.site.register(Fournisseur)
admin.site.register(Produit)
admin.site.register(Achat)

# ===========================
# Sales with Inline
# ===========================

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
