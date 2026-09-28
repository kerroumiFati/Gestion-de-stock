"""Tests du conditionnement (unites par carton) expose via l'API produit.

Le stock reste en unites ; ces tests verifient que :
- le serializer produit lit/ecrit le Conditionnement actif ;
- l'API mobile expose unites_par_carton ;
- la conversion d'achat en cartons n'est plus doublee.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from .models import Achat, Categorie, Conditionnement, Produit
from .serializers import AchatSerializer, ProduitSerializer
from .distribution_serializers import ProduitMobileSerializer


class ConditionnementProduitTests(TestCase):
    def setUp(self):
        self.categorie = Categorie.objects.create(nom='Boissons')
        self.request = APIRequestFactory().post('/API/produits/')
        self.request.company = None

    def _payload(self, **extra):
        data = {
            'reference': 'REF-001', 'code_barre': '123456', 'designation': 'Eau 1L',
            'categorie': self.categorie.id, 'prixU': '50.00',
        }
        data.update(extra)
        return data

    def test_creation_avec_conditionnement(self):
        s = ProduitSerializer(data=self._payload(unites_par_carton=12, cartons_par_colis=4),
                              context={'request': self.request})
        self.assertTrue(s.is_valid(), s.errors)
        produit = s.save()
        cond = produit.conditionnements.get()
        self.assertEqual(cond.unites_par_carton, 12)
        self.assertEqual(cond.cartons_par_colis, 4)
        self.assertEqual(s.data['unites_par_carton'], 12)
        self.assertEqual(s.data['cartons_par_colis'], 4)

    def test_creation_sans_conditionnement_ne_cree_rien(self):
        s = ProduitSerializer(data=self._payload(), context={'request': self.request})
        self.assertTrue(s.is_valid(), s.errors)
        produit = s.save()
        self.assertEqual(produit.conditionnements.count(), 0)
        self.assertEqual(s.data['unites_par_carton'], 1)

    def test_mise_a_jour_sans_les_champs_ne_touche_pas_le_conditionnement(self):
        produit = Produit.objects.create(reference='R', code_barre='CB', designation='D',
                                         categorie=self.categorie, prixU=Decimal('10'))
        Conditionnement.objects.create(produit=produit, unites_par_carton=6)
        s = ProduitSerializer(produit, data={'designation': 'D2'}, partial=True,
                              context={'request': self.request})
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(produit.conditionnements.get().unites_par_carton, 6)

    def test_mise_a_jour_modifie_puis_supprime_le_carton(self):
        produit = Produit.objects.create(reference='R', code_barre='CB', designation='D',
                                         categorie=self.categorie, prixU=Decimal('10'))
        s = ProduitSerializer(produit, data={'unites_par_carton': 24}, partial=True,
                              context={'request': self.request})
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(produit.get_unites_par_carton(), 24)
        # null -> retour a 1 (pas de carton)
        s = ProduitSerializer(produit, data={'unites_par_carton': None}, partial=True,
                              context={'request': self.request})
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        self.assertEqual(produit.get_unites_par_carton(), 1)

    def test_valeur_invalide_refusee(self):
        s = ProduitSerializer(data=self._payload(unites_par_carton=0), context={'request': self.request})
        self.assertFalse(s.is_valid())
        self.assertIn('unites_par_carton', s.errors)

    def test_format_cartons(self):
        self.assertEqual(Produit.format_cartons(38, 12), '3 ct + 2 u')
        self.assertEqual(Produit.format_cartons(36, 12), '3 ct')
        self.assertEqual(Produit.format_cartons(5, 12), '0 ct + 5 u')
        self.assertEqual(Produit.format_cartons(-14, 12), '-1 ct + 2 u')
        self.assertEqual(Produit.format_cartons(38, 1), '')
        self.assertEqual(Produit.format_cartons(None, None), '')

    def test_api_mobile_expose_le_conditionnement(self):
        produit = Produit.objects.create(reference='R', code_barre='CB', designation='D',
                                         categorie=self.categorie, prixU=Decimal('10'))
        Conditionnement.objects.create(produit=produit, unites_par_carton=6, cartons_par_colis=3)
        data = ProduitMobileSerializer(produit).data
        self.assertEqual(data['unites_par_carton'], 6)
        self.assertEqual(data['cartons_par_colis'], 3)

    def test_conditionnement_inactif_ignore(self):
        produit = Produit.objects.create(reference='R', code_barre='CB', designation='D',
                                         categorie=self.categorie, prixU=Decimal('10'))
        Conditionnement.objects.create(produit=produit, unites_par_carton=6, is_active=False)
        self.assertEqual(produit.get_unites_par_carton(), 1)


class AchatCartonTests(TestCase):
    def test_conversion_non_doublee(self):
        # 3 cartons de 12 a 50 la piece : l'ecran envoie quantite=36, prix_achat=50
        a = Achat(unite_achat='carton', quantite=36, pieces_par_carton=12, prix_achat=Decimal('50'))
        self.assertEqual(a.get_quantite_pieces(), 36)
        self.assertEqual(a.get_nb_cartons(), 3)
        self.assertEqual(a.get_prix_unitaire_piece(), Decimal('50'))
        self.assertEqual(a.get_prix_carton(), Decimal('600'))
        self.assertEqual(a.get_prix_total(), Decimal('1800'))

    def test_validation_multiple_du_carton(self):
        s = AchatSerializer()
        with self.assertRaises(Exception):
            s.validate({'unite_achat': 'carton', 'quantite': 35, 'pieces_par_carton': 12})
        self.assertEqual(s.validate({'unite_achat': 'piece', 'quantite': 7})['quantite'], 7)
