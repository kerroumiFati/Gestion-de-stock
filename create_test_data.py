#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour créer des données de test
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.models import Warehouse, Produit, ProductStock, TransfertStock, LigneTransfertStock, Client, Categorie, Fournisseur
from API.distribution_models import LivreurDistribution
from django.contrib.auth.models import User
from decimal import Decimal
import random

print('═══════════════════════════════════════════════════════')
print('        CRÉATION DE DONNÉES DE TEST')
print('═══════════════════════════════════════════════════════\n')

# Récupérer ou créer un utilisateur admin
admin_user, _ = User.objects.get_or_create(
    username='admin',
    defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin@test.com'}
)
admin_user.set_password('admin')
admin_user.save()

# 0. Créer un fournisseur par défaut
print('0. CRÉATION DU FOURNISSEUR PAR DÉFAUT')
print('   ' + '─' * 45)
fournisseur, created = Fournisseur.objects.get_or_create(
    libelle='Fournisseur Général',
    defaults={'telephone': '0770123456', 'email': 'contact@fournisseur.dz'}
)
if created:
    print(f'   ✓ Créé: {fournisseur.libelle}')
else:
    print(f'   → Existe déjà: {fournisseur.libelle}')
print()

# 1. Créer des entrepôts
print('1. CRÉATION DES ENTREPÔTS')
print('   ' + '─' * 45)

entrepots_data = [
    {'code': 'ENT-PRINCIPAL', 'name': 'Entrepôt Principal', 'is_active': True},
    {'code': 'ENT-SECONDAIRE', 'name': 'Entrepôt Secondaire', 'is_active': True},
    {'code': 'ENT-RESERVE', 'name': 'Entrepôt Réserve', 'is_active': True},
]

for data in entrepots_data:
    entrepot, created = Warehouse.objects.get_or_create(
        code=data['code'],
        defaults=data
    )
    if created:
        print(f'   ✓ Créé: {entrepot.code} - {entrepot.name}')
    else:
        print(f'   → Existe déjà: {entrepot.code}')

print()

# 2. Créer des vans
print('2. CRÉATION DES VANS')
print('   ' + '─' * 45)

vans_data = [
    {'code': 'VAN-LIVRAISON-A', 'name': 'Van Livraison Zone A', 'is_active': True},
    {'code': 'VAN-LIVRAISON-B', 'name': 'Van Livraison Zone B', 'is_active': True},
    {'code': 'VAN-EXPRESS', 'name': 'Van Livraison Express', 'is_active': True},
]

for data in vans_data:
    van, created = Warehouse.objects.get_or_create(
        code=data['code'],
        defaults=data
    )
    if created:
        print(f'   ✓ Créé: {van.code} - {van.name}')
    else:
        print(f'   → Existe déjà: {van.code}')

print()

# 3. Créer des catégories de produits
print('3. CRÉATION DES CATÉGORIES')
print('   ' + '─' * 45)

categories_data = [
    {'nom': 'Boissons', 'description': 'Boissons gazeuses et jus'},
    {'nom': 'Snacks', 'description': 'Chips, biscuits et snacks'},
    {'nom': 'Confiserie', 'description': 'Bonbons et chocolats'},
    {'nom': 'Produits Laitiers', 'description': 'Yaourts et fromages'},
]

for data in categories_data:
    cat, created = Categorie.objects.get_or_create(
        nom=data['nom'],
        defaults=data
    )
    if created:
        print(f'   ✓ Créé: {cat.nom}')
    else:
        print(f'   → Existe déjà: {cat.nom}')

print()

# 4. Créer des produits
print('4. CRÉATION DES PRODUITS')
print('   ' + '─' * 45)

cat_boissons = Categorie.objects.filter(nom='Boissons').first()
cat_snacks = Categorie.objects.filter(nom='Snacks').first()
cat_confiserie = Categorie.objects.filter(nom='Confiserie').first()

produits_data = [
    {'reference': 'COCA-500', 'code_barre': '5449000000996', 'designation': 'Coca-Cola 500ml', 'prixU': Decimal('80.00'), 'quantite': 0, 'categorie': cat_boissons, 'fournisseur': fournisseur, 'seuil_alerte': 50, 'seuil_critique': 20},
    {'reference': 'SPRITE-500', 'code_barre': '5449000054227', 'designation': 'Sprite 500ml', 'prixU': Decimal('75.00'), 'quantite': 0, 'categorie': cat_boissons, 'fournisseur': fournisseur, 'seuil_alerte': 50, 'seuil_critique': 20},
    {'reference': 'EAU-150', 'code_barre': '6111010111013', 'designation': 'Eau Minérale 1.5L', 'prixU': Decimal('40.00'), 'quantite': 0, 'categorie': cat_boissons, 'fournisseur': fournisseur, 'seuil_alerte': 100, 'seuil_critique': 30},
    {'reference': 'CHIPS-LAY', 'code_barre': '8886008101084', 'designation': 'Chips Lays Nature', 'prixU': Decimal('90.00'), 'quantite': 0, 'categorie': cat_snacks, 'fournisseur': fournisseur, 'seuil_alerte': 30, 'seuil_critique': 10},
    {'reference': 'CHIPS-PRNG', 'code_barre': '5053990101856', 'designation': 'Pringles Original', 'prixU': Decimal('150.00'), 'quantite': 0, 'categorie': cat_snacks, 'fournisseur': fournisseur, 'seuil_alerte': 25, 'seuil_critique': 10},
    {'reference': 'BISCUIT-OREO', 'code_barre': '7622210883155', 'designation': 'Oreo Original', 'prixU': Decimal('120.00'), 'quantite': 0, 'categorie': cat_snacks, 'fournisseur': fournisseur, 'seuil_alerte': 40, 'seuil_critique': 15},
    {'reference': 'CHOCO-KIT', 'code_barre': '7613033093388', 'designation': 'Kit Kat', 'prixU': Decimal('65.00'), 'quantite': 0, 'categorie': cat_confiserie, 'fournisseur': fournisseur, 'seuil_alerte': 60, 'seuil_critique': 20},
    {'reference': 'CHOCO-SNCK', 'code_barre': '5000159461122', 'designation': 'Snickers', 'prixU': Decimal('70.00'), 'quantite': 0, 'categorie': cat_confiserie, 'fournisseur': fournisseur, 'seuil_alerte': 60, 'seuil_critique': 20},
    {'reference': 'JUS-ORANGE', 'code_barre': '6111010222234', 'designation': 'Jus d Orange 1L', 'prixU': Decimal('110.00'), 'quantite': 0, 'categorie': cat_boissons, 'fournisseur': fournisseur, 'seuil_alerte': 40, 'seuil_critique': 15},
    {'reference': 'CAKE-TIGER', 'code_barre': '6111010333345', 'designation': 'Tiger Cake', 'prixU': Decimal('85.00'), 'quantite': 0, 'categorie': cat_snacks, 'fournisseur': fournisseur, 'seuil_alerte': 50, 'seuil_critique': 15},
]

for data in produits_data:
    prod, created = Produit.objects.get_or_create(
        reference=data['reference'],
        defaults=data
    )
    if created:
        print(f'   ✓ Créé: {prod.reference} - {prod.designation} ({prod.prixU} DA)')
    else:
        print(f'   → Existe déjà: {prod.reference}')

print()

# 5. Créer des stocks dans les entrepôts
print('5. CRÉATION DES STOCKS DANS LES ENTREPÔTS')
print('   ' + '─' * 45)

entrepot_principal = Warehouse.objects.get(code='ENT-PRINCIPAL')
entrepot_secondaire = Warehouse.objects.get(code='ENT-SECONDAIRE')

produits = Produit.objects.all()

# Stock dans l'entrepôt principal (quantités importantes)
for produit in produits:
    stock, created = ProductStock.objects.get_or_create(
        warehouse=entrepot_principal,
        produit=produit,
        defaults={'quantity': random.randint(100, 500)}
    )
    if created:
        print(f'   ✓ Stock créé: {produit.reference} dans {entrepot_principal.code} - {stock.quantity} unités')
    else:
        print(f'   → Stock existe: {produit.reference} dans {entrepot_principal.code}')

# Stock dans l'entrepôt secondaire (quantités moyennes)
for produit in list(produits)[:5]:  # Seulement 5 produits
    stock, created = ProductStock.objects.get_or_create(
        warehouse=entrepot_secondaire,
        produit=produit,
        defaults={'quantity': random.randint(20, 100)}
    )
    if created:
        print(f'   ✓ Stock créé: {produit.reference} dans {entrepot_secondaire.code} - {stock.quantity} unités')

print()

# 6. Créer des clients
print('6. CRÉATION DES CLIENTS')
print('   ' + '─' * 45)

clients_data = [
    {'nom': 'SARL CommerceExpress', 'prenom': '', 'telephone': '0770111222', 'email': 'contact@commerceexpress.dz', 'adresse': '12 Rue du Commerce, Alger'},
    {'nom': 'Supérette Belkacem', 'prenom': 'Ahmed', 'telephone': '0771222333', 'email': 'belkacem@email.dz', 'adresse': '45 Avenue de la Liberté, Oran'},
    {'nom': 'Épicerie Moderne', 'prenom': 'Fatima', 'telephone': '0772333444', 'email': 'epicerie.moderne@email.dz', 'adresse': '78 Boulevard Zirout Youcef, Constantine'},
    {'nom': 'Kiosque Central', 'prenom': 'Karim', 'telephone': '0773444555', 'email': 'kiosque.central@email.dz', 'adresse': '23 Place du 1er Novembre, Annaba'},
    {'nom': 'Mini-Market Riad', 'prenom': 'Nadia', 'telephone': '0774555666', 'email': 'minimarket.riad@email.dz', 'adresse': '56 Rue des Frères Bouadou, Tizi Ouzou'},
]

for data in clients_data:
    client, created = Client.objects.get_or_create(
        telephone=data['telephone'],
        defaults=data
    )
    if created:
        print(f'   ✓ Créé: {client.nom} {client.prenom}')
    else:
        print(f'   → Existe déjà: {client.nom}')

print()

# 7. Créer des livreurs
print('7. CRÉATION DES LIVREURS')
print('   ' + '─' * 45)

van_a = Warehouse.objects.get(code='VAN-LIVRAISON-A')
van_b = Warehouse.objects.get(code='VAN-LIVRAISON-B')

livreurs_data = [
    {'nom': 'Mohamed Benali', 'matricule': 'LIV-001', 'telephone': '0660111222', 'email': 'mohamed.benali@delivery.dz', 'entrepot': van_a},
    {'nom': 'Yacine Khelifi', 'matricule': 'LIV-002', 'telephone': '0661222333', 'email': 'yacine.khelifi@delivery.dz', 'entrepot': van_b},
]

for data in livreurs_data:
    livreur, created = LivreurDistribution.objects.get_or_create(
        matricule=data['matricule'],
        defaults=data
    )
    if created:
        van_code = livreur.entrepot.code if livreur.entrepot else "Aucun"
        print(f'   ✓ Créé: {livreur.nom} - {livreur.matricule} (Van: {van_code})')
    else:
        print(f'   → Existe déjà: {livreur.nom}')

print()

# 8. Créer un transfert de test
print('8. CRÉATION D\'UN TRANSFERT DE TEST')
print('   ' + '─' * 45)

transfert, created = TransfertStock.objects.get_or_create(
    numero='TRF-TEST-001',
    defaults={
        'entrepot_source': entrepot_principal,
        'entrepot_destination': van_a,
        'demandeur': admin_user,
        'statut': 'brouillon',
        'notes': 'Transfert de test pour charger le van'
    }
)

if created:
    print(f'   ✓ Transfert créé: {transfert.numero}')
    # Ajouter quelques lignes
    for produit in list(produits)[:3]:
        ligne = LigneTransfertStock.objects.create(
            transfert=transfert,
            produit=produit,
            quantite=random.randint(10, 30)
        )
        print(f'      - {produit.reference}: {ligne.quantite} unités')
else:
    print(f'   → Transfert existe déjà: {transfert.numero}')

print()

print('═══════════════════════════════════════════════════════')
print('              RÉSUMÉ FINAL')
print('═══════════════════════════════════════════════════════\n')

print(f'✓ Entrepôts: {Warehouse.objects.exclude(code__istartswith="VAN").count()}')
print(f'✓ Vans: {Warehouse.objects.filter(code__istartswith="VAN").count()}')
print(f'✓ Produits: {Produit.objects.count()}')
print(f'✓ Catégories: {Categorie.objects.count()}')
print(f'✓ Stocks: {ProductStock.objects.count()}')
print(f'✓ Clients: {Client.objects.count()}')
print(f'✓ Livreurs: {LivreurDistribution.objects.count()}')
print(f'✓ Transferts: {TransfertStock.objects.count()}')

# Calculer la valeur totale du stock
total_value = sum(
    stock.quantity * stock.produit.prixU
    for stock in ProductStock.objects.select_related('produit')
)
print(f'\n💰 Valeur totale du stock: {total_value:,.2f} DA')

print('\n✅ Données de test créées avec succès!')
print('\nVous pouvez maintenant:')
print('  1. Consulter les entrepôts et vans')
print('  2. Voir les stocks par entrepôt')
print('  3. Créer des transferts')
print('  4. Charger des vans')
print('  5. Consulter le tableau de bord')
