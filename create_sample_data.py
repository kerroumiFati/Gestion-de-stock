"""
Script pour créer des données d'exemple dans le logiciel de gestion de stock.
Exécuter avec: python create_sample_data.py
"""
import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from API.models import (
    Company, Categorie, Produit, Client, Fournisseur,
    Achat, Warehouse, ProductStock
)
from django.contrib.auth.models import User

def get_or_create_company():
    """Récupérer ou créer une entreprise par défaut"""
    company, created = Company.objects.get_or_create(
        code="MAIN",
        defaults={
            'name': "Entreprise Principale",
            'email': "contact@entreprise.com",
            'telephone': "0555 123 456",
            'adresse': "123 Rue Principale, Alger",
            'is_active': True
        }
    )
    if created:
        print(f"✅ Entreprise créée: {company.name}")
    else:
        print(f"ℹ️ Entreprise existante: {company.name}")
    return company

def create_categories(company):
    """Créer des catégories d'exemple"""
    categories_data = [
        {'nom': 'Boissons', 'description': 'Boissons gazeuses, jus et eaux', 'couleur': '#3B82F6', 'icone': 'fas fa-glass-water'},
        {'nom': 'Produits Laitiers', 'description': 'Lait, yaourt, fromage', 'couleur': '#F59E0B', 'icone': 'fas fa-cheese'},
        {'nom': 'Snacks', 'description': 'Chips, biscuits, chocolat', 'couleur': '#EF4444', 'icone': 'fas fa-cookie'},
        {'nom': 'Conserves', 'description': 'Conserves de légumes et viandes', 'couleur': '#10B981', 'icone': 'fas fa-jar'},
        {'nom': 'Hygiène', 'description': 'Produits d\'hygiène et nettoyage', 'couleur': '#8B5CF6', 'icone': 'fas fa-soap'},
        {'nom': 'Épicerie', 'description': 'Pâtes, riz, huile, sucre', 'couleur': '#EC4899', 'icone': 'fas fa-wheat-awn'},
    ]

    created_count = 0
    for cat_data in categories_data:
        cat, created = Categorie.objects.get_or_create(
            nom=cat_data['nom'],
            company=company,
            defaults={
                'description': cat_data['description'],
                'couleur': cat_data['couleur'],
                'icone': cat_data['icone'],
                'is_active': True
            }
        )
        if created:
            created_count += 1
            print(f"  ✅ Catégorie créée: {cat.nom}")

    print(f"📁 {created_count} catégories créées")
    return Categorie.objects.filter(company=company)

def create_fournisseurs(company):
    """Créer des fournisseurs d'exemple"""
    fournisseurs_data = [
        {'libelle': 'Coca-Cola Algérie', 'adresse': 'Zone Industrielle, Alger', 'telephone': '0555 111 111', 'email': 'contact@coca-cola.dz'},
        {'libelle': 'PepsiCo Algérie', 'adresse': 'Zone Industrielle, Oran', 'telephone': '0555 222 222', 'email': 'contact@pepsi.dz'},
        {'libelle': 'Danone Djurdjura', 'adresse': 'Tizi Ouzou', 'telephone': '0555 333 333', 'email': 'contact@danone.dz'},
        {'libelle': 'Ifri', 'adresse': 'Béjaïa', 'telephone': '0555 444 444', 'email': 'contact@ifri.dz'},
        {'libelle': 'Cevital', 'adresse': 'Béjaïa', 'telephone': '0555 555 555', 'email': 'contact@cevital.dz'},
        {'libelle': 'Bimo', 'adresse': 'Blida', 'telephone': '0555 666 666', 'email': 'contact@bimo.dz'},
    ]

    created_count = 0
    for four_data in fournisseurs_data:
        four, created = Fournisseur.objects.get_or_create(
            libelle=four_data['libelle'],
            company=company,
            defaults={
                'adresse': four_data['adresse'],
                'telephone': four_data['telephone'],
                'email': four_data['email']
            }
        )
        if created:
            created_count += 1
            print(f"  ✅ Fournisseur créé: {four.libelle}")

    print(f"🏭 {created_count} fournisseurs créés")
    return Fournisseur.objects.filter(company=company)

def create_produits(company, categories, fournisseurs):
    """Créer des produits d'exemple"""

    # Mapper les catégories par nom et fournisseurs par libelle
    cat_map = {cat.nom: cat for cat in categories}
    four_map = {four.libelle: four for four in fournisseurs}

    produits_data = [
        # Boissons
        {'reference': 'COCA-1.5L', 'designation': 'Coca-Cola 1.5L', 'code_barre': '5449000000996', 'prixU': 150, 'categorie': 'Boissons', 'fournisseur': 'Coca-Cola Algérie', 'quantite': 500, 'stock_min': 50},
        {'reference': 'COCA-33CL', 'designation': 'Coca-Cola 33cl', 'code_barre': '5449000000989', 'prixU': 50, 'categorie': 'Boissons', 'fournisseur': 'Coca-Cola Algérie', 'quantite': 1000, 'stock_min': 100},
        {'reference': 'FANTA-1.5L', 'designation': 'Fanta Orange 1.5L', 'code_barre': '5449000001009', 'prixU': 140, 'categorie': 'Boissons', 'fournisseur': 'Coca-Cola Algérie', 'quantite': 300, 'stock_min': 30},
        {'reference': 'PEPSI-1.5L', 'designation': 'Pepsi 1.5L', 'code_barre': '0123456789012', 'prixU': 145, 'categorie': 'Boissons', 'fournisseur': 'PepsiCo Algérie', 'quantite': 400, 'stock_min': 40},
        {'reference': 'IFRI-1.5L', 'designation': 'Eau Ifri 1.5L', 'code_barre': '6191234567890', 'prixU': 40, 'categorie': 'Boissons', 'fournisseur': 'Ifri', 'quantite': 1500, 'stock_min': 200},
        {'reference': 'IFRI-0.5L', 'designation': 'Eau Ifri 0.5L', 'code_barre': '6191234567891', 'prixU': 25, 'categorie': 'Boissons', 'fournisseur': 'Ifri', 'quantite': 2000, 'stock_min': 300},
        {'reference': 'JUS-IFRI-1L', 'designation': 'Jus Ifri Orange 1L', 'code_barre': '6191234567892', 'prixU': 120, 'categorie': 'Boissons', 'fournisseur': 'Ifri', 'quantite': 250, 'stock_min': 30},

        # Produits Laitiers
        {'reference': 'LAIT-CANDIA-1L', 'designation': 'Lait Candia 1L', 'code_barre': '6192234567890', 'prixU': 130, 'categorie': 'Produits Laitiers', 'fournisseur': 'Danone Djurdjura', 'quantite': 800, 'stock_min': 100},
        {'reference': 'YAOURT-DANONE-6', 'designation': 'Yaourt Danone x6', 'code_barre': '6192234567891', 'prixU': 180, 'categorie': 'Produits Laitiers', 'fournisseur': 'Danone Djurdjura', 'quantite': 200, 'stock_min': 50},
        {'reference': 'FROMAGE-VACHE', 'designation': 'Fromage La Vache Qui Rit x8', 'code_barre': '6192234567892', 'prixU': 220, 'categorie': 'Produits Laitiers', 'fournisseur': 'Danone Djurdjura', 'quantite': 150, 'stock_min': 30},

        # Snacks
        {'reference': 'CHIPS-BINGO-100', 'designation': 'Chips Bingo 100g', 'code_barre': '6193234567890', 'prixU': 80, 'categorie': 'Snacks', 'fournisseur': 'Bimo', 'quantite': 400, 'stock_min': 50},
        {'reference': 'CHIPS-BINGO-200', 'designation': 'Chips Bingo 200g', 'code_barre': '6193234567891', 'prixU': 150, 'categorie': 'Snacks', 'fournisseur': 'Bimo', 'quantite': 200, 'stock_min': 30},
        {'reference': 'BISCUIT-BIMO-200', 'designation': 'Biscuits Bimo 200g', 'code_barre': '6193234567892', 'prixU': 120, 'categorie': 'Snacks', 'fournisseur': 'Bimo', 'quantite': 350, 'stock_min': 40},
        {'reference': 'CHOCO-KINDER', 'designation': 'Kinder Bueno', 'code_barre': '6193234567893', 'prixU': 100, 'categorie': 'Snacks', 'fournisseur': 'Bimo', 'quantite': 500, 'stock_min': 60},

        # Conserves
        {'reference': 'TOMATE-CEVITAL', 'designation': 'Double Concentré Tomate 400g', 'code_barre': '6194234567890', 'prixU': 95, 'categorie': 'Conserves', 'fournisseur': 'Cevital', 'quantite': 300, 'stock_min': 40},
        {'reference': 'HARISSA-400', 'designation': 'Harissa 400g', 'code_barre': '6194234567891', 'prixU': 85, 'categorie': 'Conserves', 'fournisseur': 'Cevital', 'quantite': 250, 'stock_min': 30},
        {'reference': 'THON-CONS', 'designation': 'Thon en conserve 160g', 'code_barre': '6194234567892', 'prixU': 280, 'categorie': 'Conserves', 'fournisseur': 'Cevital', 'quantite': 180, 'stock_min': 25},

        # Épicerie
        {'reference': 'HUILE-FLEURIAL-5L', 'designation': 'Huile Fleurial 5L', 'code_barre': '6195234567890', 'prixU': 850, 'categorie': 'Épicerie', 'fournisseur': 'Cevital', 'quantite': 150, 'stock_min': 20},
        {'reference': 'SUCRE-1KG', 'designation': 'Sucre 1kg', 'code_barre': '6195234567891', 'prixU': 110, 'categorie': 'Épicerie', 'fournisseur': 'Cevital', 'quantite': 600, 'stock_min': 80},
        {'reference': 'PATES-500', 'designation': 'Pâtes Spaghetti 500g', 'code_barre': '6195234567892', 'prixU': 75, 'categorie': 'Épicerie', 'fournisseur': 'Cevital', 'quantite': 400, 'stock_min': 50},
        {'reference': 'RIZ-1KG', 'designation': 'Riz Basmati 1kg', 'code_barre': '6195234567893', 'prixU': 180, 'categorie': 'Épicerie', 'fournisseur': 'Cevital', 'quantite': 300, 'stock_min': 40},

        # Hygiène
        {'reference': 'SAVON-LUX', 'designation': 'Savon Lux 100g', 'code_barre': '6196234567890', 'prixU': 65, 'categorie': 'Hygiène', 'fournisseur': 'Cevital', 'quantite': 500, 'stock_min': 60},
        {'reference': 'SHAMPOING-HEAD', 'designation': 'Shampoing Head & Shoulders 200ml', 'code_barre': '6196234567891', 'prixU': 350, 'categorie': 'Hygiène', 'fournisseur': 'Cevital', 'quantite': 120, 'stock_min': 20},
        {'reference': 'DENTIFRICE-SIG', 'designation': 'Dentifrice Signal 75ml', 'code_barre': '6196234567892', 'prixU': 180, 'categorie': 'Hygiène', 'fournisseur': 'Cevital', 'quantite': 200, 'stock_min': 30},
    ]

    created_count = 0
    for prod_data in produits_data:
        categorie = cat_map.get(prod_data['categorie'])
        fournisseur = four_map.get(prod_data['fournisseur'])

        prod, created = Produit.objects.get_or_create(
            reference=prod_data['reference'],
            company=company,
            defaults={
                'designation': prod_data['designation'],
                'code_barre': prod_data['code_barre'],
                'prixU': Decimal(str(prod_data['prixU'])),
                'categorie': categorie,
                'fournisseur': fournisseur,
                'quantite': prod_data['quantite'],
                'seuil_alerte': prod_data['stock_min'],
                'seuil_critique': prod_data['stock_min'] // 2,
                'is_active': True
            }
        )
        if created:
            created_count += 1
            print(f"  ✅ Produit créé: {prod.designation}")

    print(f"📦 {created_count} produits créés")
    return Produit.objects.filter(company=company, is_active=True)

def create_clients(company):
    """Créer des clients d'exemple"""

    # Coordonnées GPS autour d'Alger
    clients_data = [
        {'nom': 'Superette Bab El Oued', 'prenom': '', 'telephone': '0555 100 001', 'adresse': '12 Rue Bab El Oued, Alger', 'lat': 36.7894, 'lng': 3.0471, 'email': 'babeloued@email.dz'},
        {'nom': 'Epicerie El Harrach', 'prenom': '', 'telephone': '0555 100 002', 'adresse': '45 Boulevard El Harrach', 'lat': 36.7200, 'lng': 3.1400, 'email': 'elharrach@email.dz'},
        {'nom': 'Mini Market Hussein Dey', 'prenom': '', 'telephone': '0555 100 003', 'adresse': '78 Rue Hussein Dey', 'lat': 36.7400, 'lng': 3.1000, 'email': 'husseindey@email.dz'},
        {'nom': 'Alimentation Kouba', 'prenom': '', 'telephone': '0555 100 004', 'adresse': '23 Rue Kouba, Alger', 'lat': 36.7300, 'lng': 3.0550, 'email': 'kouba@email.dz'},
        {'nom': 'Supermarche Rouiba', 'prenom': '', 'telephone': '0555 100 005', 'adresse': '56 Zone Industrielle Rouiba', 'lat': 36.7350, 'lng': 3.2800, 'email': 'rouiba@email.dz'},
        {'nom': 'Epicerie Ben Aknoun', 'prenom': '', 'telephone': '0555 100 006', 'adresse': '89 Rue Ben Aknoun', 'lat': 36.7650, 'lng': 3.0100, 'email': 'benaknoun@email.dz'},
        {'nom': 'Boutique Dar El Beida', 'prenom': '', 'telephone': '0555 100 007', 'adresse': '34 Avenue Dar El Beida', 'lat': 36.7150, 'lng': 3.2100, 'email': 'darelbeida@email.dz'},
        {'nom': 'Magasin Bir Mourad Rais', 'prenom': '', 'telephone': '0555 100 008', 'adresse': '67 Rue Bir Mourad Rais', 'lat': 36.7450, 'lng': 3.0350, 'email': 'birmourad@email.dz'},
        {'nom': 'Alimentation Draria', 'prenom': '', 'telephone': '0555 100 009', 'adresse': '90 Centre Draria', 'lat': 36.7250, 'lng': 2.9700, 'email': 'draria@email.dz'},
        {'nom': 'Superette Bouzareah', 'prenom': '', 'telephone': '0555 100 010', 'adresse': '12 Rue Bouzareah', 'lat': 36.7850, 'lng': 3.0200, 'email': 'bouzareah@email.dz'},
        {'nom': 'Epicerie Ain Naadja', 'prenom': '', 'telephone': '0555 100 011', 'adresse': '45 Cite Ain Naadja', 'lat': 36.7100, 'lng': 3.0800, 'email': 'ainnaadja@email.dz'},
        {'nom': 'Mini Market Bordj El Kiffan', 'prenom': '', 'telephone': '0555 100 012', 'adresse': '78 Boulevard Bordj El Kiffan', 'lat': 36.7500, 'lng': 3.1800, 'email': 'bordjelkiffan@email.dz'},
        {'nom': 'Boutique Mohammadia', 'prenom': '', 'telephone': '0555 100 013', 'adresse': '23 Rue Mohammadia', 'lat': 36.7350, 'lng': 3.1500, 'email': 'mohammadia@email.dz'},
        {'nom': 'Alimentation Bachdjerrah', 'prenom': '', 'telephone': '0555 100 014', 'adresse': '56 Cite Bachdjerrah', 'lat': 36.7200, 'lng': 3.1100, 'email': 'bachdjerrah@email.dz'},
        {'nom': 'Supermarche Dely Ibrahim', 'prenom': '', 'telephone': '0555 100 015', 'adresse': '89 Centre Dely Ibrahim', 'lat': 36.7550, 'lng': 2.9900, 'email': 'delyibrahim@email.dz'},
        {'nom': 'Magasin El Mouradia', 'prenom': '', 'telephone': '0555 100 016', 'adresse': '34 Rue El Mouradia', 'lat': 36.7600, 'lng': 3.0400, 'email': 'elmouradia@email.dz'},
        {'nom': 'Epicerie Hydra', 'prenom': '', 'telephone': '0555 100 017', 'adresse': '67 Boulevard Hydra', 'lat': 36.7700, 'lng': 3.0250, 'email': 'hydra@email.dz'},
        {'nom': 'Boutique Cheraga', 'prenom': '', 'telephone': '0555 100 018', 'adresse': '90 Centre Cheraga', 'lat': 36.7650, 'lng': 2.9500, 'email': 'cheraga@email.dz'},
        {'nom': 'Alimentation Ouled Fayet', 'prenom': '', 'telephone': '0555 100 019', 'adresse': '12 Cite Ouled Fayet', 'lat': 36.7400, 'lng': 2.9300, 'email': 'ouledfayet@email.dz'},
        {'nom': 'Superette El Biar', 'prenom': '', 'telephone': '0555 100 020', 'adresse': '45 Rue El Biar', 'lat': 36.7750, 'lng': 3.0300, 'email': 'elbiar@email.dz'},
    ]

    created_count = 0
    for cli_data in clients_data:
        client, created = Client.objects.get_or_create(
            nom=cli_data['nom'],
            company=company,
            defaults={
                'prenom': cli_data['prenom'],
                'telephone': cli_data['telephone'],
                'adresse': cli_data['adresse'],
                'email': cli_data['email'],
                'lat': Decimal(str(cli_data['lat'])),
                'lng': Decimal(str(cli_data['lng']))
            }
        )
        if created:
            created_count += 1
            print(f"  ✅ Client créé: {client.nom}")

    print(f"👥 {created_count} clients créés")
    return Client.objects.filter(company=company)

def create_warehouse(company):
    """Créer un entrepôt principal"""
    warehouse, created = Warehouse.objects.get_or_create(
        code='DEPOT-MAIN',
        company=company,
        defaults={
            'name': 'Depot Principal',
            'is_active': True
        }
    )
    if created:
        print(f"✅ Entrepôt créé: {warehouse.name}")
    else:
        print(f"ℹ️ Entrepôt existant: {warehouse.name}")
    return warehouse

def create_achats(company, fournisseurs, produits, warehouse):
    """Créer des achats d'exemple"""

    four_list = list(fournisseurs)
    prod_list = list(produits)

    # Créer des achats pour différents produits
    created_count = 0

    for prod in prod_list[:15]:  # Créer des achats pour les 15 premiers produits
        fournisseur = prod.fournisseur if prod.fournisseur else random.choice(four_list)
        date_achat = datetime.now() - timedelta(days=random.randint(1, 30))
        date_expiration = datetime.now() + timedelta(days=random.randint(90, 365))

        quantite = random.randint(50, 200)
        prix_achat = prod.prixU * Decimal('0.7')  # Prix d'achat = 70% du prix de vente

        # Vérifier si un achat similaire existe déjà
        existing = Achat.objects.filter(
            produit=prod,
            date_Achat=date_achat.date(),
            company=company
        ).first()

        if existing:
            continue

        achat = Achat.objects.create(
            company=company,
            produit=prod,
            fournisseur=fournisseur,
            warehouse=warehouse,
            date_Achat=date_achat.date(),
            date_expiration=date_expiration.date(),
            quantite=quantite,
            prix_achat=prix_achat,
            unite_achat='piece',
            pieces_par_carton=1
        )

        created_count += 1
        print(f"  ✅ Achat créé: {prod.designation} - {quantite} pcs - {prix_achat:.2f} DA/u")

    print(f"🛒 {created_count} achats créés")

def main():
    print("=" * 60)
    print("🚀 CRÉATION DES DONNÉES D'EXEMPLE")
    print("=" * 60)
    print()

    # 1. Entreprise
    print("1️⃣ Entreprise...")
    company = get_or_create_company()
    print()

    # 2. Catégories
    print("2️⃣ Catégories...")
    categories = create_categories(company)
    print()

    # 3. Fournisseurs
    print("3️⃣ Fournisseurs...")
    fournisseurs = create_fournisseurs(company)
    print()

    # 4. Produits
    print("4️⃣ Produits...")
    produits = create_produits(company, categories, fournisseurs)
    print()

    # 5. Clients
    print("5️⃣ Clients...")
    clients = create_clients(company)
    print()

    # 6. Entrepôt
    print("6️⃣ Entrepôt...")
    warehouse = create_warehouse(company)
    print()

    # 7. Achats
    print("7️⃣ Achats...")
    create_achats(company, fournisseurs, produits, warehouse)
    print()

    # Résumé
    print("=" * 60)
    print("✅ CRÉATION TERMINÉE - RÉSUMÉ")
    print("=" * 60)
    print(f"  📁 Catégories: {Categorie.objects.filter(company=company).count()}")
    print(f"  🏭 Fournisseurs: {Fournisseur.objects.filter(company=company).count()}")
    print(f"  📦 Produits: {Produit.objects.filter(company=company, is_active=True).count()}")
    print(f"  👥 Clients: {Client.objects.filter(company=company).count()}")
    print(f"  🏢 Entrepôts: {Warehouse.objects.filter(company=company).count()}")
    print(f"  🛒 Achats: {Achat.objects.filter(company=company).count()}")
    print()
    print("💡 Connectez-vous au logiciel pour voir les données !")

if __name__ == '__main__':
    main()
