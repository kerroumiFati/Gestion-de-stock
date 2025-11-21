#!/usr/bin/env python
"""
Script de test complet pour vérifier toutes les opérations CRUD du système
"""
import os
import sys
import django
from datetime import datetime, date, time, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.contrib.auth.models import User
from API.models import (
    Company, UserProfile, Currency, ExchangeRate,
    Fournisseur, Categorie, Produit, Client, Achat,
    BonLivraison, LigneLivraison, Facture, LigneFacture,
    Warehouse, ProductStock, StockMove, InventorySession, InventoryLine,
    Vente, LigneVente, Livreur, Tournee, ArretLivraison,
    TransfertStock, LigneTransfertStock, TypePrix, PrixProduit
)

# Couleurs pour l'affichage
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")

def print_result(module_name, results):
    """Affiche les résultats pour un module"""
    total = sum(results.values())
    success = results.get('success', 0)

    print(f"\n{Colors.BOLD}Résumé pour {module_name}:{Colors.RESET}")
    print(f"  Création (Create): {'✓' if results.get('create') else '✗'}")
    print(f"  Lecture (Read): {'✓' if results.get('read') else '✗'}")
    print(f"  Modification (Update): {'✓' if results.get('update') else '✗'}")
    print(f"  Suppression (Delete): {'✗ Désactivé' if results.get('skip_delete') else ('✓' if results.get('delete') else '✗')}")
    print(f"  Résultat: {success}/{total} tests réussis")

    return success == total


class CRUDTester:
    def __init__(self):
        self.results = {}
        self.test_objects = {}
        self.user = None
        self.company = None

    def setup(self):
        """Initialisation des données de base"""
        print_header("INITIALISATION DES DONNÉES DE BASE")

        # Créer un utilisateur de test
        try:
            self.user, created = User.objects.get_or_create(
                username='test_admin',
                defaults={
                    'email': 'test@example.com',
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            if created:
                self.user.set_password('test123')
                self.user.save()
            print_success(f"Utilisateur de test: {self.user.username}")
        except Exception as e:
            print_error(f"Erreur création utilisateur: {e}")

        # Créer une entreprise de test
        try:
            self.company, created = Company.objects.get_or_create(
                code='TEST-COMP',
                defaults={
                    'name': 'Entreprise Test CRUD',
                    'email': 'test@company.com',
                    'telephone': '0123456789',
                    'is_active': True
                }
            )
            print_success(f"Entreprise de test: {self.company.name}")

            # Créer le profil utilisateur
            profile, _ = UserProfile.objects.get_or_create(
                user=self.user,
                defaults={
                    'company': self.company,
                    'role': 'admin'
                }
            )
            print_success(f"Profil utilisateur créé: {profile.role}")

        except Exception as e:
            print_error(f"Erreur création entreprise: {e}")

        # Créer une devise par défaut
        try:
            currency, created = Currency.objects.get_or_create(
                code='EUR',
                defaults={
                    'name': 'Euro',
                    'symbol': '€',
                    'is_default': True,
                    'is_active': True
                }
            )
            self.test_objects['currency'] = currency
            print_success(f"Devise par défaut: {currency.code}")
        except Exception as e:
            print_error(f"Erreur création devise: {e}")

    def test_company_crud(self):
        """Test CRUD pour Company"""
        print_header("TEST CRUD: ENTREPRISES (COMPANIES)")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # CREATE
            company = Company.objects.create(
                code='TEST-NEW',
                name='Nouvelle Entreprise Test',
                email='new@test.com',
                telephone='9876543210',
                is_active=True
            )
            print_success(f"CREATE: Entreprise créée - {company.name}")
            results['create'] = 1
            results['success'] += 1

            # READ
            company_read = Company.objects.get(code='TEST-NEW')
            assert company_read.name == 'Nouvelle Entreprise Test'
            print_success(f"READ: Entreprise lue - {company_read.name}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            company_read.name = 'Entreprise Modifiée'
            company_read.save()
            company_updated = Company.objects.get(code='TEST-NEW')
            assert company_updated.name == 'Entreprise Modifiée'
            print_success(f"UPDATE: Entreprise modifiée - {company_updated.name}")
            results['update'] = 1
            results['success'] += 1

            # DELETE (désactivation au lieu de suppression)
            company_updated.is_active = False
            company_updated.save()
            print_success(f"DELETE: Entreprise désactivée")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['company'] = company

        except Exception as e:
            print_error(f"Erreur test Company: {e}")

        self.results['Company'] = results
        return print_result('Company', results)

    def test_categorie_crud(self):
        """Test CRUD pour Categorie"""
        print_header("TEST CRUD: CATÉGORIES")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # CREATE
            categorie = Categorie.objects.create(
                company=self.company,
                nom='Électronique Test',
                description='Catégorie test pour électronique',
                couleur='#3B82F6',
                icone='fa-laptop',
                is_active=True
            )
            print_success(f"CREATE: Catégorie créée - {categorie.nom}")
            results['create'] = 1
            results['success'] += 1

            # READ
            cat_read = Categorie.objects.get(id=categorie.id)
            assert cat_read.nom == 'Électronique Test'
            print_success(f"READ: Catégorie lue - {cat_read.nom}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            cat_read.description = 'Description modifiée'
            cat_read.save()
            cat_updated = Categorie.objects.get(id=categorie.id)
            assert cat_updated.description == 'Description modifiée'
            print_success(f"UPDATE: Catégorie modifiée")
            results['update'] = 1
            results['success'] += 1

            # DELETE (désactivation)
            cat_updated.is_active = False
            cat_updated.save()
            print_success(f"DELETE: Catégorie désactivée")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['categorie'] = categorie

        except Exception as e:
            print_error(f"Erreur test Categorie: {e}")

        self.results['Categorie'] = results
        return print_result('Catégorie', results)

    def test_fournisseur_crud(self):
        """Test CRUD pour Fournisseur"""
        print_header("TEST CRUD: FOURNISSEURS")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0, 'skip_delete': True}

        try:
            # CREATE
            fournisseur = Fournisseur.objects.create(
                company=self.company,
                libelle='Fournisseur Test SARL',
                telephone='0600000001',
                email='fournisseur@test.com',
                adresse='123 Rue Test'
            )
            print_success(f"CREATE: Fournisseur créé - {fournisseur.libelle}")
            results['create'] = 1
            results['success'] += 1

            # READ
            fourn_read = Fournisseur.objects.get(id=fournisseur.id)
            assert fourn_read.libelle == 'Fournisseur Test SARL'
            print_success(f"READ: Fournisseur lu - {fourn_read.libelle}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            fourn_read.email = 'nouveau@fournisseur.com'
            fourn_read.save()
            fourn_updated = Fournisseur.objects.get(id=fournisseur.id)
            assert fourn_updated.email == 'nouveau@fournisseur.com'
            print_success(f"UPDATE: Fournisseur modifié")
            results['update'] = 1
            results['success'] += 1

            # DELETE - Skip car utilisé dans d'autres objets
            print_info("DELETE: Suppression ignorée (utilisé par d'autres objets)")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['fournisseur'] = fournisseur

        except Exception as e:
            print_error(f"Erreur test Fournisseur: {e}")

        self.results['Fournisseur'] = results
        return print_result('Fournisseur', results)

    def test_warehouse_crud(self):
        """Test CRUD pour Warehouse"""
        print_header("TEST CRUD: ENTREPÔTS (WAREHOUSES)")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # CREATE
            warehouse = Warehouse.objects.create(
                company=self.company,
                code='WH-TEST',
                name='Entrepôt Test',
                is_active=True
            )
            print_success(f"CREATE: Entrepôt créé - {warehouse.name}")
            results['create'] = 1
            results['success'] += 1

            # READ
            wh_read = Warehouse.objects.get(id=warehouse.id)
            assert wh_read.code == 'WH-TEST'
            print_success(f"READ: Entrepôt lu - {wh_read.name}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            wh_read.name = 'Entrepôt Modifié'
            wh_read.save()
            wh_updated = Warehouse.objects.get(id=warehouse.id)
            assert wh_updated.name == 'Entrepôt Modifié'
            print_success(f"UPDATE: Entrepôt modifié")
            results['update'] = 1
            results['success'] += 1

            # DELETE (désactivation)
            wh_updated.is_active = False
            wh_updated.save()
            print_success(f"DELETE: Entrepôt désactivé")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['warehouse'] = warehouse

        except Exception as e:
            print_error(f"Erreur test Warehouse: {e}")

        self.results['Warehouse'] = results
        return print_result('Warehouse', results)

    def test_produit_crud(self):
        """Test CRUD pour Produit"""
        print_header("TEST CRUD: PRODUITS")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # Créer une catégorie active pour le test
            cat = Categorie.objects.filter(company=self.company, is_active=True).first()
            if not cat:
                cat = self.test_objects.get('categorie')
                if cat:
                    cat.is_active = True
                    cat.save()

            # CREATE
            produit = Produit.objects.create(
                company=self.company,
                reference='PROD-TEST-001',
                code_barre='1234567890123',
                designation='Produit Test',
                description='Description du produit test',
                categorie=cat,
                prixU=Decimal('99.99'),
                currency=self.test_objects.get('currency'),
                quantite=100,
                seuil_alerte=20,
                seuil_critique=5,
                unite_mesure='piece',
                fournisseur=self.test_objects.get('fournisseur'),
                is_active=True
            )
            print_success(f"CREATE: Produit créé - {produit.designation}")
            results['create'] = 1
            results['success'] += 1

            # READ
            prod_read = Produit.objects.get(id=produit.id)
            assert prod_read.reference == 'PROD-TEST-001'
            print_success(f"READ: Produit lu - {prod_read.designation}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            prod_read.prixU = Decimal('149.99')
            prod_read.save()
            prod_updated = Produit.objects.get(id=produit.id)
            assert prod_updated.prixU == Decimal('149.99')
            print_success(f"UPDATE: Produit modifié - nouveau prix: {prod_updated.prixU}")
            results['update'] = 1
            results['success'] += 1

            # DELETE (désactivation)
            prod_updated.is_active = False
            prod_updated.save()
            print_success(f"DELETE: Produit désactivé")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['produit'] = produit

        except Exception as e:
            print_error(f"Erreur test Produit: {e}")
            import traceback
            traceback.print_exc()

        self.results['Produit'] = results
        return print_result('Produit', results)

    def test_client_crud(self):
        """Test CRUD pour Client"""
        print_header("TEST CRUD: CLIENTS")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0, 'skip_delete': True}

        try:
            # CREATE
            client = Client.objects.create(
                company=self.company,
                nom='Dupont',
                prenom='Jean',
                email='jean.dupont@test.com',
                telephone='0601020304',
                adresse='456 Avenue Test',
                lat=Decimal('48.8566'),
                lng=Decimal('2.3522')
            )
            print_success(f"CREATE: Client créé - {client.nom} {client.prenom}")
            results['create'] = 1
            results['success'] += 1

            # READ
            client_read = Client.objects.get(id=client.id)
            assert client_read.email == 'jean.dupont@test.com'
            print_success(f"READ: Client lu - {client_read.nom} {client_read.prenom}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            client_read.telephone = '0609080706'
            client_read.save()
            client_updated = Client.objects.get(id=client.id)
            assert client_updated.telephone == '0609080706'
            print_success(f"UPDATE: Client modifié - nouveau tél: {client_updated.telephone}")
            results['update'] = 1
            results['success'] += 1

            # DELETE - Skip
            print_info("DELETE: Suppression ignorée (utilisé par d'autres objets)")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['client'] = client

        except Exception as e:
            print_error(f"Erreur test Client: {e}")

        self.results['Client'] = results
        return print_result('Client', results)

    def test_achat_crud(self):
        """Test CRUD pour Achat"""
        print_header("TEST CRUD: ACHATS")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0, 'skip_delete': True}

        try:
            # Réactiver le produit si nécessaire
            produit = self.test_objects.get('produit')
            if produit and not produit.is_active:
                produit.is_active = True
                produit.save()

            # CREATE
            achat = Achat.objects.create(
                company=self.company,
                date_Achat=date.today(),
                quantite=50,
                prix_achat=Decimal('75.00'),
                fournisseur=self.test_objects.get('fournisseur'),
                produit=produit,
                warehouse=self.test_objects.get('warehouse')
            )
            print_success(f"CREATE: Achat créé - {achat.quantite} unités")
            results['create'] = 1
            results['success'] += 1

            # READ
            achat_read = Achat.objects.get(id=achat.id)
            assert achat_read.quantite == 50
            print_success(f"READ: Achat lu - {achat_read.quantite} unités")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            achat_read.quantite = 60
            achat_read.save()
            achat_updated = Achat.objects.get(id=achat.id)
            assert achat_updated.quantite == 60
            print_success(f"UPDATE: Achat modifié - nouvelle quantité: {achat_updated.quantite}")
            results['update'] = 1
            results['success'] += 1

            # DELETE - Skip
            print_info("DELETE: Suppression ignorée (conserve l'historique)")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['achat'] = achat

        except Exception as e:
            print_error(f"Erreur test Achat: {e}")

        self.results['Achat'] = results
        return print_result('Achat', results)

    def test_vente_crud(self):
        """Test CRUD pour Vente"""
        print_header("TEST CRUD: VENTES")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # CREATE
            vente = Vente.objects.create(
                company=self.company,
                numero='VTE-TEST-001',
                date_vente=datetime.now(),
                client=self.test_objects.get('client'),
                type_paiement='cash',
                statut='draft',
                warehouse=self.test_objects.get('warehouse'),
                currency=self.test_objects.get('currency'),
                total_ht=Decimal('100.00'),
                total_ttc=Decimal('100.00')
            )
            print_success(f"CREATE: Vente créée - {vente.numero}")
            results['create'] = 1
            results['success'] += 1

            # READ
            vente_read = Vente.objects.get(id=vente.id)
            assert vente_read.numero == 'VTE-TEST-001'
            print_success(f"READ: Vente lue - {vente_read.numero}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            vente_read.statut = 'completed'
            vente_read.save()
            vente_updated = Vente.objects.get(id=vente.id)
            assert vente_updated.statut == 'completed'
            print_success(f"UPDATE: Vente modifiée - statut: {vente_updated.statut}")
            results['update'] = 1
            results['success'] += 1

            # DELETE (changement de statut)
            vente_updated.statut = 'canceled'
            vente_updated.save()
            print_success(f"DELETE: Vente annulée")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['vente'] = vente

        except Exception as e:
            print_error(f"Erreur test Vente: {e}")
            import traceback
            traceback.print_exc()

        self.results['Vente'] = results
        return print_result('Vente', results)

    def test_inventaire_crud(self):
        """Test CRUD pour InventorySession"""
        print_header("TEST CRUD: INVENTAIRES")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # CREATE
            inventaire = InventorySession.objects.create(
                company=self.company,
                numero='INV-TEST-001',
                date=date.today(),
                statut='draft',
                note='Inventaire de test',
                created_by=self.user
            )
            print_success(f"CREATE: Inventaire créé - {inventaire.numero}")
            results['create'] = 1
            results['success'] += 1

            # READ
            inv_read = InventorySession.objects.get(id=inventaire.id)
            assert inv_read.numero == 'INV-TEST-001'
            print_success(f"READ: Inventaire lu - {inv_read.numero}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            inv_read.statut = 'in_progress'
            inv_read.save()
            inv_updated = InventorySession.objects.get(id=inventaire.id)
            assert inv_updated.statut == 'in_progress'
            print_success(f"UPDATE: Inventaire modifié - statut: {inv_updated.statut}")
            results['update'] = 1
            results['success'] += 1

            # DELETE (annulation)
            inv_updated.statut = 'canceled'
            inv_updated.save()
            print_success(f"DELETE: Inventaire annulé")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['inventaire'] = inventaire

        except Exception as e:
            print_error(f"Erreur test Inventaire: {e}")

        self.results['Inventaire'] = results
        return print_result('Inventaire', results)

    def test_livreur_crud(self):
        """Test CRUD pour Livreur"""
        print_header("TEST CRUD: LIVREURS")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # CREATE
            livreur = Livreur.objects.create(
                company=self.company,
                nom='Martin',
                prenom='Pierre',
                telephone='0605040302',
                email='pierre.martin@test.com',
                vehicule_type='Camionnette',
                immatriculation='AB-123-CD',
                is_active=True,
                is_disponible=True
            )
            print_success(f"CREATE: Livreur créé - {livreur.nom} {livreur.prenom}")
            results['create'] = 1
            results['success'] += 1

            # READ
            liv_read = Livreur.objects.get(id=livreur.id)
            assert liv_read.telephone == '0605040302'
            print_success(f"READ: Livreur lu - {liv_read.get_full_name()}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            liv_read.is_disponible = False
            liv_read.save()
            liv_updated = Livreur.objects.get(id=livreur.id)
            assert liv_updated.is_disponible == False
            print_success(f"UPDATE: Livreur modifié - disponibilité: {liv_updated.is_disponible}")
            results['update'] = 1
            results['success'] += 1

            # DELETE (désactivation)
            liv_updated.is_active = False
            liv_updated.save()
            print_success(f"DELETE: Livreur désactivé")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['livreur'] = livreur

        except Exception as e:
            print_error(f"Erreur test Livreur: {e}")

        self.results['Livreur'] = results
        return print_result('Livreur', results)

    def test_tournee_crud(self):
        """Test CRUD pour Tournee"""
        print_header("TEST CRUD: TOURNÉES")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # Réactiver le livreur et le warehouse
            livreur = self.test_objects.get('livreur')
            if livreur:
                livreur.is_active = True
                livreur.save()

            warehouse = self.test_objects.get('warehouse')
            if warehouse:
                warehouse.is_active = True
                warehouse.save()

            # CREATE
            tournee = Tournee.objects.create(
                company=self.company,
                numero=f'TOUR-TEST-{datetime.now().strftime("%Y%m%d")}-001',
                date=date.today(),
                livreur=livreur,
                warehouse=warehouse,
                heure_depart_prevue=time(8, 0),
                statut='planifiee'
            )
            print_success(f"CREATE: Tournée créée - {tournee.numero}")
            results['create'] = 1
            results['success'] += 1

            # READ
            tour_read = Tournee.objects.get(id=tournee.id)
            assert tour_read.statut == 'planifiee'
            print_success(f"READ: Tournée lue - {tour_read.numero}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            tour_read.statut = 'en_cours'
            tour_read.heure_depart_reelle = time(8, 15)
            tour_read.save()
            tour_updated = Tournee.objects.get(id=tournee.id)
            assert tour_updated.statut == 'en_cours'
            print_success(f"UPDATE: Tournée modifiée - statut: {tour_updated.statut}")
            results['update'] = 1
            results['success'] += 1

            # DELETE (annulation)
            tour_updated.statut = 'annulee'
            tour_updated.save()
            print_success(f"DELETE: Tournée annulée")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['tournee'] = tournee

        except Exception as e:
            print_error(f"Erreur test Tournée: {e}")
            import traceback
            traceback.print_exc()

        self.results['Tournee'] = results
        return print_result('Tournée', results)

    def test_transfert_crud(self):
        """Test CRUD pour TransfertStock"""
        print_header("TEST CRUD: TRANSFERTS DE STOCK")
        results = {'create': 0, 'read': 0, 'update': 0, 'delete': 0, 'success': 0}

        try:
            # Créer un deuxième entrepôt pour le transfert
            warehouse2 = Warehouse.objects.create(
                company=self.company,
                code='WH-DEST',
                name='Entrepôt Destination',
                is_active=True
            )

            # CREATE
            transfert = TransfertStock.objects.create(
                company=self.company,
                entrepot_source=self.test_objects.get('warehouse'),
                entrepot_destination=warehouse2,
                statut='brouillon',
                demandeur=self.user,
                notes='Transfert de test'
            )
            print_success(f"CREATE: Transfert créé - {transfert.numero}")
            results['create'] = 1
            results['success'] += 1

            # READ
            trans_read = TransfertStock.objects.get(id=transfert.id)
            assert trans_read.statut == 'brouillon'
            print_success(f"READ: Transfert lu - {trans_read.numero}")
            results['read'] = 1
            results['success'] += 1

            # UPDATE
            trans_read.notes = 'Notes modifiées'
            trans_read.save()
            trans_updated = TransfertStock.objects.get(id=transfert.id)
            assert trans_updated.notes == 'Notes modifiées'
            print_success(f"UPDATE: Transfert modifié")
            results['update'] = 1
            results['success'] += 1

            # DELETE (annulation)
            trans_updated.statut = 'annule'
            trans_updated.motif_annulation = 'Test terminé'
            trans_updated.save()
            print_success(f"DELETE: Transfert annulé")
            results['delete'] = 1
            results['success'] += 1

            self.test_objects['transfert'] = transfert

        except Exception as e:
            print_error(f"Erreur test Transfert: {e}")
            import traceback
            traceback.print_exc()

        self.results['Transfert'] = results
        return print_result('Transfert de Stock', results)

    def run_all_tests(self):
        """Exécuter tous les tests"""
        print_header("DÉMARRAGE DES TESTS CRUD COMPLETS")
        print_info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.setup()

        # Liste des tests à exécuter
        tests = [
            ('Company', self.test_company_crud),
            ('Catégorie', self.test_categorie_crud),
            ('Fournisseur', self.test_fournisseur_crud),
            ('Warehouse', self.test_warehouse_crud),
            ('Produit', self.test_produit_crud),
            ('Client', self.test_client_crud),
            ('Achat', self.test_achat_crud),
            ('Vente', self.test_vente_crud),
            ('Inventaire', self.test_inventaire_crud),
            ('Livreur', self.test_livreur_crud),
            ('Tournée', self.test_tournee_crud),
            ('Transfert', self.test_transfert_crud),
        ]

        passed_tests = []
        failed_tests = []

        for test_name, test_func in tests:
            try:
                success = test_func()
                if success:
                    passed_tests.append(test_name)
                else:
                    failed_tests.append(test_name)
            except Exception as e:
                print_error(f"Erreur lors du test {test_name}: {e}")
                failed_tests.append(test_name)

        # Résumé final
        self.print_final_summary(passed_tests, failed_tests)

    def print_final_summary(self, passed, failed):
        """Afficher le résumé final"""
        print_header("RÉSUMÉ FINAL DES TESTS")

        total = len(passed) + len(failed)
        success_rate = (len(passed) / total * 100) if total > 0 else 0

        print(f"\n{Colors.BOLD}Tests réussis: {Colors.GREEN}{len(passed)}/{total}{Colors.RESET}")
        for test in passed:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {test}")

        if failed:
            print(f"\n{Colors.BOLD}Tests échoués: {Colors.RED}{len(failed)}/{total}{Colors.RESET}")
            for test in failed:
                print(f"  {Colors.RED}✗{Colors.RESET} {test}")

        print(f"\n{Colors.BOLD}Taux de réussite: ", end='')
        if success_rate == 100:
            print(f"{Colors.GREEN}{success_rate:.1f}%{Colors.RESET}")
        elif success_rate >= 80:
            print(f"{Colors.YELLOW}{success_rate:.1f}%{Colors.RESET}")
        else:
            print(f"{Colors.RED}{success_rate:.1f}%{Colors.RESET}")

        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


if __name__ == '__main__':
    tester = CRUDTester()
    tester.run_all_tests()
