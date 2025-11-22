#!/usr/bin/env python
"""
Script pour créer des produits et effectuer des achats dans le système de gestion de stock.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from API.models import (
    Company, Fournisseur, Categorie, Produit, Achat,
    Currency, Warehouse, ProductStock, StockMove
)


def get_or_create_company():
    """Récupère ou crée une entreprise par défaut"""
    company, created = Company.objects.get_or_create(
        code='MAIN',
        defaults={
            'name': 'Entreprise Principale',
            'adresse': '123 Rue du Commerce, Alger',
            'telephone': '+213 555 123 456',
            'email': 'contact@entreprise.dz'
        }
    )
    if created:
        print(f"[+] Entreprise créée: {company.name}")
    else:
        print(f"[=] Entreprise existante: {company.name}")
    return company


def get_or_create_currency():
    """Récupère ou crée la devise par défaut (Dinar Algérien)"""
    currency, created = Currency.objects.get_or_create(
        code='DZD',
        defaults={
            'name': 'Dinar Algérien',
            'symbol': 'DA',
            'is_default': True,
            'is_active': True
        }
    )
    if created:
        print(f"[+] Devise créée: {currency.name}")
    else:
        print(f"[=] Devise existante: {currency.name}")
    return currency


def get_or_create_warehouse(company):
    """Récupère ou crée un entrepôt principal"""
    warehouse, created = Warehouse.objects.get_or_create(
        company=company,
        code='ENT-PRINCIPAL',
        defaults={
            'name': 'Entrepôt Principal',
            'is_active': True
        }
    )
    if created:
        print(f"[+] Entrepôt créé: {warehouse.name}")
    else:
        print(f"[=] Entrepôt existant: {warehouse.name}")
    return warehouse


def create_fournisseurs(company):
    """Crée les fournisseurs"""
    fournisseurs_data = [
        {
            'libelle': 'Distributeur Alimentaire SA',
            'telephone': '+213 21 123 456',
            'email': 'contact@dist-alimentaire.dz',
            'adresse': '45 Zone Industrielle, Alger'
        },
        {
            'libelle': 'Boissons du Maghreb',
            'telephone': '+213 21 789 012',
            'email': 'ventes@boissons-maghreb.dz',
            'adresse': '12 Route Nationale, Blida'
        },
        {
            'libelle': 'Produits Laitiers du Sud',
            'telephone': '+213 29 456 789',
            'email': 'commandes@laitiers-sud.dz',
            'adresse': '78 Avenue de l\'Industrie, Oran'
        },
        {
            'libelle': 'Import Export Céréales',
            'telephone': '+213 31 234 567',
            'email': 'info@cereales-import.dz',
            'adresse': '23 Port de Commerce, Annaba'
        },
        {
            'libelle': 'Hygiène et Nettoyage SARL',
            'telephone': '+213 25 345 678',
            'email': 'contact@hygiene-net.dz',
            'adresse': '56 Zone Franche, Constantine'
        }
    ]

    fournisseurs = []
    for data in fournisseurs_data:
        fournisseur, created = Fournisseur.objects.get_or_create(
            company=company,
            libelle=data['libelle'],
            defaults=data
        )
        fournisseurs.append(fournisseur)
        if created:
            print(f"[+] Fournisseur créé: {fournisseur.libelle}")

    return fournisseurs


def create_categories(company):
    """Crée les catégories de produits"""
    categories_data = [
        {'nom': 'Boissons', 'description': 'Eaux, sodas, jus de fruits', 'couleur': '#3498db', 'icone': 'fa-bottle-water'},
        {'nom': 'Produits Laitiers', 'description': 'Lait, yaourt, fromage', 'couleur': '#f1c40f', 'icone': 'fa-cheese'},
        {'nom': 'Épicerie', 'description': 'Produits secs, conserves', 'couleur': '#e74c3c', 'icone': 'fa-store'},
        {'nom': 'Biscuits et Snacks', 'description': 'Biscuits, chips, chocolat', 'couleur': '#9b59b6', 'icone': 'fa-cookie'},
        {'nom': 'Hygiène', 'description': 'Produits d\'hygiène et nettoyage', 'couleur': '#2ecc71', 'icone': 'fa-spray-can'},
    ]

    categories = {}
    for data in categories_data:
        categorie, created = Categorie.objects.get_or_create(
            company=company,
            nom=data['nom'],
            defaults=data
        )
        categories[data['nom']] = categorie
        if created:
            print(f"[+] Catégorie créée: {categorie.nom}")

    return categories


def create_produits(company, categories, fournisseurs, currency):
    """Crée les produits"""
    produits_data = [
        # Boissons
        {'reference': 'BOISS-001', 'code_barre': '6191234567001', 'designation': 'Eau minérale Ifri 1.5L', 'categorie': 'Boissons', 'prixU': '45.00', 'quantite': 0, 'fournisseur_idx': 1, 'unite_mesure': 'piece'},
        {'reference': 'BOISS-002', 'code_barre': '6191234567002', 'designation': 'Coca-Cola 1L', 'categorie': 'Boissons', 'prixU': '120.00', 'quantite': 0, 'fournisseur_idx': 1, 'unite_mesure': 'piece'},
        {'reference': 'BOISS-003', 'code_barre': '6191234567003', 'designation': 'Jus d\'orange Rouiba 1L', 'categorie': 'Boissons', 'prixU': '150.00', 'quantite': 0, 'fournisseur_idx': 1, 'unite_mesure': 'piece'},
        {'reference': 'BOISS-004', 'code_barre': '6191234567004', 'designation': 'Hamoud Boualem Selecto 1L', 'categorie': 'Boissons', 'prixU': '90.00', 'quantite': 0, 'fournisseur_idx': 1, 'unite_mesure': 'piece'},
        {'reference': 'BOISS-005', 'code_barre': '6191234567005', 'designation': 'Eau Saïda 0.5L (pack 6)', 'categorie': 'Boissons', 'prixU': '180.00', 'quantite': 0, 'fournisseur_idx': 1, 'unite_mesure': 'piece'},

        # Produits Laitiers
        {'reference': 'LAIT-001', 'code_barre': '6191234568001', 'designation': 'Lait Candia 1L', 'categorie': 'Produits Laitiers', 'prixU': '130.00', 'quantite': 0, 'fournisseur_idx': 2, 'unite_mesure': 'piece'},
        {'reference': 'LAIT-002', 'code_barre': '6191234568002', 'designation': 'Yaourt Danone Nature (pack 4)', 'categorie': 'Produits Laitiers', 'prixU': '200.00', 'quantite': 0, 'fournisseur_idx': 2, 'unite_mesure': 'piece'},
        {'reference': 'LAIT-003', 'code_barre': '6191234568003', 'designation': 'Fromage La Vache qui rit (16 portions)', 'categorie': 'Produits Laitiers', 'prixU': '350.00', 'quantite': 0, 'fournisseur_idx': 2, 'unite_mesure': 'piece'},
        {'reference': 'LAIT-004', 'code_barre': '6191234568004', 'designation': 'Beurre Soummam 250g', 'categorie': 'Produits Laitiers', 'prixU': '280.00', 'quantite': 0, 'fournisseur_idx': 2, 'unite_mesure': 'piece'},
        {'reference': 'LAIT-005', 'code_barre': '6191234568005', 'designation': 'Crème fraîche Trèfle 20cl', 'categorie': 'Produits Laitiers', 'prixU': '95.00', 'quantite': 0, 'fournisseur_idx': 2, 'unite_mesure': 'piece'},

        # Épicerie
        {'reference': 'EPIC-001', 'code_barre': '6191234569001', 'designation': 'Huile de tournesol Elio 1L', 'categorie': 'Épicerie', 'prixU': '320.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},
        {'reference': 'EPIC-002', 'code_barre': '6191234569002', 'designation': 'Sucre blanc 1kg', 'categorie': 'Épicerie', 'prixU': '120.00', 'quantite': 0, 'fournisseur_idx': 3, 'unite_mesure': 'kg'},
        {'reference': 'EPIC-003', 'code_barre': '6191234569003', 'designation': 'Farine Semoule 1kg', 'categorie': 'Épicerie', 'prixU': '85.00', 'quantite': 0, 'fournisseur_idx': 3, 'unite_mesure': 'kg'},
        {'reference': 'EPIC-004', 'code_barre': '6191234569004', 'designation': 'Tomate concentrée CAB 400g', 'categorie': 'Épicerie', 'prixU': '75.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},
        {'reference': 'EPIC-005', 'code_barre': '6191234569005', 'designation': 'Pâtes Sim 500g', 'categorie': 'Épicerie', 'prixU': '65.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},
        {'reference': 'EPIC-006', 'code_barre': '6191234569006', 'designation': 'Riz Basmati 1kg', 'categorie': 'Épicerie', 'prixU': '250.00', 'quantite': 0, 'fournisseur_idx': 3, 'unite_mesure': 'kg'},
        {'reference': 'EPIC-007', 'code_barre': '6191234569007', 'designation': 'Café Bondin 250g', 'categorie': 'Épicerie', 'prixU': '450.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},

        # Biscuits et Snacks
        {'reference': 'BISC-001', 'code_barre': '6191234570001', 'designation': 'Biscuits Bimo Choco', 'categorie': 'Biscuits et Snacks', 'prixU': '50.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},
        {'reference': 'BISC-002', 'code_barre': '6191234570002', 'designation': 'Chips Star 45g', 'categorie': 'Biscuits et Snacks', 'prixU': '60.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},
        {'reference': 'BISC-003', 'code_barre': '6191234570003', 'designation': 'Chocolat Kinder Bueno', 'categorie': 'Biscuits et Snacks', 'prixU': '150.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},
        {'reference': 'BISC-004', 'code_barre': '6191234570004', 'designation': 'Gaufrettes Chocotom', 'categorie': 'Biscuits et Snacks', 'prixU': '40.00', 'quantite': 0, 'fournisseur_idx': 0, 'unite_mesure': 'piece'},

        # Hygiène
        {'reference': 'HYGI-001', 'code_barre': '6191234571001', 'designation': 'Savon Palmolive 90g', 'categorie': 'Hygiène', 'prixU': '80.00', 'quantite': 0, 'fournisseur_idx': 4, 'unite_mesure': 'piece'},
        {'reference': 'HYGI-002', 'code_barre': '6191234571002', 'designation': 'Shampooing Head & Shoulders 200ml', 'categorie': 'Hygiène', 'prixU': '450.00', 'quantite': 0, 'fournisseur_idx': 4, 'unite_mesure': 'piece'},
        {'reference': 'HYGI-003', 'code_barre': '6191234571003', 'designation': 'Dentifrice Signal 75ml', 'categorie': 'Hygiène', 'prixU': '180.00', 'quantite': 0, 'fournisseur_idx': 4, 'unite_mesure': 'piece'},
        {'reference': 'HYGI-004', 'code_barre': '6191234571004', 'designation': 'Javel ISIS 1L', 'categorie': 'Hygiène', 'prixU': '95.00', 'quantite': 0, 'fournisseur_idx': 4, 'unite_mesure': 'piece'},
        {'reference': 'HYGI-005', 'code_barre': '6191234571005', 'designation': 'Détergent OMO 3kg', 'categorie': 'Hygiène', 'prixU': '850.00', 'quantite': 0, 'fournisseur_idx': 4, 'unite_mesure': 'kg'},
    ]

    produits = []
    for data in produits_data:
        produit, created = Produit.objects.get_or_create(
            company=company,
            reference=data['reference'],
            defaults={
                'code_barre': data['code_barre'],
                'designation': data['designation'],
                'categorie': categories[data['categorie']],
                'prixU': Decimal(data['prixU']),
                'currency': currency,
                'quantite': data['quantite'],
                'seuil_alerte': 20,
                'seuil_critique': 5,
                'unite_mesure': data['unite_mesure'],
                'fournisseur': fournisseurs[data['fournisseur_idx']],
                'is_active': True
            }
        )
        produits.append(produit)
        if created:
            print(f"[+] Produit créé: {produit.designation}")

    return produits


def create_achats(company, produits, fournisseurs, warehouse):
    """Crée des achats pour augmenter le stock"""
    print("\n" + "="*60)
    print("CRÉATION DES ACHATS")
    print("="*60)

    achats_data = [
        # Achats de boissons
        {'produit_ref': 'BOISS-001', 'quantite': 240, 'prix_achat': '35.00', 'fournisseur_idx': 1},
        {'produit_ref': 'BOISS-002', 'quantite': 120, 'prix_achat': '95.00', 'fournisseur_idx': 1},
        {'produit_ref': 'BOISS-003', 'quantite': 96, 'prix_achat': '120.00', 'fournisseur_idx': 1},
        {'produit_ref': 'BOISS-004', 'quantite': 144, 'prix_achat': '70.00', 'fournisseur_idx': 1},
        {'produit_ref': 'BOISS-005', 'quantite': 50, 'prix_achat': '150.00', 'fournisseur_idx': 1},

        # Achats de produits laitiers
        {'produit_ref': 'LAIT-001', 'quantite': 200, 'prix_achat': '100.00', 'fournisseur_idx': 2},
        {'produit_ref': 'LAIT-002', 'quantite': 100, 'prix_achat': '160.00', 'fournisseur_idx': 2},
        {'produit_ref': 'LAIT-003', 'quantite': 80, 'prix_achat': '280.00', 'fournisseur_idx': 2},
        {'produit_ref': 'LAIT-004', 'quantite': 60, 'prix_achat': '220.00', 'fournisseur_idx': 2},
        {'produit_ref': 'LAIT-005', 'quantite': 100, 'prix_achat': '75.00', 'fournisseur_idx': 2},

        # Achats d'épicerie
        {'produit_ref': 'EPIC-001', 'quantite': 100, 'prix_achat': '250.00', 'fournisseur_idx': 0},
        {'produit_ref': 'EPIC-002', 'quantite': 200, 'prix_achat': '95.00', 'fournisseur_idx': 3},
        {'produit_ref': 'EPIC-003', 'quantite': 150, 'prix_achat': '65.00', 'fournisseur_idx': 3},
        {'produit_ref': 'EPIC-004', 'quantite': 200, 'prix_achat': '55.00', 'fournisseur_idx': 0},
        {'produit_ref': 'EPIC-005', 'quantite': 300, 'prix_achat': '50.00', 'fournisseur_idx': 0},
        {'produit_ref': 'EPIC-006', 'quantite': 100, 'prix_achat': '200.00', 'fournisseur_idx': 3},
        {'produit_ref': 'EPIC-007', 'quantite': 80, 'prix_achat': '380.00', 'fournisseur_idx': 0},

        # Achats biscuits et snacks
        {'produit_ref': 'BISC-001', 'quantite': 200, 'prix_achat': '35.00', 'fournisseur_idx': 0},
        {'produit_ref': 'BISC-002', 'quantite': 300, 'prix_achat': '45.00', 'fournisseur_idx': 0},
        {'produit_ref': 'BISC-003', 'quantite': 100, 'prix_achat': '120.00', 'fournisseur_idx': 0},
        {'produit_ref': 'BISC-004', 'quantite': 250, 'prix_achat': '28.00', 'fournisseur_idx': 0},

        # Achats hygiène
        {'produit_ref': 'HYGI-001', 'quantite': 200, 'prix_achat': '60.00', 'fournisseur_idx': 4},
        {'produit_ref': 'HYGI-002', 'quantite': 50, 'prix_achat': '380.00', 'fournisseur_idx': 4},
        {'produit_ref': 'HYGI-003', 'quantite': 100, 'prix_achat': '140.00', 'fournisseur_idx': 4},
        {'produit_ref': 'HYGI-004', 'quantite': 150, 'prix_achat': '70.00', 'fournisseur_idx': 4},
        {'produit_ref': 'HYGI-005', 'quantite': 40, 'prix_achat': '700.00', 'fournisseur_idx': 4},
    ]

    # Créer un dictionnaire des produits par référence
    produits_dict = {p.reference: p for p in produits}

    achats_crees = []
    total_achats = Decimal('0')

    for data in achats_data:
        produit = produits_dict.get(data['produit_ref'])
        if not produit:
            print(f"[!] Produit non trouvé: {data['produit_ref']}")
            continue

        # Créer l'achat
        achat = Achat.objects.create(
            company=company,
            date_Achat=timezone.now().date(),
            quantite=data['quantite'],
            prix_achat=Decimal(data['prix_achat']),
            produit=produit,
            fournisseur=fournisseurs[data['fournisseur_idx']],
            warehouse=warehouse,
            date_expiration=timezone.now().date() + timedelta(days=365)
        )

        # Mettre à jour le stock du produit
        produit.quantite += data['quantite']
        produit.save()

        # Mettre à jour ou créer le ProductStock pour l'entrepôt
        product_stock, created = ProductStock.objects.get_or_create(
            produit=produit,
            warehouse=warehouse,
            defaults={'quantity': 0}
        )
        product_stock.quantity += data['quantite']
        product_stock.save()

        # Créer un mouvement de stock
        StockMove.objects.create(
            produit=produit,
            warehouse=warehouse,
            delta=data['quantite'],
            source='ACHAT',
            ref_id=str(achat.id),
            note=f"Achat du {achat.date_Achat}"
        )

        montant_achat = Decimal(data['prix_achat']) * data['quantite']
        total_achats += montant_achat
        achats_crees.append(achat)

        print(f"[+] Achat: {data['quantite']} x {produit.designation} @ {data['prix_achat']} DA = {montant_achat} DA")

    return achats_crees, total_achats


def print_summary(produits, achats, total_achats):
    """Affiche un résumé des opérations"""
    print("\n" + "="*60)
    print("RÉSUMÉ")
    print("="*60)
    print(f"Produits créés/existants: {len(produits)}")
    print(f"Achats effectués: {len(achats)}")
    print(f"Montant total des achats: {total_achats:,.2f} DA")

    print("\n" + "-"*60)
    print("ÉTAT DU STOCK PAR CATÉGORIE")
    print("-"*60)

    # Grouper les produits par catégorie
    categories_stock = {}
    for produit in produits:
        cat_nom = produit.categorie.nom
        if cat_nom not in categories_stock:
            categories_stock[cat_nom] = {'produits': 0, 'quantite': 0, 'valeur': Decimal('0')}
        categories_stock[cat_nom]['produits'] += 1
        categories_stock[cat_nom]['quantite'] += produit.quantite
        categories_stock[cat_nom]['valeur'] += produit.quantite * produit.prixU

    for cat, stats in categories_stock.items():
        print(f"\n{cat}:")
        print(f"  - Produits: {stats['produits']}")
        print(f"  - Quantité totale: {stats['quantite']}")
        print(f"  - Valeur du stock: {stats['valeur']:,.2f} DA")

    print("\n" + "-"*60)
    print("DÉTAIL DES PRODUITS")
    print("-"*60)
    for produit in produits:
        status = produit.get_stock_status() if hasattr(produit, 'get_stock_status') else 'N/A'
        print(f"{produit.reference}: {produit.designation}")
        print(f"  Stock: {produit.quantite} | Prix: {produit.prixU} DA | Statut: {status}")


def main():
    print("="*60)
    print("CRÉATION DE PRODUITS ET ACHATS")
    print("="*60 + "\n")

    # Étape 1: Créer/récupérer l'entreprise
    company = get_or_create_company()

    # Étape 2: Créer/récupérer la devise
    currency = get_or_create_currency()

    # Étape 3: Créer/récupérer l'entrepôt
    warehouse = get_or_create_warehouse(company)

    # Étape 4: Créer les fournisseurs
    print("\n" + "-"*60)
    print("CRÉATION DES FOURNISSEURS")
    print("-"*60)
    fournisseurs = create_fournisseurs(company)

    # Étape 5: Créer les catégories
    print("\n" + "-"*60)
    print("CRÉATION DES CATÉGORIES")
    print("-"*60)
    categories = create_categories(company)

    # Étape 6: Créer les produits
    print("\n" + "-"*60)
    print("CRÉATION DES PRODUITS")
    print("-"*60)
    produits = create_produits(company, categories, fournisseurs, currency)

    # Étape 7: Effectuer les achats
    achats, total_achats = create_achats(company, produits, fournisseurs, warehouse)

    # Afficher le résumé
    print_summary(produits, achats, total_achats)

    print("\n" + "="*60)
    print("OPÉRATION TERMINÉE AVEC SUCCÈS!")
    print("="*60)


if __name__ == '__main__':
    main()
