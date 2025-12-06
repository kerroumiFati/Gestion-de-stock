"""
Commande Django pour générer des données d'exemple complètes
Couvre toutes les fonctionnalités du système de gestion de stock
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta, datetime, time
import random

from API.models import (
    Company, UserProfile, Currency, ExchangeRate, Fournisseur,
    Categorie, TypePrix, Produit, PrixProduit, Client, Achat,
    BonLivraison, LigneLivraison, Facture, LigneFacture,
    Warehouse, ProductStock, StockMove, InventorySession, InventoryLine,
    Vente, LigneVente, Livreur, Tournee, ArretLivraison,
    TransfertStock, LigneTransfertStock, SystemConfig
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Génère des données d\'exemple complètes pour toutes les fonctionnalités'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Supprime toutes les données existantes avant de générer les exemples',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Suppression des données existantes...'))
            self.clear_data()

        self.stdout.write(self.style.SUCCESS('Génération des données d\'exemple...'))

        # 1. Devises
        self.stdout.write('1. Création des devises...')
        self.create_currencies()

        # 2. Entreprises et utilisateurs
        self.stdout.write('2. Création des entreprises et utilisateurs...')
        self.create_companies_and_users()

        # 3. Configuration système
        self.stdout.write('3. Configuration du système...')
        self.create_system_config()

        # 4. Entrepôts
        self.stdout.write('4. Création des entrepôts...')
        self.create_warehouses()

        # 5. Fournisseurs
        self.stdout.write('5. Création des fournisseurs...')
        self.create_suppliers()

        # 6. Catégories de produits
        self.stdout.write('6. Création des catégories...')
        self.create_categories()

        # 7. Types de prix
        self.stdout.write('7. Création des types de prix...')
        self.create_price_types()

        # 8. Produits
        self.stdout.write('8. Création des produits...')
        self.create_products()

        # 9. Prix multiples pour produits
        self.stdout.write('9. Création des prix multiples...')
        self.create_product_prices()

        # 10. Clients
        self.stdout.write('10. Création des clients...')
        self.create_clients()

        # 11. Achats
        self.stdout.write('11. Création des achats...')
        self.create_purchases()

        # 12. Stocks
        self.stdout.write('12. Création des stocks...')
        self.create_stocks()

        # 13. Mouvements de stock
        self.stdout.write('13. Création des mouvements de stock...')
        self.create_stock_moves()

        # 14. Inventaires
        self.stdout.write('14. Création des sessions d\'inventaire...')
        self.create_inventory_sessions()

        # 15. Bons de livraison
        self.stdout.write('15. Création des bons de livraison...')
        self.create_delivery_notes()

        # 16. Factures
        self.stdout.write('16. Création des factures...')
        self.create_invoices()

        # 17. Ventes
        self.stdout.write('17. Création des ventes...')
        self.create_sales()

        # 18. Livreurs
        self.stdout.write('18. Création des livreurs...')
        self.create_delivery_drivers()

        # 19. Tournées de livraison
        self.stdout.write('19. Création des tournées...')
        self.create_delivery_tours()

        # 20. Transferts de stock
        self.stdout.write('20. Création des transferts de stock...')
        self.create_stock_transfers()

        self.stdout.write(self.style.SUCCESS('\n✓ Génération terminée avec succès!'))
        self.print_summary()

    def clear_data(self):
        """Supprime toutes les données"""
        models_to_clear = [
            LigneTransfertStock, TransfertStock, ArretLivraison, Tournee, Livreur,
            LigneVente, Vente, InventoryLine, InventorySession, StockMove,
            ProductStock, LigneFacture, Facture, LigneLivraison, BonLivraison,
            Achat, PrixProduit, Produit, TypePrix, Categorie, Client,
            Fournisseur, Warehouse, ExchangeRate, Currency,
            UserProfile, Company
        ]

        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f'  - {model.__name__}: {count} supprimés')

    def create_currencies(self):
        """Crée les devises"""
        currencies_data = [
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€', 'is_default': True},
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$', 'is_default': False},
            {'code': 'MAD', 'name': 'Dirham marocain', 'symbol': 'DH', 'is_default': False},
            {'code': 'GBP', 'name': 'Livre sterling', 'symbol': '£', 'is_default': False},
        ]

        for curr_data in currencies_data:
            currency, created = Currency.objects.get_or_create(
                code=curr_data['code'],
                defaults=curr_data
            )
            if created:
                self.stdout.write(f'  ✓ {currency.code} - {currency.name}')

        # Taux de change
        eur = Currency.objects.get(code='EUR')
        usd = Currency.objects.get(code='USD')
        mad = Currency.objects.get(code='MAD')
        gbp = Currency.objects.get(code='GBP')

        rates = [
            (eur, usd, Decimal('1.10')),
            (eur, mad, Decimal('10.80')),
            (eur, gbp, Decimal('0.86')),
            (usd, mad, Decimal('9.82')),
        ]

        for from_curr, to_curr, rate in rates:
            ExchangeRate.objects.get_or_create(
                from_currency=from_curr,
                to_currency=to_curr,
                date=timezone.now().date(),
                defaults={'rate': rate}
            )

    def create_companies_and_users(self):
        """Crée les entreprises et utilisateurs"""
        companies_data = [
            {
                'name': 'TechStore SARL',
                'code': 'TECH01',
                'email': 'contact@techstore.com',
                'telephone': '+212 5 22 00 11 22',
                'adresse': '123 Bd Mohammed V, Casablanca',
                'tax_id': 'ICE001234567890123'
            },
            {
                'name': 'Distribution Plus',
                'code': 'DIST01',
                'email': 'info@distplus.ma',
                'telephone': '+212 5 37 11 22 33',
                'adresse': '45 Avenue Hassan II, Rabat',
                'tax_id': 'ICE002345678901234'
            }
        ]

        self.companies = {}
        for comp_data in companies_data:
            company, created = Company.objects.get_or_create(
                code=comp_data['code'],
                defaults=comp_data
            )
            self.companies[comp_data['code']] = company
            if created:
                self.stdout.write(f'  ✓ {company.name}')

                # Créer des utilisateurs pour chaque entreprise
                for role, role_name in [('admin', 'Administrateur'), ('manager', 'Gestionnaire'), ('employee', 'Employé')]:
                    username = f"{comp_data['code'].lower()}_{role}"
                    user, u_created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'email': f'{username}@example.com',
                            'first_name': role_name,
                            'last_name': company.name.split()[0],
                            'is_active': True
                        }
                    )
                    if u_created:
                        user.set_password('password123')
                        user.save()

                    UserProfile.objects.get_or_create(
                        user=user,
                        defaults={'company': company, 'role': role}
                    )

    def create_system_config(self):
        """Configure le système"""
        config = SystemConfig.get_solo()
        config.default_currency = Currency.objects.get(code='EUR')
        config.language = 'fr'
        config.auto_print_ticket = True
        config.ticket_footer_message = 'Merci de votre visite!\nÀ bientôt!'
        config.ticket_company_name = 'TechStore SARL'
        config.ticket_company_address = '123 Bd Mohammed V, Casablanca'
        config.ticket_company_phone = '+212 5 22 00 11 22'
        config.save()

    def create_warehouses(self):
        """Crée les entrepôts"""
        self.warehouses = {}

        for company in Company.objects.all():
            warehouses_data = [
                {'name': 'Entrepôt Principal', 'code': f'{company.code}-WH01'},
                {'name': 'Entrepôt Secondaire', 'code': f'{company.code}-WH02'},
                {'name': 'Van Livreur 1', 'code': f'{company.code}-VAN01'},
                {'name': 'Van Livreur 2', 'code': f'{company.code}-VAN02'},
            ]

            for wh_data in warehouses_data:
                warehouse, created = Warehouse.objects.get_or_create(
                    company=company,
                    code=wh_data['code'],
                    defaults={'name': wh_data['name']}
                )
                self.warehouses[wh_data['code']] = warehouse

        # Définir l'entrepôt par défaut
        config = SystemConfig.get_solo()
        config.default_warehouse = Warehouse.objects.first()
        config.save()

    def create_suppliers(self):
        """Crée les fournisseurs"""
        self.suppliers = {}

        suppliers_data = [
            {
                'libelle': 'TechSupply International',
                'telephone': '+33 1 23 45 67 89',
                'email': 'contact@techsupply.fr',
                'adresse': '12 Rue de la Tech, 75001 Paris, France'
            },
            {
                'libelle': 'ElectroMaroc',
                'telephone': '+212 5 22 33 44 55',
                'email': 'info@electromaroc.ma',
                'adresse': 'Zone Industrielle, Casablanca'
            },
            {
                'libelle': 'Global Electronics',
                'telephone': '+1 555 123 4567',
                'email': 'sales@globalelec.com',
                'adresse': '1234 Tech Ave, San Francisco, CA 94102, USA'
            },
            {
                'libelle': 'Fournitures Bureau Plus',
                'telephone': '+212 5 37 66 77 88',
                'email': 'contact@bureauplus.ma',
                'adresse': '78 Avenue Allal Ben Abdellah, Rabat'
            }
        ]

        for company in Company.objects.all():
            for supp_data in suppliers_data:
                supplier, created = Fournisseur.objects.get_or_create(
                    company=company,
                    libelle=supp_data['libelle'],
                    defaults=supp_data
                )
                key = f"{company.code}_{supp_data['libelle']}"
                self.suppliers[key] = supplier

    def create_categories(self):
        """Crée les catégories de produits avec hiérarchie"""
        self.categories = {}

        categories_structure = {
            'Électronique': {
                'couleur': '#007bff',
                'icone': 'fa-laptop',
                'sous_categories': ['Ordinateurs', 'Smartphones', 'Tablettes', 'Accessoires']
            },
            'Informatique': {
                'couleur': '#28a745',
                'icone': 'fa-desktop',
                'sous_categories': ['Périphériques', 'Composants', 'Réseau', 'Stockage']
            },
            'Électroménager': {
                'couleur': '#ffc107',
                'icone': 'fa-blender',
                'sous_categories': ['Cuisine', 'Nettoyage', 'Climatisation']
            },
            'Bureau': {
                'couleur': '#17a2b8',
                'icone': 'fa-briefcase',
                'sous_categories': ['Fournitures', 'Mobilier', 'Papeterie']
            }
        }

        for company in Company.objects.all():
            for cat_name, cat_info in categories_structure.items():
                parent_cat, created = Categorie.objects.get_or_create(
                    company=company,
                    nom=cat_name,
                    defaults={
                        'description': f'Catégorie {cat_name}',
                        'couleur': cat_info['couleur'],
                        'icone': cat_info['icone']
                    }
                )
                key = f"{company.code}_{cat_name}"
                self.categories[key] = parent_cat

                # Sous-catégories
                for sub_cat_name in cat_info['sous_categories']:
                    sub_cat, _ = Categorie.objects.get_or_create(
                        company=company,
                        nom=sub_cat_name,
                        defaults={
                            'description': f'Sous-catégorie {sub_cat_name}',
                            'parent': parent_cat,
                            'couleur': cat_info['couleur'],
                            'icone': cat_info['icone']
                        }
                    )
                    sub_key = f"{company.code}_{cat_name}_{sub_cat_name}"
                    self.categories[sub_key] = sub_cat

    def create_price_types(self):
        """Crée les types de prix"""
        price_types_data = [
            {'code': 'DETAIL', 'libelle': 'Prix Détaillant', 'ordre': 1, 'is_default': True},
            {'code': 'GROSS', 'libelle': 'Prix Grossiste', 'ordre': 2},
            {'code': 'PROMO', 'libelle': 'Prix Promotionnel', 'ordre': 3},
            {'code': 'VIP', 'libelle': 'Prix VIP', 'ordre': 4},
        ]

        self.price_types = {}
        for pt_data in price_types_data:
            price_type, created = TypePrix.objects.get_or_create(
                code=pt_data['code'],
                defaults=pt_data
            )
            self.price_types[pt_data['code']] = price_type

    def create_products(self):
        """Crée les produits"""
        self.products = []

        products_data = [
            # Électronique > Ordinateurs
            {
                'reference': 'LAP-001',
                'code_barre': '3760123456789',
                'designation': 'Laptop Dell XPS 15',
                'description': 'Ordinateur portable haute performance, écran 15.6", Intel i7, 16GB RAM, 512GB SSD',
                'category': 'Ordinateurs',
                'prixU': Decimal('1299.99'),
                'quantite': 25,
                'seuil_alerte': 10,
                'seuil_critique': 5,
                'unite_mesure': 'piece',
                'poids': Decimal('1.8')
            },
            {
                'reference': 'LAP-002',
                'code_barre': '3760123456790',
                'designation': 'MacBook Pro 14"',
                'description': 'Apple MacBook Pro 14 pouces, M3 Pro, 18GB RAM, 512GB SSD',
                'category': 'Ordinateurs',
                'prixU': Decimal('2499.00'),
                'quantite': 15,
                'seuil_alerte': 8,
                'seuil_critique': 3,
                'unite_mesure': 'piece',
                'poids': Decimal('1.6')
            },
            # Électronique > Smartphones
            {
                'reference': 'PHN-001',
                'code_barre': '3760123456791',
                'designation': 'iPhone 15 Pro 256GB',
                'description': 'Apple iPhone 15 Pro, 256GB, Titane Naturel',
                'category': 'Smartphones',
                'prixU': Decimal('1229.00'),
                'quantite': 40,
                'seuil_alerte': 15,
                'seuil_critique': 8,
                'unite_mesure': 'piece',
                'poids': Decimal('0.187')
            },
            {
                'reference': 'PHN-002',
                'code_barre': '3760123456792',
                'designation': 'Samsung Galaxy S24 Ultra',
                'description': 'Samsung Galaxy S24 Ultra, 512GB, Noir Titanium',
                'category': 'Smartphones',
                'prixU': Decimal('1399.00'),
                'quantite': 30,
                'seuil_alerte': 12,
                'seuil_critique': 6,
                'unite_mesure': 'piece',
                'poids': Decimal('0.233')
            },
            # Électronique > Accessoires
            {
                'reference': 'ACC-001',
                'code_barre': '3760123456793',
                'designation': 'Écouteurs AirPods Pro 2',
                'description': 'Apple AirPods Pro 2ème génération avec réduction de bruit active',
                'category': 'Accessoires',
                'prixU': Decimal('279.00'),
                'quantite': 60,
                'seuil_alerte': 20,
                'seuil_critique': 10,
                'unite_mesure': 'piece',
                'poids': Decimal('0.056')
            },
            {
                'reference': 'ACC-002',
                'code_barre': '3760123456794',
                'designation': 'Chargeur USB-C 65W',
                'description': 'Chargeur rapide USB-C 65W compatible MacBook, iPad, iPhone',
                'category': 'Accessoires',
                'prixU': Decimal('49.99'),
                'quantite': 100,
                'seuil_alerte': 30,
                'seuil_critique': 15,
                'unite_mesure': 'piece',
                'poids': Decimal('0.185')
            },
            # Informatique > Périphériques
            {
                'reference': 'PER-001',
                'code_barre': '3760123456795',
                'designation': 'Clavier Mécanique Logitech MX',
                'description': 'Clavier mécanique sans fil rétroéclairé',
                'category': 'Périphériques',
                'prixU': Decimal('149.99'),
                'quantite': 45,
                'seuil_alerte': 15,
                'seuil_critique': 8,
                'unite_mesure': 'piece',
                'poids': Decimal('0.810')
            },
            {
                'reference': 'PER-002',
                'code_barre': '3760123456796',
                'designation': 'Souris Logitech MX Master 3S',
                'description': 'Souris sans fil ergonomique haute précision',
                'category': 'Périphériques',
                'prixU': Decimal('109.99'),
                'quantite': 55,
                'seuil_alerte': 20,
                'seuil_critique': 10,
                'unite_mesure': 'piece',
                'poids': Decimal('0.141')
            },
            # Informatique > Stockage
            {
                'reference': 'STO-001',
                'code_barre': '3760123456797',
                'designation': 'SSD Samsung 1TB NVMe',
                'description': 'Disque SSD NVMe M.2 1To, lecture 7000MB/s',
                'category': 'Stockage',
                'prixU': Decimal('119.99'),
                'quantite': 70,
                'seuil_alerte': 25,
                'seuil_critique': 12,
                'unite_mesure': 'piece',
                'poids': Decimal('0.008')
            },
            {
                'reference': 'STO-002',
                'code_barre': '3760123456798',
                'designation': 'Disque Dur Externe 4TB',
                'description': 'HDD externe USB 3.0, 4To, portable',
                'category': 'Stockage',
                'prixU': Decimal('89.99'),
                'quantite': 50,
                'seuil_alerte': 18,
                'seuil_critique': 9,
                'unite_mesure': 'piece',
                'poids': Decimal('0.230')
            },
            # Bureau > Fournitures
            {
                'reference': 'BUR-001',
                'code_barre': '3760123456799',
                'designation': 'Ramette Papier A4 500 feuilles',
                'description': 'Papier blanc A4 80g/m², 500 feuilles',
                'category': 'Fournitures',
                'prixU': Decimal('4.99'),
                'quantite': 200,
                'seuil_alerte': 50,
                'seuil_critique': 25,
                'unite_mesure': 'piece',
                'poids': Decimal('2.5')
            },
            {
                'reference': 'BUR-002',
                'code_barre': '3760123456800',
                'designation': 'Stylos BIC Cristal x10',
                'description': 'Lot de 10 stylos bille BIC Cristal bleu',
                'category': 'Fournitures',
                'prixU': Decimal('3.49'),
                'quantite': 150,
                'seuil_alerte': 40,
                'seuil_critique': 20,
                'unite_mesure': 'piece',
                'poids': Decimal('0.065')
            },
        ]

        eur = Currency.objects.get(code='EUR')

        for company in Company.objects.all():
            suppliers = list(Fournisseur.objects.filter(company=company))

            for prod_data in products_data:
                # Trouver la catégorie
                parent_cat_name = None
                if prod_data['category'] in ['Ordinateurs', 'Smartphones', 'Tablettes', 'Accessoires']:
                    parent_cat_name = 'Électronique'
                elif prod_data['category'] in ['Périphériques', 'Composants', 'Réseau', 'Stockage']:
                    parent_cat_name = 'Informatique'
                elif prod_data['category'] in ['Fournitures', 'Mobilier', 'Papeterie']:
                    parent_cat_name = 'Bureau'

                cat_key = f"{company.code}_{parent_cat_name}_{prod_data['category']}"
                category = self.categories.get(cat_key)

                if not category:
                    continue

                product, created = Produit.objects.get_or_create(
                    company=company,
                    reference=prod_data['reference'],
                    defaults={
                        'code_barre': prod_data['code_barre'],
                        'designation': prod_data['designation'],
                        'description': prod_data['description'],
                        'categorie': category,
                        'prixU': prod_data['prixU'],
                        'currency': eur,
                        'quantite': prod_data['quantite'],
                        'seuil_alerte': prod_data['seuil_alerte'],
                        'seuil_critique': prod_data['seuil_critique'],
                        'unite_mesure': prod_data['unite_mesure'],
                        'poids': prod_data.get('poids'),
                        'fournisseur': random.choice(suppliers)
                    }
                )

                if created:
                    self.products.append(product)

    def create_product_prices(self):
        """Crée les prix multiples pour les produits"""
        for product in Produit.objects.all()[:20]:  # Les 20 premiers produits
            base_price = product.prixU

            # Prix détaillant (par défaut, déjà dans le produit)
            PrixProduit.objects.get_or_create(
                produit=product,
                type_prix=self.price_types['DETAIL'],
                defaults={
                    'prix': base_price,
                    'quantite_min': 1
                }
            )

            # Prix grossiste (-15%)
            PrixProduit.objects.get_or_create(
                produit=product,
                type_prix=self.price_types['GROSS'],
                defaults={
                    'prix': base_price * Decimal('0.85'),
                    'quantite_min': 10
                }
            )

            # Prix promotionnel (-20%, temporaire)
            PrixProduit.objects.get_or_create(
                produit=product,
                type_prix=self.price_types['PROMO'],
                defaults={
                    'prix': base_price * Decimal('0.80'),
                    'quantite_min': 1,
                    'date_debut': timezone.now().date(),
                    'date_fin': timezone.now().date() + timedelta(days=30)
                }
            )

            # Prix VIP (-25%)
            PrixProduit.objects.get_or_create(
                produit=product,
                type_prix=self.price_types['VIP'],
                defaults={
                    'prix': base_price * Decimal('0.75'),
                    'quantite_min': 1
                }
            )

    def create_clients(self):
        """Crée les clients"""
        self.clients = []

        clients_data = [
            {'nom': 'Alami', 'prenom': 'Mohammed', 'email': 'malami@email.com', 'telephone': '0661234567', 'adresse': '12 Rue Atlas, Casablanca'},
            {'nom': 'Bennani', 'prenom': 'Fatima', 'email': 'fbennani@email.com', 'telephone': '0662345678', 'adresse': '34 Av Hassan II, Rabat'},
            {'nom': 'Cohen', 'prenom': 'David', 'email': 'dcohen@email.com', 'telephone': '0663456789', 'adresse': '56 Bd Zerktouni, Casablanca'},
            {'nom': 'Idrissi', 'prenom': 'Amina', 'email': 'aidrissi@email.com', 'telephone': '0664567890', 'adresse': '78 Rue Oujda, Rabat'},
            {'nom': 'El Fassi', 'prenom': 'Youssef', 'email': 'yelfassi@email.com', 'telephone': '0665678901', 'adresse': '90 Av Royale, Fès'},
            {'nom': 'Tazi', 'prenom': 'Laila', 'email': 'ltazi@email.com', 'telephone': '0666789012', 'adresse': '21 Bd Mohammed V, Marrakech'},
            {'nom': 'Benjelloun', 'prenom': 'Karim', 'email': 'kbenjelloun@email.com', 'telephone': '0667890123', 'adresse': '43 Rue Tanger, Casablanca'},
            {'nom': 'Rachidi', 'prenom': 'Nadia', 'email': 'nrachidi@email.com', 'telephone': '0668901234', 'adresse': '65 Av Mers Sultan, Casablanca'},
            {'nom': 'Berrada', 'prenom': 'Omar', 'email': 'oberrada@email.com', 'telephone': '0669012345', 'adresse': '87 Rue Agadir, Rabat'},
            {'nom': 'Ziani', 'prenom': 'Samira', 'email': 'sziani@email.com', 'telephone': '0660123456', 'adresse': '109 Bd Anfa, Casablanca'},
        ]

        for company in Company.objects.all():
            for client_data in clients_data:
                client, created = Client.objects.get_or_create(
                    company=company,
                    email=client_data['email'],
                    defaults=client_data
                )
                if created:
                    self.clients.append(client)

    def create_purchases(self):
        """Crée les achats"""
        for company in Company.objects.all():
            products = list(Produit.objects.filter(company=company))
            warehouses = list(Warehouse.objects.filter(company=company))

            # Créer 30 achats sur les 3 derniers mois
            for i in range(30):
                date_achat = timezone.now().date() - timedelta(days=random.randint(0, 90))
                product = random.choice(products)

                Achat.objects.get_or_create(
                    company=company,
                    produit=product,
                    date_Achat=date_achat,
                    defaults={
                        'quantite': random.randint(10, 100),
                        'prix_achat': product.prixU * Decimal('0.7'),  # Prix d'achat = 70% du prix de vente
                        'fournisseur': product.fournisseur,
                        'warehouse': random.choice(warehouses) if warehouses else None,
                        'date_expiration': date_achat + timedelta(days=random.randint(180, 730))
                    }
                )

    def create_stocks(self):
        """Crée les stocks dans les entrepôts"""
        for company in Company.objects.all():
            products = Produit.objects.filter(company=company)
            warehouses = Warehouse.objects.filter(company=company)

            for product in products:
                for warehouse in warehouses:
                    # Stock aléatoire entre 0 et la quantité du produit
                    quantity = random.randint(0, product.quantite)

                    ProductStock.objects.get_or_create(
                        produit=product,
                        warehouse=warehouse,
                        defaults={'quantity': quantity}
                    )

    def create_stock_moves(self):
        """Crée des mouvements de stock"""
        for company in Company.objects.all():
            products = list(Produit.objects.filter(company=company))
            warehouses = list(Warehouse.objects.filter(company=company))

            sources = ['ACHAT', 'VENTE', 'INV', 'CORR', 'PERTE', 'TRANS']

            # 50 mouvements aléatoires
            for i in range(50):
                product = random.choice(products)
                warehouse = random.choice(warehouses)
                source = random.choice(sources)

                # Delta positif pour ACHAT, INV, CORR; négatif pour VENTE, PERTE
                if source in ['ACHAT', 'INV', 'CORR']:
                    delta = random.randint(5, 50)
                else:
                    delta = -random.randint(1, 20)

                StockMove.objects.create(
                    produit=product,
                    warehouse=warehouse,
                    delta=delta,
                    source=source,
                    ref_id=f'{source}-{random.randint(1000, 9999)}',
                    date=timezone.now() - timedelta(days=random.randint(0, 60)),
                    note=f'Mouvement {source} pour {product.designation}'
                )

    def create_inventory_sessions(self):
        """Crée des sessions d'inventaire"""
        for company in Company.objects.all():
            products = list(Produit.objects.filter(company=company))
            users = list(User.objects.filter(profile__company=company))

            if not users:
                continue

            # Inventaire validé (terminé)
            inv1 = InventorySession.objects.create(
                company=company,
                numero=f'INV-{timezone.now().strftime("%Y%m")}-001',
                date=timezone.now().date() - timedelta(days=15),
                statut='validated',
                note='Inventaire mensuel',
                created_by=users[0],
                validated_by=users[0]
            )

            # Créer des lignes pour cet inventaire
            for product in products[:20]:  # Les 20 premiers produits
                snapshot_qty = product.quantite
                counted_qty = snapshot_qty + random.randint(-5, 5)  # Petite variance

                InventoryLine.objects.create(
                    session=inv1,
                    produit=product,
                    snapshot_qty=snapshot_qty,
                    counted_qty=counted_qty,
                    counted_by=random.choice(users),
                    counted_at=timezone.now() - timedelta(days=15)
                )

            inv1.update_completion_percentage()

            # Inventaire en cours
            inv2 = InventorySession.objects.create(
                company=company,
                numero=f'INV-{timezone.now().strftime("%Y%m")}-002',
                date=timezone.now().date(),
                statut='in_progress',
                note='Inventaire hebdomadaire',
                created_by=users[0]
            )

            # Quelques lignes comptées, d'autres non
            for i, product in enumerate(products[:15]):
                counted_qty = product.quantite if i < 8 else None  # 8 comptés, 7 non comptés

                InventoryLine.objects.create(
                    session=inv2,
                    produit=product,
                    snapshot_qty=product.quantite,
                    counted_qty=counted_qty,
                    counted_by=random.choice(users) if counted_qty is not None else None
                )

            inv2.update_completion_percentage()

    def create_delivery_notes(self):
        """Crée des bons de livraison"""
        for company in Company.objects.all():
            clients = list(Client.objects.filter(company=company))
            products = list(Produit.objects.filter(company=company))

            if not clients or not products:
                continue

            # 10 bons de livraison
            for i in range(10):
                statut = random.choice(['draft', 'validated', 'validated', 'validated'])  # Plus de validés

                bl = BonLivraison.objects.create(
                    company=company,
                    numero=f'BL-{timezone.now().strftime("%Y%m")}-{i+1:03d}',
                    date_creation=timezone.now().date() - timedelta(days=random.randint(0, 30)),
                    client=random.choice(clients),
                    statut=statut,
                    observations='Livraison standard'
                )

                # 2-5 lignes par bon
                for _ in range(random.randint(2, 5)):
                    product = random.choice(products)

                    LigneLivraison.objects.create(
                        bon=bl,
                        produit=product,
                        quantite=random.randint(1, 10),
                        prixU_snapshot=product.prixU
                    )

    def create_invoices(self):
        """Crée des factures"""
        for company in Company.objects.all():
            bons = list(BonLivraison.objects.filter(company=company, statut='validated'))

            # Créer des factures pour certains bons de livraison
            for i, bon in enumerate(bons[:7]):  # 7 factures
                statut = random.choice(['issued', 'paid', 'paid'])  # Plus de payées

                facture = Facture.objects.create(
                    company=company,
                    numero=f'FA-{timezone.now().strftime("%Y%m")}-{i+1:03d}',
                    date_emission=bon.date_creation,
                    client=bon.client,
                    bon_livraison=bon,
                    statut=statut,
                    tva_rate=Decimal('20.00')
                )

                # Créer les lignes de facture depuis le bon de livraison
                for ligne_bl in bon.lignes.all():
                    LigneFacture.objects.create(
                        facture=facture,
                        produit=ligne_bl.produit,
                        designation=ligne_bl.produit.designation,
                        quantite=ligne_bl.quantite,
                        prixU_snapshot=ligne_bl.prixU_snapshot
                    )

                # Recalculer les totaux
                facture.recompute_totals()
                facture.save()

    def create_sales(self):
        """Crée des ventes"""
        for company in Company.objects.all():
            clients = list(Client.objects.filter(company=company))
            products = list(Produit.objects.filter(company=company))
            warehouses = list(Warehouse.objects.filter(company=company))

            if not clients or not products or not warehouses:
                continue

            # 25 ventes
            for i in range(25):
                statut = random.choice(['completed', 'completed', 'completed', 'draft'])  # Plus de complétées
                type_paiement = random.choice(['cash', 'card', 'card', 'transfer'])

                vente = Vente.objects.create(
                    company=company,
                    numero=f'VEN-{timezone.now().strftime("%Y%m")}-{i+1:03d}',
                    date_vente=timezone.now() - timedelta(days=random.randint(0, 60)),
                    client=random.choice(clients),
                    type_paiement=type_paiement,
                    statut=statut,
                    warehouse=random.choice(warehouses),
                    remise_percent=Decimal(random.choice([0, 0, 0, 5, 10, 15]))  # Certaines avec remise
                )

                # 1-4 lignes par vente
                for _ in range(random.randint(1, 4)):
                    product = random.choice(products)

                    LigneVente.objects.create(
                        vente=vente,
                        produit=product,
                        designation=product.designation,
                        quantite=random.randint(1, 5),
                        prixU_snapshot=product.prixU,
                        currency=product.currency
                    )

                # Recalculer les totaux
                vente.recompute_totals()
                vente.save()

    def create_delivery_drivers(self):
        """Crée des livreurs"""
        self.drivers = []

        drivers_data = [
            {
                'nom': 'Taoufik',
                'prenom': 'Hassan',
                'telephone': '0671234567',
                'email': 'htaoufik@delivery.com',
                'adresse': '23 Rue Ain Sebaa, Casablanca',
                'vehicule_type': 'Camionnette',
                'vehicule_marque': 'Renault Master',
                'immatriculation': '12345-ب-12',
                'capacite_charge': Decimal('1500'),
                'numero_permis': 'MA123456',
            },
            {
                'nom': 'Amrani',
                'prenom': 'Said',
                'telephone': '0672345678',
                'email': 'samrani@delivery.com',
                'adresse': '45 Av Fal Ould Oumeir, Casablanca',
                'vehicule_type': 'Camion',
                'vehicule_marque': 'Mercedes Sprinter',
                'immatriculation': '67890-ب-34',
                'capacite_charge': Decimal('3500'),
                'numero_permis': 'MA234567',
            },
            {
                'nom': 'Rami',
                'prenom': 'Karim',
                'telephone': '0673456789',
                'email': 'krami@delivery.com',
                'adresse': '67 Bd Brahim Roudani, Casablanca',
                'vehicule_type': 'Van',
                'vehicule_marque': 'Peugeot Expert',
                'immatriculation': '11223-ب-56',
                'capacite_charge': Decimal('1200'),
                'numero_permis': 'MA345678',
            }
        ]

        for company in Company.objects.all():
            for driver_data in drivers_data:
                driver, created = Livreur.objects.get_or_create(
                    company=company,
                    telephone=driver_data['telephone'],
                    defaults={
                        **driver_data,
                        'date_expiration_permis': timezone.now().date() + timedelta(days=random.randint(180, 1095))
                    }
                )
                if created:
                    self.drivers.append(driver)

    def create_delivery_tours(self):
        """Crée des tournées de livraison"""
        for company in Company.objects.all():
            drivers = list(Livreur.objects.filter(company=company))
            warehouses = list(Warehouse.objects.filter(company=company, code__contains='WH'))  # Entrepôts principaux
            clients = list(Client.objects.filter(company=company))
            bons = list(BonLivraison.objects.filter(company=company, statut='validated'))

            if not drivers or not warehouses or not clients:
                continue

            # 5 tournées
            for i in range(5):
                statut = random.choice(['planifiee', 'en_cours', 'terminee', 'terminee'])
                date_tournee = timezone.now().date() - timedelta(days=random.randint(0, 14))

                tournee = Tournee.objects.create(
                    company=company,
                    numero=f'TOUR-{date_tournee.strftime("%Y%m%d")}-{i+1:03d}',
                    date=date_tournee,
                    livreur=random.choice(drivers),
                    warehouse=random.choice(warehouses),
                    heure_depart_prevue=time(8, 0),
                    heure_depart_reelle=time(8, 15) if statut != 'planifiee' else None,
                    heure_retour_prevue=time(17, 0),
                    heure_retour_reelle=time(16, 45) if statut == 'terminee' else None,
                    statut=statut,
                    distance_km=Decimal(random.randint(50, 150)),
                    commentaire='Tournée standard'
                )

                # 3-6 arrêts par tournée
                nb_arrets = random.randint(3, 6)
                for ordre in range(1, nb_arrets + 1):
                    client = random.choice(clients)
                    bon = random.choice(bons) if bons else None

                    statut_arret = 'en_attente'
                    if tournee.statut == 'terminee':
                        statut_arret = random.choice(['livre', 'livre', 'livre', 'echec'])  # Majorité livrés
                    elif tournee.statut == 'en_cours':
                        if ordre <= nb_arrets // 2:
                            statut_arret = 'livre'
                        else:
                            statut_arret = 'en_cours' if ordre == (nb_arrets // 2) + 1 else 'en_attente'

                    heure_prevue = time(9 + ordre, 0)

                    ArretLivraison.objects.create(
                        company=company,
                        tournee=tournee,
                        bon_livraison=bon,
                        client=client,
                        ordre=ordre,
                        heure_prevue=heure_prevue,
                        heure_arrivee=time(9 + ordre, random.randint(0, 30)) if statut_arret in ['livre', 'echec'] else None,
                        heure_depart=time(9 + ordre, random.randint(35, 55)) if statut_arret in ['livre', 'echec'] else None,
                        adresse_livraison=client.adresse,
                        statut=statut_arret,
                        nom_recepteur=f'{client.prenom} {client.nom}' if statut_arret == 'livre' else '',
                        commentaire='Livraison effectuée sans problème' if statut_arret == 'livre' else '',
                        raison_echec='Client absent' if statut_arret == 'echec' else ''
                    )

    def create_stock_transfers(self):
        """Crée des transferts de stock"""
        for company in Company.objects.all():
            warehouses = list(Warehouse.objects.filter(company=company))
            products = list(Produit.objects.filter(company=company))
            users = list(User.objects.filter(profile__company=company))

            if len(warehouses) < 2 or not products or not users:
                continue

            # 8 transferts
            for i in range(8):
                # Séparer les entrepôts principaux et les vans
                entrepots_principaux = [w for w in warehouses if 'WH' in w.code]
                vans = [w for w in warehouses if 'VAN' in w.code]

                # Choisir aléatoirement le type de transfert
                if vans and entrepots_principaux:
                    if random.choice([True, False]):
                        # Transfert vers van
                        source = random.choice(entrepots_principaux)
                        destination = random.choice(vans)
                    else:
                        # Transfert entre entrepôts
                        source, destination = random.sample(entrepots_principaux, 2)
                else:
                    source, destination = random.sample(warehouses, 2)

                statut = random.choice(['valide', 'valide', 'receptionne', 'brouillon'])

                transfert = TransfertStock.objects.create(
                    company=company,
                    entrepot_source=source,
                    entrepot_destination=destination,
                    statut=statut,
                    demandeur=users[0],
                    valideur=users[0] if statut != 'brouillon' else None,
                    recepteur=users[0] if statut == 'receptionne' else None,
                    date_validation=timezone.now() if statut != 'brouillon' else None,
                    date_reception=timezone.now() if statut == 'receptionne' else None,
                    notes=f'Transfert {source.code} → {destination.code}'
                )

                # 2-5 lignes par transfert
                selected_products = random.sample(products, min(random.randint(2, 5), len(products)))
                for product in selected_products:
                    quantite = random.randint(5, 20)

                    LigneTransfertStock.objects.create(
                        transfert=transfert,
                        produit=product,
                        quantite=quantite,
                        quantite_recue=quantite if statut == 'receptionne' else None
                    )

    def print_summary(self):
        """Affiche un résumé des données créées"""
        self.stdout.write(self.style.SUCCESS('\n=== RÉSUMÉ DES DONNÉES GÉNÉRÉES ===\n'))

        models_stats = [
            ('Entreprises', Company),
            ('Utilisateurs', User),
            ('Devises', Currency),
            ('Taux de change', ExchangeRate),
            ('Entrepôts', Warehouse),
            ('Fournisseurs', Fournisseur),
            ('Catégories', Categorie),
            ('Types de prix', TypePrix),
            ('Produits', Produit),
            ('Prix produits', PrixProduit),
            ('Clients', Client),
            ('Achats', Achat),
            ('Stocks', ProductStock),
            ('Mouvements de stock', StockMove),
            ('Sessions d\'inventaire', InventorySession),
            ('Lignes d\'inventaire', InventoryLine),
            ('Bons de livraison', BonLivraison),
            ('Lignes de livraison', LigneLivraison),
            ('Factures', Facture),
            ('Lignes de facture', LigneFacture),
            ('Ventes', Vente),
            ('Lignes de vente', LigneVente),
            ('Livreurs', Livreur),
            ('Tournées', Tournee),
            ('Arrêts de livraison', ArretLivraison),
            ('Transferts de stock', TransfertStock),
            ('Lignes de transfert', LigneTransfertStock),
        ]

        for name, model in models_stats:
            count = model.objects.count()
            self.stdout.write(f'  {name}: {count}')

        self.stdout.write(self.style.SUCCESS('\n=== ACCÈS AU SYSTÈME ===\n'))

        for company in Company.objects.all():
            self.stdout.write(f'\nEntreprise: {company.name} ({company.code})')
            users = UserProfile.objects.filter(company=company)
            for profile in users:
                self.stdout.write(f'  - {profile.user.username} ({profile.get_role_display()}): password123')

        self.stdout.write(self.style.SUCCESS('\n=== FONCTIONNALITÉS COUVERTES ===\n'))
        features = [
            '✓ Multi-tenancy (entreprises)',
            '✓ Gestion des devises et taux de change',
            '✓ Gestion des entrepôts (incluant vans de livraison)',
            '✓ Catégories de produits hiérarchiques',
            '✓ Produits avec alertes de stock',
            '✓ Prix multiples par produit (détaillant, grossiste, promo, VIP)',
            '✓ Gestion des fournisseurs',
            '✓ Gestion des clients',
            '✓ Achats avec traçabilité',
            '✓ Stocks multi-entrepôts',
            '✓ Mouvements de stock',
            '✓ Inventaires (avec sessions en cours et validées)',
            '✓ Bons de livraison',
            '✓ Factures clients',
            '✓ Ventes avec remises',
            '✓ Livreurs et véhicules',
            '✓ Tournées de livraison',
            '✓ Arrêts de livraison avec statuts',
            '✓ Transferts de stock entre entrepôts',
            '✓ Configuration système',
        ]

        for feature in features:
            self.stdout.write(f'  {feature}')
