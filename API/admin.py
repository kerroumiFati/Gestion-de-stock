from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from .models import (
    Company, UserProfile, SystemConfig,
    Client, Fournisseur, Produit, Achat,
    Vente, LigneVente, Warehouse, ProductStock,
    TransfertStock, LigneTransfertStock, StockMove, Currency
)
from .distribution_models import (
    LivreurDistribution, TourneeMobile, ArretTourneeMobile,
    VenteTourneeMobile, LigneVenteTourneeMobile, RapportCaisseMobile,
    DepenseTourneeMobile, SyncLogMobile
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

from .models import Categorie

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'telephone', 'adresse', 'lat', 'lng']
    list_filter = ['company']
    search_fields = ['nom', 'prenom', 'telephone', 'adresse']
    fields = ['company', 'nom', 'prenom', 'email', 'telephone', 'adresse', 'lat', 'lng']

admin.site.register(Achat)

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['nom', 'parent', 'is_active']
    list_filter = ['is_active', 'parent']
    search_fields = ['nom', 'description']

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'email', 'telephone']
    search_fields = ['libelle', 'email', 'adresse']

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['reference', 'designation', 'quantite', 'prixU', 'categorie']
    list_filter = ['categorie', 'fournisseur']
    search_fields = ['reference', 'designation', 'code_barre']
    autocomplete_fields = ['categorie', 'fournisseur']

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

# ===========================
# Distribution Mobile Models
# ===========================

@admin.register(LivreurDistribution)
class LivreurDistributionAdmin(admin.ModelAdmin):
    list_display = ['matricule', 'nom', 'telephone', 'statut', 'vehicule_immatriculation', 'entrepot']
    list_filter = ['statut', 'date_embauche', 'entrepot']
    search_fields = ['matricule', 'nom', 'telephone', 'email', 'vehicule_immatriculation']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('user', 'matricule', 'nom', 'telephone', 'email')
        }),
        ('Véhicule', {
            'fields': ('vehicule_immatriculation', 'vehicule_marque')
        }),
        ('Statut et affectation', {
            'fields': ('statut', 'date_embauche', 'entrepot')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class ArretTourneeMobileInline(admin.TabularInline):
    model = ArretTourneeMobile
    extra = 0
    fields = ['ordre_passage', 'client', 'statut', 'heure_prevue']
    readonly_fields = ['ordre_passage']

@admin.register(TourneeMobile)
class TourneeMobileAdmin(admin.ModelAdmin):
    list_display = ['numero_tournee', 'livreur', 'date_tournee', 'statut', 'est_cloturee', 'distance_km']
    list_filter = ['statut', 'est_cloturee', 'date_tournee', 'livreur']
    search_fields = ['numero_tournee', 'livreur__nom', 'livreur__matricule']
    readonly_fields = ['created_at', 'updated_at', 'date_cloture', 'cloturee_par']
    date_hierarchy = 'date_tournee'
    inlines = [ArretTourneeMobileInline]
    fieldsets = (
        ('Informations principales', {
            'fields': ('livreur', 'date_tournee', 'numero_tournee', 'statut')
        }),
        ('Horaires', {
            'fields': ('heure_debut', 'heure_fin', 'distance_km')
        }),
        ('Géolocalisation', {
            'fields': ('position_depart_lat', 'position_depart_lng', 'position_fin_lat', 'position_fin_lng'),
            'classes': ('collapse',)
        }),
        ('Clôture', {
            'fields': ('est_cloturee', 'date_cloture', 'cloturee_par', 'notes')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ArretTourneeMobile)
class ArretTourneeMobileAdmin(admin.ModelAdmin):
    list_display = ['tournee', 'ordre_passage', 'client', 'statut', 'heure_prevue', 'heure_arrivee']
    list_filter = ['statut', 'tournee__date_tournee', 'tournee__livreur']
    search_fields = ['client__nom', 'tournee__numero_tournee', 'motif_echec']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Arrêt', {
            'fields': ('tournee', 'client', 'ordre_passage', 'statut')
        }),
        ('Horaires', {
            'fields': ('heure_prevue', 'heure_arrivee', 'heure_depart')
        }),
        ('Livraison', {
            'fields': ('nom_receptionnaire', 'signature_base64', 'photo_livraison'),
            'classes': ('collapse',)
        }),
        ('Échec', {
            'fields': ('motif_echec', 'notes_echec'),
            'classes': ('collapse',)
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

class LigneVenteTourneeMobileInline(admin.TabularInline):
    model = LigneVenteTourneeMobile
    extra = 1
    fields = ['produit', 'quantite', 'prix_unitaire', 'taux_tva', 'montant_ttc']
    readonly_fields = ['montant_ttc']

@admin.register(VenteTourneeMobile)
class VenteTourneeMobileAdmin(admin.ModelAdmin):
    list_display = ['numero_vente', 'tournee', 'client', 'date_vente', 'montant_total', 'type_paiement', 'est_synchronise']
    list_filter = ['type_paiement', 'est_synchronise', 'date_vente', 'tournee__livreur']
    search_fields = ['numero_vente', 'client__nom', 'tournee__numero_tournee']
    readonly_fields = ['created_at', 'updated_at', 'date_synchronisation']
    date_hierarchy = 'date_vente'
    inlines = [LigneVenteTourneeMobileInline]
    fieldsets = (
        ('Vente', {
            'fields': ('tournee', 'arret', 'client', 'numero_vente', 'date_vente')
        }),
        ('Montants', {
            'fields': ('montant_ht', 'montant_tva', 'montant_total')
        }),
        ('Paiement', {
            'fields': ('type_paiement', 'montant_paye', 'montant_rendu')
        }),
        ('Synchronisation', {
            'fields': ('est_synchronise', 'date_synchronisation'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )

@admin.register(RapportCaisseMobile)
class RapportCaisseMobileAdmin(admin.ModelAdmin):
    list_display = ['tournee', 'statut', 'total_encaissements', 'total_depenses', 'ecart', 'a_des_anomalies']
    list_filter = ['statut', 'a_des_anomalies', 'tournee__date_tournee']
    search_fields = ['tournee__numero_tournee', 'tournee__livreur__nom']
    readonly_fields = ['total_encaissements', 'total_depenses', 'solde_final_theorique', 'ecart', 'created_at', 'updated_at']
    fieldsets = (
        ('Tournée', {
            'fields': ('tournee', 'fonds_depart')
        }),
        ('Encaissements', {
            'fields': ('total_especes', 'total_cartes', 'total_cheques', 'total_credits', 'total_encaissements')
        }),
        ('Dépenses', {
            'fields': ('carburant', 'reparations', 'autres_depenses', 'total_depenses')
        }),
        ('Solde', {
            'fields': ('solde_final_theorique', 'solde_final_reel', 'ecart', 'justification_ecart')
        }),
        ('Validation', {
            'fields': ('statut', 'valide_par', 'date_validation')
        }),
        ('Anomalies', {
            'fields': ('a_des_anomalies', 'notes_anomalies')
        }),
    )

@admin.register(DepenseTourneeMobile)
class DepenseTourneeMobileAdmin(admin.ModelAdmin):
    list_display = ['rapport_caisse', 'type_depense', 'montant', 'description', 'date_depense']
    list_filter = ['type_depense', 'date_depense']
    search_fields = ['description', 'rapport_caisse__tournee__numero_tournee']
    readonly_fields = ['created_at']

@admin.register(SyncLogMobile)
class SyncLogMobileAdmin(admin.ModelAdmin):
    list_display = ['livreur', 'type_sync', 'statut', 'nb_tournees', 'nb_ventes', 'nb_arrets', 'date_sync']
    list_filter = ['type_sync', 'statut', 'date_sync', 'livreur']
    search_fields = ['livreur__nom', 'message', 'device_id']
    readonly_fields = ['date_sync']
    date_hierarchy = 'date_sync'
    fieldsets = (
        ('Synchronisation', {
            'fields': ('livreur', 'type_sync', 'statut', 'date_sync', 'duree_secondes')
        }),
        ('Données synchronisées', {
            'fields': ('nb_tournees', 'nb_ventes', 'nb_arrets')
        }),
        ('Détails', {
            'fields': ('message', 'erreur_details')
        }),
        ('Device', {
            'fields': ('device_id', 'app_version'),
            'classes': ('collapse',)
        }),
    )


# ===========================
# Stock Management
# ===========================

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'get_total_products', 'get_stock_value']
    list_filter = ['is_active', 'company']
    search_fields = ['code', 'name']
    actions = ['view_stock_details']

    def get_total_products(self, obj):
        return obj.stocks.count()
    get_total_products.short_description = 'Nombre de produits'

    def get_stock_value(self, obj):
        total = sum(
            stock.quantity * stock.produit.prixU
            for stock in obj.stocks.select_related('produit')
        )
        return f"{total:.2f}"
    get_stock_value.short_description = 'Valeur du stock'

    def view_stock_details(self, request, queryset):
        """Afficher les détails du stock pour les entrepôts sélectionnés"""
        warehouse_ids = queryset.values_list('id', flat=True)
        url = reverse('admin:stock_dashboard') + f"?warehouses={','.join(map(str, warehouse_ids))}"
        return redirect(url)
    view_stock_details.short_description = 'Voir détails du stock'


@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ['produit', 'warehouse', 'quantity', 'get_status']
    list_filter = ['warehouse', 'produit__categorie']
    search_fields = ['produit__reference', 'produit__designation', 'warehouse__code']
    readonly_fields = ['produit', 'warehouse']

    def get_status(self, obj):
        if obj.quantity <= 0:
            color = 'red'
            status = 'Rupture'
        elif obj.quantity <= obj.produit.seuil_critique:
            color = 'orange'
            status = 'Critique'
        elif obj.quantity <= obj.produit.seuil_alerte:
            color = 'yellow'
            status = 'Alerte'
        else:
            color = 'green'
            status = 'OK'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    get_status.short_description = 'Statut'


# ===========================
# Stock Transfers
# ===========================

class LigneTransfertStockInline(admin.TabularInline):
    model = LigneTransfertStock
    extra = 1
    fields = ['produit', 'quantite', 'get_stock_disponible_display', 'notes']
    readonly_fields = ['get_stock_disponible_display']
    autocomplete_fields = ['produit']

    def get_stock_disponible_display(self, obj):
        if obj.id:
            stock_dispo = obj.get_stock_disponible()
            color = 'green' if stock_dispo >= obj.quantite else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} unités disponibles</span>',
                color, stock_dispo
            )
        return '-'
    get_stock_disponible_display.short_description = 'Stock disponible'


@admin.register(TransfertStock)
class TransfertStockAdmin(admin.ModelAdmin):
    list_display = [
        'numero', 'date_creation', 'entrepot_source', 'entrepot_destination',
        'get_statut_colored', 'get_nombre_lignes', 'get_nombre_produits', 'demandeur'
    ]
    list_filter = ['statut', 'date_creation', 'entrepot_source', 'entrepot_destination']
    search_fields = ['numero', 'notes', 'entrepot_source__code', 'entrepot_destination__code']
    readonly_fields = [
        'numero', 'date_creation', 'date_validation', 'date_reception',
        'valideur', 'recepteur', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'date_creation'
    inlines = [LigneTransfertStockInline]
    actions = ['valider_transferts', 'annuler_transferts', 'exporter_transferts']

    fieldsets = (
        ('Informations générales', {
            'fields': ('numero', 'date_creation', 'statut')
        }),
        ('Transfert', {
            'fields': ('entrepot_source', 'entrepot_destination')
        }),
        ('Traçabilité', {
            'fields': (
                'demandeur', 'valideur', 'date_validation',
                'recepteur', 'date_reception'
            )
        }),
        ('Notes', {
            'fields': ('notes', 'motif_annulation')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_statut_colored(self, obj):
        colors = {
            'brouillon': 'gray',
            'valide': 'green',
            'en_transit': 'blue',
            'receptionne': 'darkgreen',
            'annule': 'red',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colors.get(obj.statut, 'gray'),
            obj.get_statut_display()
        )
    get_statut_colored.short_description = 'Statut'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.demandeur = request.user
        super().save_model(request, obj, form, change)

    def valider_transferts(self, request, queryset):
        """Valider les transferts sélectionnés"""
        validated = 0
        errors = []

        for transfert in queryset:
            try:
                transfert.valider(request.user)
                validated += 1
            except Exception as e:
                errors.append(f"{transfert.numero}: {str(e)}")

        if validated:
            self.message_user(
                request,
                f"{validated} transfert(s) validé(s) avec succès.",
                messages.SUCCESS
            )

        if errors:
            self.message_user(
                request,
                "Erreurs: " + "; ".join(errors),
                messages.ERROR
            )
    valider_transferts.short_description = 'Valider les transferts sélectionnés'

    def annuler_transferts(self, request, queryset):
        """Annuler les transferts sélectionnés"""
        cancelled = 0

        for transfert in queryset:
            try:
                transfert.annuler(request.user, "Annulé via l'admin")
                cancelled += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour {transfert.numero}: {str(e)}",
                    messages.ERROR
                )

        if cancelled:
            self.message_user(
                request,
                f"{cancelled} transfert(s) annulé(s) avec succès.",
                messages.SUCCESS
            )
    annuler_transferts.short_description = 'Annuler les transferts sélectionnés'

    def exporter_transferts(self, request, queryset):
        """Exporter les transferts en CSV"""
        import csv
        from django.utils import timezone

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="transferts_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Numéro', 'Date création', 'Source', 'Destination',
            'Statut', 'Nb lignes', 'Nb produits', 'Demandeur'
        ])

        for transfert in queryset:
            writer.writerow([
                transfert.numero,
                transfert.date_creation.strftime('%Y-%m-%d %H:%M'),
                transfert.entrepot_source.code,
                transfert.entrepot_destination.code,
                transfert.get_statut_display(),
                transfert.get_nombre_lignes(),
                transfert.get_nombre_produits(),
                transfert.demandeur.username if transfert.demandeur else '-'
            ])

        return response
    exporter_transferts.short_description = 'Exporter en CSV'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('charger-van/', self.admin_site.admin_view(self.charger_van_view), name='charger_van'),
            path('stock-dashboard/', self.admin_site.admin_view(self.stock_dashboard_view), name='stock_dashboard'),
        ]
        return custom_urls + urls

    def charger_van_view(self, request):
        """Vue personnalisée pour charger un van rapidement"""
        from django import forms

        class ChargerVanForm(forms.Form):
            van = forms.ModelChoiceField(
                queryset=Warehouse.objects.filter(
                    code__istartswith='van',
                    is_active=True
                ),
                label='Sélectionner le van',
                required=True
            )
            entrepot_source = forms.ModelChoiceField(
                queryset=Warehouse.objects.exclude(
                    code__istartswith='van'
                ).filter(is_active=True),
                label='Entrepôt source',
                required=True
            )
            produits = forms.CharField(
                widget=forms.Textarea(attrs={'rows': 10}),
                label='Produits à charger',
                help_text='Format: REFERENCE,QUANTITE (une ligne par produit)\nExemple:\nPROD-001,50\nPROD-002,30',
                required=True
            )

        if request.method == 'POST':
            form = ChargerVanForm(request.POST)
            if form.is_valid():
                van = form.cleaned_data['van']
                source = form.cleaned_data['entrepot_source']
                produits_text = form.cleaned_data['produits']

                # Créer le transfert
                transfert = TransfertStock.objects.create(
                    company=request.user.userprofile.company if hasattr(request.user, 'userprofile') else None,
                    entrepot_source=source,
                    entrepot_destination=van,
                    demandeur=request.user,
                    notes=f'Chargement van créé via interface rapide'
                )

                # Parser les produits
                errors = []
                for line in produits_text.strip().split('\n'):
                    if not line.strip():
                        continue

                    try:
                        ref, qty = line.split(',')
                        produit = Produit.objects.get(reference=ref.strip())
                        LigneTransfertStock.objects.create(
                            transfert=transfert,
                            produit=produit,
                            quantite=int(qty.strip())
                        )
                    except Exception as e:
                        errors.append(f"Ligne '{line}': {str(e)}")

                if not errors:
                    # Valider automatiquement
                    try:
                        transfert.valider(request.user)
                        messages.success(request, f'Transfert {transfert.numero} créé et validé avec succès!')
                        return redirect('admin:API_transfertstock_change', transfert.id)
                    except Exception as e:
                        messages.error(request, f'Transfert créé mais erreur de validation: {str(e)}')
                        return redirect('admin:API_transfertstock_change', transfert.id)
                else:
                    messages.warning(request, 'Transfert créé avec des erreurs: ' + '; '.join(errors))
                    return redirect('admin:API_transfertstock_change', transfert.id)
        else:
            form = ChargerVanForm()

        context = {
            'form': form,
            'title': 'Charger un van rapidement',
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
        }
        return render(request, 'admin/charger_van.html', context)

    def stock_dashboard_view(self, request):
        """Tableau de bord des stocks par van"""
        # Récupérer tous les vans (entrepôts commençant par VAN)
        vans = Warehouse.objects.filter(
            code__istartswith='van',
            is_active=True
        ).prefetch_related('stocks__produit')

        # Statistiques par van
        van_stats = []
        for van in vans:
            stocks = van.stocks.select_related('produit').all()
            total_produits = stocks.count()
            total_quantite = sum(s.quantity for s in stocks)
            valeur_stock = sum(s.quantity * s.produit.prixU for s in stocks)

            # Trouver le livreur associé
            livreur = LivreurDistribution.objects.filter(entrepot=van).first()

            van_stats.append({
                'van': van,
                'livreur': livreur,
                'total_produits': total_produits,
                'total_quantite': total_quantite,
                'valeur_stock': valeur_stock,
                'stocks': stocks[:10]  # Top 10 produits
            })

        # Récupérer la devise par défaut
        currency = Currency.objects.filter(is_default=True, is_active=True).first()
        if not currency:
            currency = Currency.objects.filter(is_active=True).first()

        context = {
            'van_stats': van_stats,
            'title': 'Tableau de bord des stocks par van',
            'site_header': self.admin_site.site_header,
            'site_title': self.admin_site.site_title,
            'currency': currency
        }
        return render(request, 'admin/stock_dashboard.html', context)
