"""Paramètres par entreprise (0094) : avec une seule entreprise, les comptes du bureau sans
entreprise, les téléphones et les commandes de clients sans entreprise partagent les MÊMES
réglages ; le dépôt des commandes mobiles reste celui choisi dans les Paramètres."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Company, Produit, ProductStock, SystemConfig, Warehouse
from .distribution_models import CommandeClient, LigneCommandeClient, LivreurDistribution


class ParametresEntrepriseTests(TestCase):
    def setUp(self):
        self.societe = Company.objects.create(name='RayanneDist', code='RAYAN01')
        self.depot_a = Warehouse.objects.create(name='Autre dépôt', code='A1', company=self.societe)
        self.depot = Warehouse.objects.create(name='Dar El Beida', code='123456', company=self.societe)
        self.van = Warehouse.objects.create(name='Van', code='VAN-0001', company=self.societe)
        cfg = SystemConfig.get_solo(self.societe)
        cfg.depot_commandes_mobile = self.depot
        cfg.save()

    def test_sans_entreprise_lit_les_parametres_de_l_unique_entreprise(self):
        self.assertEqual(SystemConfig.get_solo(None).pk, SystemConfig.get_solo(self.societe).pk)
        self.assertEqual(SystemConfig.get_solo().depot_commandes_mobile, self.depot)

    def test_plusieurs_entreprises_sans_entreprise_reste_separe(self):
        autre = Company.objects.create(name='Autre', code='AUT')
        self.assertIsNone(SystemConfig.get_solo(None).company)
        self.assertNotEqual(SystemConfig.get_solo(None).pk, SystemConfig.get_solo(autre).pk)

    def test_commande_client_sans_entreprise_part_du_depot_des_parametres(self):
        cat = Categorie.objects.create(nom='Fromages')
        p = Produit.objects.create(reference='CH', code_barre='9', designation='Cheddar',
                                   prixU=Decimal('100'), categorie=cat)
        ProductStock.objects.create(produit=p, warehouse=self.depot_a, quantity=50)
        ProductStock.objects.create(produit=p, warehouse=self.depot, quantity=50)
        livreur = LivreurDistribution.objects.create(matricule='L1', nom='Amer', telephone='0',
                                                     user=User.objects.create_user('amer', password='x'),
                                                     entrepot=self.van)
        client = Client.objects.create(nom='Sans', prenom='Entreprise', telephone='0')   # pas d'entreprise
        prevendeur = LivreurDistribution.objects.create(matricule='P1', nom='Yacine', telephone='0')
        cmd = CommandeClient.objects.create(client=client, livreur=prevendeur, reference='CMD-9')
        LigneCommandeClient.objects.create(commande=cmd, produit=p, quantite=5,
                                           prix_unitaire_ht=Decimal('100'), taux_tva=0)
        api = APIClient()
        api.force_authenticate(User.objects.create_user('adv1', password='x', is_staff=True))
        r = api.post(f'/API/distribution/commandes/{cmd.id}/affecter_livreur/',
                     {'livreur_id': livreur.id}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(ProductStock.objects.get(produit=p, warehouse=self.depot).quantity, 45)
        self.assertEqual(ProductStock.objects.get(produit=p, warehouse=self.depot_a).quantity, 50)
