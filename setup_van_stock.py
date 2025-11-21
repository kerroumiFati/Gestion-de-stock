"""
Script pour configurer le van et le stock pour le livreur de test
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import LivreurDistribution
from API.models import Warehouse, ProductStock, Produit
from decimal import Decimal

print("=" * 80)
print("CONFIGURATION DU VAN ET DU STOCK POUR LIV004")
print("=" * 80)

# 1. Récupérer le livreur LIV004
try:
    livreur = LivreurDistribution.objects.get(matricule='LIV004')
    print(f"\n✅ Livreur trouvé : {livreur.nom} ({livreur.matricule})")
except LivreurDistribution.DoesNotExist:
    print("\n❌ Livreur LIV004 introuvable !")
    exit(1)

# 2. Trouver ou créer un van pour ce livreur
van = None

# Essayer d'utiliser un van existant sans livreur
# Récupérer les IDs des vans déjà assignés
vans_assignes_ids = LivreurDistribution.objects.filter(
    entrepot__isnull=False
).values_list('entrepot_id', flat=True)

vans_disponibles = Warehouse.objects.filter(
    code__icontains='VAN',
    is_active=True
).exclude(
    id__in=vans_assignes_ids  # Exclure les vans déjà assignés
)

if vans_disponibles.exists():
    van = vans_disponibles.first()
    print(f"\n✅ Van disponible trouvé : {van.name} ({van.code})")
else:
    # Créer un nouveau van
    print("\n📦 Création d'un nouveau van...")
    van = Warehouse.objects.create(
        name=f"Van de {livreur.nom}",
        code=f"VAN-{livreur.matricule}",
        is_active=True
    )
    print(f"✅ Van créé : {van.name} ({van.code})")

# 3. Assigner le van au livreur
livreur.entrepot = van
livreur.save()
print(f"\n✅ Van assigné au livreur {livreur.nom}")

# 4. Vérifier s'il y a des produits
produits = Produit.objects.all()
if not produits.exists():
    print("\n❌ Aucun produit dans la base !")
    print("   Créez des produits via Django Admin d'abord.")
    exit(1)

print(f"\n📦 {produits.count()} produit(s) disponible(s)")

# 5. Ajouter du stock dans le van
print(f"\n📦 Ajout de stock dans le van...")

# Prendre les 5 premiers produits
produits_a_ajouter = produits[:5]

for produit in produits_a_ajouter:
    # Vérifier si le stock existe déjà
    stock, created = ProductStock.objects.get_or_create(
        warehouse=van,
        produit=produit,
        defaults={'quantity': 0}
    )

    if created or stock.quantity == 0:
        # Ajouter une quantité de base
        stock.quantity = 50
        stock.save()
        print(f"   ✅ {produit.designation}: {stock.quantity} {produit.get_unite_mesure_display()}")
    else:
        print(f"   ℹ️  {produit.designation}: {stock.quantity} {produit.get_unite_mesure_display()} (déjà en stock)")

# 6. Calculer les statistiques
stocks = ProductStock.objects.filter(warehouse=van, quantity__gt=0)
total_produits = stocks.count()
total_quantite = sum(s.quantity for s in stocks)
valeur_totale = sum(float(s.quantity * (s.produit.prixU or 0)) for s in stocks)

# 7. Résumé
print("\n" + "=" * 80)
print("RÉSUMÉ")
print("=" * 80)

print(f"\n✅ Configuration terminée !")
print(f"\n📊 Statistiques du van :")
print(f"   - Van : {van.name} ({van.code})")
print(f"   - Livreur : {livreur.nom}")
print(f"   - Produits en stock : {total_produits}")
print(f"   - Quantité totale : {total_quantite}")
print(f"   - Valeur estimée : {valeur_totale:.2f} DA")

print(f"\n📱 Dans l'app mobile :")
print(f"   - Connectez-vous avec : {livreur.user.username if livreur.user else livreur.matricule}")
print(f"   - Aller dans l'onglet 'Stock'")
print(f"   - Vous verrez {total_produits} produit(s)")

print(f"\n📡 Test de l'endpoint API :")
print(f"   GET /API/distribution/livreurs/{livreur.id}/stock_van/")

print("\n")
