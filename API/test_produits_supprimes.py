"""Tests de la corbeille des produits supprimés (désactivés)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

import json

from .models import (AuditLog, Categorie, Conditionnement, PrixProduit, ProductStock,
                     Produit, StockMove, Warehouse)


class ProduitsSupprimesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin_ps', password='x', is_staff=True, is_superuser=True)
        self.user = User.objects.create_user('simple_ps', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        cat = Categorie.objects.create(nom='Cat PS')
        self.libre = Produit.objects.create(reference='LIBRE', code_barre='1', designation='Libre',
                                            categorie=cat, prixU=Decimal('10'), is_active=False)
        Conditionnement.objects.create(produit=self.libre, unites_par_carton=6)
        self.historique = Produit.objects.create(reference='HIST', code_barre='2', designation='Historique',
                                                 categorie=cat, prixU=Decimal('10'), is_active=False)
        StockMove.objects.create(produit=self.historique, delta=5)
        w = Warehouse.objects.create(name='Entrepot PS', code='ENT-PS')
        ProductStock.objects.create(produit=self.historique, warehouse=w, quantity=40)
        Conditionnement.objects.create(produit=self.historique, unites_par_carton=12)
        self.actif = Produit.objects.create(reference='ACTIF', code_barre='3', designation='Actif',
                                            categorie=cat, prixU=Decimal('10'))

    def test_liste_avec_historique_et_stock(self):
        r = self.client.get('/API/produits-supprimes/')
        self.assertEqual(r.status_code, 200)
        par_ref = {p['reference']: p for p in r.data['results']}
        self.assertEqual(set(par_ref), {'LIBRE', 'HIST'})
        self.assertFalse(par_ref['LIBRE']['avec_historique'])
        self.assertTrue(par_ref['HIST']['avec_historique'])
        self.assertIn('mouvement', par_ref['HIST']['historique'][0]['libelle'])
        self.assertEqual(par_ref['HIST']['stock_restant'], 40)
        self.assertEqual(r.data['sans_historique'], 1)
        self.assertEqual(r.data['avec_historique'], 1)

    def test_suppression_definitive_sans_historique_efface_tout(self):
        r = self.client.delete(f'/API/produits-supprimes/{self.libre.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Produit.objects.filter(id=self.libre.id).exists())
        self.assertFalse(Conditionnement.objects.filter(produit_id=self.libre.id).exists())

    def test_suppression_avec_historique_efface_donnees_et_garde_documents(self):
        r = self.client.delete(f'/API/produits-supprimes/{self.historique.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('documents', r.data['message'])
        p = Produit.objects.get(id=self.historique.id)
        # Fiche archivée, invisible, sans stock ni données annexes
        self.assertTrue(p.est_archive)
        self.assertFalse(p.is_active)
        self.assertIsNotNone(p.archive_le)
        self.assertEqual(p.quantite, 0)
        self.assertFalse(ProductStock.objects.filter(produit=p).exists())
        self.assertFalse(Conditionnement.objects.filter(produit=p).exists())
        self.assertFalse(PrixProduit.objects.filter(produit=p).exists())
        # Les documents / mouvements déjà faits restent intacts
        self.assertEqual(StockMove.objects.filter(produit=p).count(), 1)
        self.assertEqual(StockMove.objects.get(produit=p).produit.designation, 'Historique')
        # Plus dans la corbeille
        refs = {x['reference'] for x in self.client.get('/API/produits-supprimes/').data['results']}
        self.assertNotIn('HIST', refs)
        # Tracé dans le journal d'audit avec la quantité supprimée
        log = AuditLog.objects.filter(action='produit.purge').latest('id')
        meta = json.loads(log.metadata)
        self.assertEqual(meta['stock_supprime'], 40)
        self.assertIn('mouvement', meta['documents_conserves'])

    def test_produit_archive_ne_peut_pas_etre_restaure(self):
        self.client.delete(f'/API/produits-supprimes/{self.historique.id}/')
        r = self.client.post(f'/API/produits-supprimes/{self.historique.id}/restaurer/')
        self.assertEqual(r.status_code, 404)

    def test_produit_actif_ne_peut_pas_etre_supprime_ici(self):
        r = self.client.delete(f'/API/produits-supprimes/{self.actif.id}/')
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Produit.objects.filter(id=self.actif.id).exists())

    def test_restaurer(self):
        r = self.client.post(f'/API/produits-supprimes/{self.historique.id}/restaurer/')
        self.assertEqual(r.status_code, 200)
        self.historique.refresh_from_db()
        self.assertTrue(self.historique.is_active)

    def test_suppression_en_lot(self):
        r = self.client.post('/API/produits-supprimes/supprimer-lot/',
                             {'ids': [self.libre.id, self.historique.id, self.actif.id]}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['supprimes'], 2)
        self.assertEqual(r.data['refuses'], 0)
        self.assertFalse(Produit.objects.filter(id=self.libre.id).exists())
        self.assertTrue(Produit.objects.get(id=self.historique.id).est_archive)
        self.assertTrue(Produit.objects.get(id=self.actif.id).is_active)

    def test_reserve_aux_administrateurs(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/API/produits-supprimes/').status_code, 403)
        self.assertEqual(self.client.delete(f'/API/produits-supprimes/{self.libre.id}/').status_code, 403)
        self.assertTrue(Produit.objects.filter(id=self.libre.id).exists())


class StockProduitsSupprimesTests(TestCase):
    """Le stock d'un produit supprimé (désactivé) n'apparaît plus nulle part."""

    def setUp(self):
        from .models import ProductStock, Warehouse
        self.admin = User.objects.create_user('admin_st', password='x', is_staff=True, is_superuser=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        cat = Categorie.objects.create(nom='Cat ST')
        w = Warehouse.objects.create(name='Entrepôt test', code='ENT-T')
        self.actif = Produit.objects.create(reference='ST-ACTIF', code_barre='9', designation='Actif',
                                            categorie=cat, prixU=Decimal('10'), quantite=0)
        self.supprime = Produit.objects.create(reference='ST-SUPP', code_barre='8', designation='Supprime',
                                               categorie=cat, prixU=Decimal('10'), quantite=0, is_active=False)
        ProductStock.objects.create(produit=self.actif, warehouse=w, quantity=5)
        ProductStock.objects.create(produit=self.supprime, warehouse=w, quantity=484)

    def test_api_stocks(self):
        refs = {s['produit'] for s in self.client.get('/API/stocks/').data}
        self.assertIn(self.actif.id, refs)
        self.assertNotIn(self.supprime.id, refs)

    def test_alertes(self):
        data = self.client.get('/API/alerts/?limit=50').json()
        refs = {i['reference'] for i in data['items']}
        self.assertNotIn('ST-SUPP', refs)

    def test_pages_stocks(self):
        from django.test import Client
        c = Client()
        c.force_login(self.admin)
        page = c.get('/page/stocks_list/').content.decode()
        self.assertIn('ST-ACTIF', page)
        self.assertNotIn('ST-SUPP', page)
        page = c.get('/page/entrepots_list/').content.decode()
        self.assertNotIn('489', page)  # 5 + 484 : le stock supprimé ne doit pas être additionné
