"""Ventes avec promotion : les articles offerts EN PLUS (« Achetez X, Y offert(s) ») sortent du stock ;
pour « Achetez X, payez Y » les gratuits sont déjà dans la quantité (rien en plus).
Annuler une vente terminée remet tout en stock ; annuler un brouillon ne touche pas au stock."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Categorie, Client, Produit, ProductStock, Promotion, Vente, Warehouse


class VenteArticlesOffertsTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.jus = Produit.objects.create(reference='JUS', code_barre='1', designation='Jus', prixU=Decimal('100'),
                                          categorie=cat, quantite=50)
        self.depot = Warehouse.objects.create(name='Dépôt', code='DEP')
        ProductStock.objects.create(produit=self.jus, warehouse=self.depot, quantity=50)
        self.client_ = Client.objects.create(nom='Client', prenom='Test', telephone='0')
        maintenant = timezone.now()
        self.offert = Promotion.objects.create(code='6P2', nom='6 achetés, 2 offerts', type_promotion='achetez_x_offert_y',
                                               quantite_achat=6, quantite_offerte=2, produit=self.jus,
                                               date_debut=maintenant - timedelta(days=1), date_fin=maintenant + timedelta(days=9))
        self.payez = Promotion.objects.create(code='3P2', nom='3 pour le prix de 2', type_promotion='achetez_x_payez_y',
                                              quantite_achat=3, quantite_offerte=2, produit=self.jus,
                                              date_debut=maintenant - timedelta(days=1), date_fin=maintenant + timedelta(days=9))
        self.api = APIClient()
        self.api.force_authenticate(User.objects.create_superuser('admin', 'a@a.fr', 'x'))

    def vente(self, qte, promotion=None, statut='completed', offerte_envoyee=0, attendu=201):
        ligne = {'produit': self.jus.id, 'designation': 'Jus', 'quantite': qte, 'prixU_snapshot': '100.00'}
        if promotion:
            ligne.update(promotion=promotion.id, quantite_offerte=offerte_envoyee)
        r = self.api.post('/API/ventes/', {'client': self.client_.id, 'warehouse': self.depot.id, 'type_paiement': 'cash',
                                           'statut': statut, 'lignes': [ligne]}, format='json')
        self.assertEqual(r.status_code, attendu, r.content)
        return r.json()

    def stock(self):
        self.jus.refresh_from_db()
        return ProductStock.objects.get(produit=self.jus, warehouse=self.depot).quantity, self.jus.quantite

    def test_achetez_6_deux_offerts_sortent_du_stock(self):
        v = self.vente(6, self.offert, offerte_envoyee=99)   # le chiffre du navigateur est ignoré
        self.assertEqual(self.stock(), (42, 42))               # 6 achetés + 2 offerts
        self.assertEqual(Vente.objects.get(pk=v['id']).lignes.get().quantite_offerte, 2)

    def test_achetez_3_payez_2_rien_en_plus(self):
        self.vente(6, self.payez, offerte_envoyee=2)
        self.assertEqual(self.stock(), (44, 44))               # les 2 gratuits sont dans les 6

    def test_sans_promotion_inchange(self):
        self.vente(5)
        self.assertEqual(self.stock(), (45, 45))

    def test_brouillon_puis_finalisation(self):
        v = self.vente(12, self.offert, statut='draft')
        self.assertEqual(self.stock(), (50, 50))
        r = self.api.post(f"/API/ventes/{v['id']}/complete/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock()[0], 34)                  # 12 + 4 offerts

    def test_stock_insuffisant_compte_les_offerts(self):
        ProductStock.objects.filter(produit=self.jus).update(quantity=7)
        Produit.objects.filter(pk=self.jus.pk).update(quantite=7)
        self.vente(6, self.offert, attendu=400)                # 6 + 2 = 8 > 7
        self.assertEqual(self.stock(), (7, 7))

    def test_annuler_une_vente_terminee_remet_tout(self):
        v = self.vente(6, self.offert)
        r = self.api.post(f"/API/ventes/{v['id']}/cancel/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(), (50, 50))

    def test_annuler_un_brouillon_ne_touche_pas_au_stock(self):
        v = self.vente(6, statut='draft')
        r = self.api.post(f"/API/ventes/{v['id']}/cancel/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.stock(), (50, 50))               # avant : 56
