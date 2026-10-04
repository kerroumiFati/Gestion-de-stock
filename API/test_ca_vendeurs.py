"""Tests du chiffre d'affaires par vendeur, mois par mois (API/indicateurs.py, calculer_ca_mensuel)."""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .indicateurs import calculer_ca_mensuel
from .models import Client
from .distribution_models import CommandeClient, LivreurDistribution, TourneeMobile, VenteTourneeMobile


def _dt(y, m, d):
    return timezone.make_aware(datetime(y, m, d, 10, 0))


class CAVendeursTests(TestCase):
    def setUp(self):
        self.ahmed = LivreurDistribution.objects.create(matricule='V1', nom='Ahmed', telephone='0')
        self.yacine = LivreurDistribution.objects.create(matricule='V2', nom='Yacine', telephone='0')
        self.inactif = LivreurDistribution.objects.create(matricule='V3', nom='Zed', telephone='0', statut='inactif')
        self.client_ = Client.objects.create(nom='C', prenom='x', telephone='0')
        self._n = 0

    def _vente(self, vendeur, y, m, d, montant):
        self._n += 1
        t, _ = TourneeMobile.objects.get_or_create(livreur=vendeur, date_tournee=date(y, m, d),
                                                   defaults={'numero_tournee': f'T-{vendeur.id}-{y}{m:02d}{d:02d}'})
        return VenteTourneeMobile.objects.create(tournee=t, client=self.client_, numero_vente=f'V-{self._n}',
                                                 date_vente=_dt(y, m, d), type_paiement='especes', montant_total=montant)

    def _commande(self, vendeur, y, m, d, montant, statut='pending'):
        self._n += 1
        c = CommandeClient.objects.create(client=self.client_, livreur=vendeur, reference=f'CMD-{self._n}')
        CommandeClient.objects.filter(pk=c.pk).update(date_commande=_dt(y, m, d), montant_total_ttc=montant, statut=statut)
        return c

    def _donnees(self):
        self._vente(self.ahmed, 2026, 1, 10, 100)
        self._vente(self.ahmed, 2026, 1, 20, 50)
        self._commande(self.ahmed, 2026, 1, 15, 30)
        self._commande(self.ahmed, 2026, 1, 16, 999, statut='cancelled')     # annulee : ignoree
        self._vente(self.ahmed, 2026, 9, 5, 400)
        self._commande(self.ahmed, 2026, 9, 6, 200, statut='delivered')
        self._vente(self.ahmed, 2025, 9, 5, 7777)                            # autre annee
        self._commande(self.yacine, 2026, 9, 7, 1000)                        # prevendeur : commandes seulement

    def test_ca_mois_par_mois(self):
        self._donnees()
        data = calculer_ca_mensuel(2026, aujourd_hui=date(2026, 9, 29))
        self.assertEqual([v['nom'] for v in data['vendeurs']], ['Yacine', 'Ahmed'])   # tri par CA annuel
        ahmed = next(v for v in data['vendeurs'] if v['nom'] == 'Ahmed')
        janvier, septembre = ahmed['mois'][0], ahmed['mois'][8]
        self.assertEqual((janvier['ventes'], janvier['commandes'], janvier['total']), (150.0, 30.0, 180.0))
        self.assertEqual((janvier['nb_ventes'], janvier['nb_commandes']), (2, 1))
        self.assertEqual((septembre['ventes'], septembre['commandes'], septembre['total']), (400.0, 200.0, 600.0))
        self.assertEqual(ahmed['mois'][5]['total'], 0.0)
        self.assertEqual(len(ahmed['mois']), 12)
        self.assertEqual((ahmed['total_ventes'], ahmed['total_commandes'], ahmed['total_annee']), (550.0, 230.0, 780.0))

    def test_ca_du_mois_en_cours_affiche_a_part(self):
        self._donnees()
        data = calculer_ca_mensuel(2026, aujourd_hui=date(2026, 9, 29))
        self.assertEqual(data['mois_courant'], 9)
        self.assertEqual(data['mois_en_cours'], {'mois': 9, 'libelle': 'Septembre 2026', 'total': 1600.0,
                                                 'ventes': 400.0, 'commandes': 1200.0})
        ahmed = next(v for v in data['vendeurs'] if v['nom'] == 'Ahmed')
        self.assertEqual((ahmed['ca_mois_courant'], ahmed['ca_mois_courant_ventes'], ahmed['ca_mois_courant_commandes']),
                         (600.0, 400.0, 200.0))
        yacine = next(v for v in data['vendeurs'] if v['nom'] == 'Yacine')
        self.assertEqual(yacine['ca_mois_courant'], 1000.0)

    def test_totaux_et_annee_passee(self):
        self._donnees()
        data = calculer_ca_mensuel(2026, aujourd_hui=date(2026, 9, 29))
        self.assertEqual(data['totaux_mois'][0]['total'], 180.0)
        self.assertEqual(data['totaux_mois'][8], {'mois': 9, 'ventes': 400.0, 'commandes': 1200.0, 'total': 1600.0})
        self.assertEqual(data['total_annee'], 1780.0)
        passe = calculer_ca_mensuel(2025, aujourd_hui=date(2026, 9, 29))
        self.assertIsNone(passe['mois_courant'])
        self.assertIsNone(passe['mois_en_cours']['total'])
        self.assertEqual(passe['total_annee'], 7777.0)

    def test_vendeurs_affiches(self):
        self._vente(self.inactif, 2026, 3, 1, 10)
        data = calculer_ca_mensuel(2026, aujourd_hui=date(2026, 9, 29))
        self.assertEqual({v['nom'] for v in data['vendeurs']}, {'Ahmed', 'Yacine', 'Zed'})   # inactif avec CA : affiche
        data = calculer_ca_mensuel(2025, aujourd_hui=date(2026, 9, 29))
        self.assertEqual({v['nom'] for v in data['vendeurs']}, {'Ahmed', 'Yacine'})          # inactif sans CA : masque
        data = calculer_ca_mensuel(2026, livreur_id=self.yacine.id, aujourd_hui=date(2026, 9, 29))
        self.assertEqual([v['nom'] for v in data['vendeurs']], ['Yacine'])

    def test_coherence_avec_le_taux_de_realisation(self):
        """Le CA du mois doit etre celui qui sert aux objectifs quand le perimetre couvre tout."""
        from .indicateurs import calculer_indicateurs_vendeur
        self._donnees()
        ind = calculer_indicateurs_vendeur(self.ahmed, date(2026, 9, 1), date(2026, 9, 30), aujourd_hui=date(2026, 9, 30))
        data = calculer_ca_mensuel(2026, livreur_id=self.ahmed.id, aujourd_hui=date(2026, 9, 29))
        self.assertEqual(ind['ca_periode'], data['vendeurs'][0]['ca_mois_courant'])

    def test_api(self):
        self._donnees()
        api = APIClient()
        self.assertIn(api.get('/API/distribution/ca-vendeurs/').status_code, (401, 403))
        api.force_authenticate(User.objects.create_user('u', password='x'))
        r = api.get('/API/distribution/ca-vendeurs/?annee=2026')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['annee'], 2026)
        self.assertEqual(len(r.json()['vendeurs']), 2)
        self.assertEqual(r.json()['total_annee'], 1780.0)
        self.assertEqual(api.get('/API/distribution/ca-vendeurs/').status_code, 200)
        self.assertEqual(api.get('/API/distribution/ca-vendeurs/?annee=abc').status_code, 400)
        self.assertEqual(api.get('/API/distribution/ca-vendeurs/?annee=1800').status_code, 400)
        self.assertEqual(api.get('/API/distribution/ca-vendeurs/?annee=2026&livreur_id=x').status_code, 400)
