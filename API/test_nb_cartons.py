"""Colonne « Nb cartons » des impressions serveur : nombre de cartons vendus, le reste en fraction
de carton (carton de 8 : 1 u = « 1/8 », 8 u = « 1 », 10 u = « 1 + 2/8 »)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Conditionnement, Produit, ProductStock, Vente, Warehouse
from .views import nb_cartons


class NbCartonsTests(TestCase):
    def test_calcul(self):
        self.assertEqual(nb_cartons(1, 8), '1/8')
        self.assertEqual(nb_cartons(8, 8), '1')
        self.assertEqual(nb_cartons(10, 8), '1 + 2/8')
        self.assertEqual(nb_cartons(16, 8), '2')
        self.assertEqual(nb_cartons(5, 1), '-')
        self.assertEqual(nb_cartons(0, 8), '0')

    def test_bon_de_vente_et_bl_imprimes(self):
        cat = Categorie.objects.create(nom='Crèmerie')
        creme = Produit.objects.create(reference='CR', code_barre='1', designation='Crème fraîche 380ml',
                                       prixU=Decimal('100'), categorie=cat, quantite=100)
        Conditionnement.objects.create(produit=creme, unites_par_carton=8, is_active=True)
        eau = Produit.objects.create(reference='EAU', code_barre='2', designation='Eau', prixU=Decimal('10'),
                                     categorie=cat, quantite=100)
        depot = Warehouse.objects.create(name='Dépôt', code='DEP')
        ProductStock.objects.create(produit=creme, warehouse=depot, quantity=100)
        ProductStock.objects.create(produit=eau, warehouse=depot, quantity=100)
        client = Client.objects.create(nom='Client', prenom='T', telephone='0')
        api = APIClient(); api.force_authenticate(User.objects.create_superuser('admin', 'a@a.fr', 'x'))
        r = api.post('/API/ventes/', {'client': client.id, 'warehouse': depot.id, 'type_paiement': 'cash', 'statut': 'draft',
                                      'lignes': [{'produit': creme.id, 'designation': 'Crème', 'quantite': 1, 'prixU_snapshot': '100'},
                                                 {'produit': creme.id, 'designation': 'Crème', 'quantite': 10, 'prixU_snapshot': '100'},
                                                 {'produit': eau.id, 'designation': 'Eau', 'quantite': 3, 'prixU_snapshot': '10'}]},
                     format='json')
        self.assertEqual(r.status_code, 201, r.content)
        vid = r.json()['id']
        self.assertEqual(api.post(f'/API/ventes/{vid}/complete/').status_code, 200)
        for url in (f'/API/ventes/{vid}/printable/', f'/API/bons/{Vente.objects.get(pk=vid).bon_livraison_id}/printable/'):
            html = api.get(url).content.decode()
            self.assertIn('>Nb cartons</th>', html, url)
            self.assertNotIn('Qté / carton', html, url)
            self.assertIn('<td class="c">1/8</td>', html, url)       # 1 pièce
            self.assertIn('<td class="c">1 + 2/8</td>', html, url)   # 10 pièces
            self.assertIn('<td class="c">-</td>', html, url)         # eau : pas en carton
