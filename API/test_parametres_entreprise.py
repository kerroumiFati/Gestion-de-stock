"""Paramètres par entreprise (0094) : avec une seule entreprise, les comptes du bureau sans
entreprise, les téléphones et les commandes de clients sans entreprise partagent les MÊMES
réglages. Affectation d'une commande : le dépôt source est toujours choisi par l'utilisateur."""
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

    def test_affectation_jamais_de_depot_automatique(self):
        """Le dépôt source est toujours choisi par l'utilisateur : sans choix, l'affectation est
        refusée (avant : dépôt des paramètres, puis n'importe quel dépôt actif)."""
        from .models import UserProfile
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
        adv = User.objects.create_user('adv1', password='x', is_staff=True)
        UserProfile.objects.update_or_create(user=adv, defaults={'company': self.societe})
        api = APIClient()
        api.force_authenticate(adv)
        url = f'/API/distribution/commandes/{cmd.id}/affecter_livreur/'

        r = api.post(url, {'livreur_id': livreur.id}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("Choisissez l'entrepôt source", r.json()['error'])
        cmd.refresh_from_db()
        self.assertEqual(cmd.livreur_id, prevendeur.id)                     # rien d'affecté
        self.assertEqual(ProductStock.objects.get(produit=p, warehouse=self.depot).quantity, 50)

        # Dépôt d'une autre entreprise : introuvable
        autre = Company.objects.create(name='Autre', code='AUT')
        depot_autre = Warehouse.objects.create(name='Dépôt autre', code='X1', company=autre)
        ProductStock.objects.create(produit=p, warehouse=depot_autre, quantity=50)
        r = api.post(url, {'livreur_id': livreur.id, 'entrepot_source_id': depot_autre.id}, format='json')
        self.assertEqual(r.status_code, 404, r.content)
        self.assertEqual(ProductStock.objects.get(produit=p, warehouse=depot_autre).quantity, 50)

        # Livreur d'une autre entreprise : introuvable
        van_autre = Warehouse.objects.create(name='Van autre', code='VAN-X', company=autre)
        livreur_autre = LivreurDistribution.objects.create(matricule='LX', nom='Autre', telephone='0',
                                                           entrepot=van_autre)
        r = api.post(url, {'livreur_id': livreur_autre.id, 'entrepot_source_id': self.depot.id}, format='json')
        self.assertEqual(r.status_code, 404, r.content)

        # Dépôt choisi par l'utilisateur : le stock part de CE dépôt
        r = api.post(url, {'livreur_id': livreur.id, 'entrepot_source_id': self.depot_a.id}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(ProductStock.objects.get(produit=p, warehouse=self.depot_a).quantity, 45)
        self.assertEqual(ProductStock.objects.get(produit=p, warehouse=self.depot).quantity, 50)
