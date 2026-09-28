"""Tests des objectifs mensuels de CA des vendeurs (ObjectifVendeur).

Deux perimetres : entrepot / gamme de rattachement du produit, et type de produit
(categorie + sous-categories). Le CA realise = lignes de ventes de tournee (TTC) du
vendeur sur le mois, filtrees sur le perimetre, avec un taux calcule separement.
"""
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Categorie, Client, Produit, Warehouse
from .distribution_models import (
    LigneVenteTourneeMobile, LivreurDistribution, ObjectifVendeur, TourneeMobile, VenteTourneeMobile,
)
from .distribution_serializers import ObjectifVendeurSerializer


def _dt(y, m, d):
    return timezone.make_aware(datetime(y, m, d, 10, 0)) if timezone.is_naive(datetime(y, m, d)) else datetime(y, m, d)


class ObjectifVendeurTests(TestCase):
    def setUp(self):
        self.ent1 = Warehouse.objects.create(code='ENT1', name='Entrepôt Frais')
        self.ent2 = Warehouse.objects.create(code='ENT2', name='Entrepôt Sec')
        self.cat_boissons = Categorie.objects.create(nom='Boissons')
        self.cat_jus = Categorie.objects.create(nom='Jus', parent=self.cat_boissons)
        self.cat_snacks = Categorie.objects.create(nom='Snacks')
        self.p_eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau', prixU=Decimal('10'),
                                            categorie=self.cat_boissons, entrepot_rattachement=self.ent1)
        self.p_jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus', prixU=Decimal('20'),
                                            categorie=self.cat_jus, entrepot_rattachement=self.ent2)
        self.p_chips = Produit.objects.create(reference='CHIPS', code_barre='3', designation='Chips', prixU=Decimal('5'),
                                              categorie=self.cat_snacks, entrepot_rattachement=self.ent1)
        self.livreur = LivreurDistribution.objects.create(matricule='LIV1', nom='Ahmed', telephone='0')
        self.autre = LivreurDistribution.objects.create(matricule='LIV2', nom='Yacine', telephone='0')
        self.client_ = Client.objects.create(nom='Client', prenom='Test', telephone='0')

    def _vente(self, livreur, y, m, d, lignes, numero):
        tournee = TourneeMobile.objects.create(livreur=livreur, date_tournee=datetime(y, m, d).date(),
                                               numero_tournee=f'T-{numero}')
        vente = VenteTourneeMobile.objects.create(tournee=tournee, client=self.client_, numero_vente=f'V-{numero}',
                                                  date_vente=_dt(y, m, d), type_paiement='especes')
        for produit, ttc in lignes:
            # Le modele recalcule les montants (prix x quantite, TVA) : TVA a 0 => TTC = prix
            LigneVenteTourneeMobile.objects.create(
                vente=vente, produit=produit, quantite=1, prix_unitaire=ttc, taux_tva=0,
                montant_ht=ttc, montant_tva=0, montant_ttc=ttc)
        return vente

    def _ventes_septembre(self):
        # Septembre 2026 : Eau 100 (ENT1/Boissons), Jus 50 (ENT2/Jus), Chips 30 (ENT1/Snacks)
        self._vente(self.livreur, 2026, 9, 15, [(self.p_eau, 100), (self.p_jus, 50), (self.p_chips, 30)], 1)
        # Août 2026 (hors periode) et autre vendeur (hors perimetre)
        self._vente(self.livreur, 2026, 8, 20, [(self.p_eau, 999)], 2)
        self._vente(self.autre, 2026, 9, 16, [(self.p_eau, 777)], 3)

    def test_objectif_par_entrepot(self):
        self._ventes_septembre()
        obj = ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='entrepot',
                                             entrepot=self.ent1, montant_objectif=Decimal('200'))
        suivi = obj.get_suivi()
        self.assertEqual(suivi['ca_realise'], Decimal('130'))   # Eau 100 + Chips 30
        self.assertEqual(suivi['taux_reussite'], 65.0)
        self.assertEqual(suivi['reste'], Decimal('70'))
        self.assertFalse(suivi['atteint'])

    def test_objectif_par_type_de_produit_inclut_sous_categories(self):
        self._ventes_septembre()
        obj = ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='categorie',
                                             categorie=self.cat_boissons, montant_objectif=Decimal('100'))
        suivi = obj.get_suivi()
        self.assertEqual(suivi['ca_realise'], Decimal('150'))   # Eau 100 + Jus 50 (sous-categorie)
        self.assertEqual(suivi['taux_reussite'], 150.0)
        self.assertTrue(suivi['atteint'])
        self.assertEqual(suivi['reste'], Decimal('0'))

    def test_deux_objectifs_distincts_taux_separes(self):
        self._ventes_septembre()
        o1 = ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='entrepot',
                                            entrepot=self.ent2, montant_objectif=Decimal('100'))
        o2 = ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='categorie',
                                            categorie=self.cat_snacks, montant_objectif=Decimal('60'))
        self.assertEqual(o1.get_suivi()['taux_reussite'], 50.0)   # Jus 50 / 100
        self.assertEqual(o2.get_suivi()['taux_reussite'], 50.0)   # Chips 30 / 60
        self.assertEqual(ObjectifVendeur.objects.filter(livreur=self.livreur, annee=2026, mois=9).count(), 2)

    def test_sans_vente_taux_zero(self):
        obj = ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='entrepot',
                                             entrepot=self.ent1, montant_objectif=Decimal('500'))
        self.assertEqual(obj.get_suivi()['ca_realise'], Decimal('0'))
        self.assertEqual(obj.get_suivi()['taux_reussite'], 0.0)

    def test_clean_perimetre_coherent(self):
        obj = ObjectifVendeur(livreur=self.livreur, annee=2026, mois=9, type_perimetre='entrepot',
                              montant_objectif=Decimal('10'))
        with self.assertRaises(ValidationError):
            obj.clean()
        obj = ObjectifVendeur(livreur=self.livreur, annee=2026, mois=9, type_perimetre='categorie',
                              entrepot=self.ent1, categorie=self.cat_snacks, montant_objectif=Decimal('10'))
        obj.clean()
        self.assertIsNone(obj.entrepot)   # l'entrepot est ignore sur un perimetre categorie

    def test_serializer_validation_et_sortie(self):
        self._ventes_septembre()
        s = ObjectifVendeurSerializer(data={'livreur': self.livreur.id, 'annee': 2026, 'mois': 9,
                                            'type_perimetre': 'entrepot', 'montant_objectif': '200'})
        self.assertFalse(s.is_valid())
        self.assertIn('entrepot', s.errors)

        s = ObjectifVendeurSerializer(data={'livreur': self.livreur.id, 'annee': 2026, 'mois': 13,
                                            'type_perimetre': 'entrepot', 'entrepot': self.ent1.id, 'montant_objectif': '200'})
        self.assertFalse(s.is_valid())

        s = ObjectifVendeurSerializer(data={'livreur': self.livreur.id, 'annee': 2026, 'mois': 9,
                                            'type_perimetre': 'entrepot', 'entrepot': self.ent1.id,
                                            'categorie': self.cat_snacks.id, 'montant_objectif': '200'})
        self.assertTrue(s.is_valid(), s.errors)
        obj = s.save()
        self.assertIsNone(obj.categorie)
        data = ObjectifVendeurSerializer(obj).data
        self.assertEqual(data['ca_realise'], 130.0)
        self.assertEqual(data['taux_reussite'], 65.0)
        self.assertEqual(data['reste'], 70.0)
        self.assertFalse(data['atteint'])
        self.assertEqual(data['perimetre_label'], 'Entrepôt Entrepôt Frais')
        self.assertEqual(data['mois_display'], 'Septembre')

    def test_unicite_par_perimetre_et_mois(self):
        ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='entrepot',
                                       entrepot=self.ent1, montant_objectif=Decimal('1'))
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError), transaction.atomic():
            ObjectifVendeur.objects.create(livreur=self.livreur, annee=2026, mois=9, type_perimetre='entrepot',
                                           entrepot=self.ent1, montant_objectif=Decimal('2'))
