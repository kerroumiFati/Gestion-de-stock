"""Transfert de TOUT le stock d'un entrepôt vers un autre (POST /API/mouvements/transfer-all/)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Company, Produit, ProductStock, StockMove, UserProfile, Warehouse

URL = '/API/mouvements/transfer-all/'


class TransfertCompletTests(TestCase):
    def setUp(self):
        self.societe = Company.objects.create(name='Société A', code='SOCA')
        self.autre = Company.objects.create(name='Société B', code='SOCB')
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau', prixU=Decimal('10'), categorie=cat)
        self.jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus', prixU=Decimal('20'), categorie=cat)
        self.chips = Produit.objects.create(reference='CHIPS', code_barre='3', designation='Chips', prixU=Decimal('5'), categorie=cat)
        self.depot = Warehouse.objects.create(code='DEP1', name='Dépôt centre', company=self.societe)
        self.magasin = Warehouse.objects.create(code='MAG1', name='Magasin', company=self.societe)
        self.etranger = Warehouse.objects.create(code='EXT', name='Dépôt société B', company=self.autre)
        ProductStock.objects.create(produit=self.eau, warehouse=self.depot, quantity=12)
        ProductStock.objects.create(produit=self.jus, warehouse=self.depot, quantity=5)
        ProductStock.objects.create(produit=self.chips, warehouse=self.depot, quantity=0)   # rien à déplacer
        ProductStock.objects.create(produit=self.eau, warehouse=self.magasin, quantity=3)
        user = User.objects.create_user('gerant', password='x', is_staff=True)
        UserProfile.objects.create(user=user, company=self.societe)
        self.api = APIClient()
        self.api.force_authenticate(user)

    def stock(self, produit, entrepot):
        ps = ProductStock.objects.filter(produit=produit, warehouse=entrepot).first()
        return ps.quantity if ps else 0

    def test_apercu_ne_change_rien(self):
        r = self.api.post(URL, {'from_warehouse': self.depot.id, 'dry_run': True}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['nb_produits'], 2)
        self.assertEqual(r.json()['total_unites'], 17)
        self.assertEqual(self.stock(self.eau, self.depot), 12)
        self.assertFalse(StockMove.objects.exists())

    def test_transfert_complet(self):
        r = self.api.post(URL, {'from_warehouse': self.depot.id, 'to_warehouse': self.magasin.id, 'note': 'Fermeture'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['nb_produits'], 2)
        self.assertEqual(self.stock(self.eau, self.depot), 0)
        self.assertEqual(self.stock(self.jus, self.depot), 0)
        self.assertEqual(self.stock(self.eau, self.magasin), 15)   # 3 déjà présents + 12
        self.assertEqual(self.stock(self.jus, self.magasin), 5)
        # Journal : une sortie et une entrée par produit, même référence
        moves = StockMove.objects.filter(ref_id=r.json()['reference'])
        self.assertEqual(moves.count(), 4)
        self.assertEqual(sum(m.delta for m in moves), 0)
        self.assertTrue(all('Fermeture' in m.note for m in moves))
        # Second essai : le dépôt est vide
        r = self.api.post(URL, {'from_warehouse': self.depot.id, 'to_warehouse': self.magasin.id}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_refus(self):
        cas = [
            ({'from_warehouse': self.depot.id, 'to_warehouse': self.depot.id}, 400),     # même entrepôt
            ({'from_warehouse': self.depot.id}, 400),                                    # pas de destination
            ({'from_warehouse': self.depot.id, 'to_warehouse': self.etranger.id}, 404),  # autre société
            ({'from_warehouse': self.etranger.id, 'dry_run': True}, 404),                # stock d'une autre société
        ]
        for data, code in cas:
            self.assertEqual(self.api.post(URL, data, format='json').status_code, code, data)
        Warehouse.objects.filter(pk=self.magasin.pk).update(is_active=False)
        r = self.api.post(URL, {'from_warehouse': self.depot.id, 'to_warehouse': self.magasin.id}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.stock(self.eau, self.depot), 12)   # rien n'a bougé
