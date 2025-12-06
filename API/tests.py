from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from API.models import Produit, Categorie, Fournisseur, Warehouse, ProductStock, Currency

class StockMultiWarehouseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create minimal data
        self.cat = Categorie.objects.create(nom='Cat A')
        self.four = Fournisseur.objects.create(libelle='F1', telephone='1', email='', adresse='')
        # Currency default to avoid None issues in Produit __str__
        self.cur = Currency.objects.create(code='EUR', name='Euro', symbol='€', is_default=True)
        self.p = Produit.objects.create(reference='P1', code_barre='CB1', designation='Prod 1', categorie=self.cat, prixU=10, currency=self.cur, quantite=0, fournisseur=self.four)
        self.w1 = Warehouse.objects.create(name='Depot', code='DEP')
        self.w2 = Warehouse.objects.create(name='Magasin', code='MAG')

    def test_transfer_between_warehouses(self):
        # Seed source stock
        ProductStock.objects.create(produit=self.p, warehouse=self.w1, quantity=20)
        # Ensure aggregate updated
        self.p.quantite = 20
        self.p.save(update_fields=['quantite'])

        url = '/API/mouvements/transfer/'
        payload = { 'produit': self.p.id, 'quantite': 5, 'from_warehouse': self.w1.id, 'to_warehouse': self.w2.id }
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.content)

        # Check stocks
        w1_qty = ProductStock.objects.get(produit=self.p, warehouse=self.w1).quantity
        w2_qty = ProductStock.objects.get(produit=self.p, warehouse=self.w2).quantity
        self.assertEqual(w1_qty, 15)
        self.assertEqual(w2_qty, 5)
        # Aggregate updated
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantite, 20)

        # Journal contains both moves with warehouses
        res_list = self.client.get('/API/mouvements/', {'produit': self.p.id})
        self.assertEqual(res_list.status_code, 200)
        data = res_list.json()
        self.assertTrue(any(m.get('warehouse') == self.w1.id and m.get('delta') == -5 for m in data))
        self.assertTrue(any(m.get('warehouse') == self.w2.id and m.get('delta') == 5 for m in data))

    def test_loss_requires_and_updates_warehouse(self):
        ProductStock.objects.create(produit=self.p, warehouse=self.w1, quantity=10)
        self.p.quantite = 10
        self.p.save(update_fields=['quantite'])

        # Missing warehouse -> 400
        res_bad = self.client.post('/API/mouvements/loss/', { 'produit': self.p.id, 'quantite': 3, 'type':'PERTE' }, format='json')
        self.assertEqual(res_bad.status_code, 400)

        # With warehouse -> ok
        res = self.client.post('/API/mouvements/loss/', { 'produit': self.p.id, 'quantite': 3, 'type':'PERTE', 'warehouse': self.w1.id }, format='json')
        self.assertEqual(res.status_code, 201, res.content)

        ps = ProductStock.objects.get(produit=self.p, warehouse=self.w1)
        self.assertEqual(ps.quantity, 7)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantite, 7)

    def test_edit_product_stock_via_api_updates_aggregate(self):
        # Create empty stocks for both
        ProductStock.objects.create(produit=self.p, warehouse=self.w1, quantity=2)
        ProductStock.objects.create(produit=self.p, warehouse=self.w2, quantity=3)
        self.p.quantite = 5
        self.p.save(update_fields=['quantite'])

        # Update one row via API
        row = ProductStock.objects.get(produit=self.p, warehouse=self.w1)
        res = self.client.patch(f'/API/stocks/{row.id}/', {'quantity': 6}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantite, 9)

        # Create a new warehouse stock via API
        w3 = Warehouse.objects.create(name='Annexe', code='ANX')
        res2 = self.client.post('/API/stocks/', {'produit': self.p.id, 'warehouse': w3.id, 'quantity': 1}, format='json')
        self.assertEqual(res2.status_code, 201, res2.content)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantite, 10)
