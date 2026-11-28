"""Erreurs des journaux de production du 28/11/2026.

1. POST /API/livreurs/ : 500 IntegrityError (matricule en double, double envoi du formulaire).
2. GET /API/sync/deltas/ : 404 (route inexistante, appelée par l'application mobile).
3. GET /API/distribution/comptes-clients/ : 400 « tournees ou clients est requis » (42 octets).
4. GET /API/distribution/livreurs/<id>/stock_van/ : 404 quand le livreur n'a pas de van.
5. Van partagé sans entreprise (« CENTRAL ») : tarifs du van calculés pour « aucune entreprise ».
"""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Categorie, Client, Company, ProductStock, Produit, Promotion, TypePrix, UserProfile, Warehouse
from .distribution_models import ArretTourneeMobile, LivreurDistribution, TourneeMobile
from .distribution_serializers import LivreurSerializer
from .securite_encaissements import company_id_du_livreur

BASE = '/API/distribution'


class Base(TestCase):
    def setUp(self):
        self.co = Company.objects.create(name='Société A', code='A')
        self.co_b = Company.objects.create(name='Société B', code='B')
        self.van = Warehouse.objects.create(company=self.co, name='Van 1', code='VAN1')
        self.user = User.objects.create_user('liv1', password='x')
        self.livreur = LivreurDistribution.objects.create(matricule='LIV1', nom='Livreur Un', telephone='0',
                                                          user=self.user, entrepot=self.van)
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.client_a = Client.objects.create(nom='MINI market', prenom='ahmed', telephone='1', company=self.co)


class CreationLivreurTests(Base):
    def setUp(self):
        super().setUp()
        self.admin = APIClient()
        self.admin.force_authenticate(User.objects.create_superuser('admin', 'a@a.fr', 'x'))

    def _donnees(self, matricule='AHMEDBENAL'):
        return {'matricule': matricule, 'nom': 'Ahmed Benali', 'telephone': '0550', 'statut': 'actif',
                'entrepot': self.van.id}

    def test_matricule_en_double_400_lisible(self):
        self.assertEqual(self.admin.post('/API/livreurs/', self._donnees(), format='json').status_code, 201)
        r = self.admin.post('/API/livreurs/', self._donnees(), format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('Ce matricule existe déjà (AHMEDBENAL)', r.json()['matricule'][0])
        # même matricule, autre casse : refusé aussi
        r = self.admin.post('/API/livreurs/', self._donnees('ahmedbenal'), format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(LivreurDistribution.objects.filter(matricule__iexact='AHMEDBENAL').count(), 1)

    def test_envoi_simultane_integrity_error_400_et_rien_de_cree(self):
        """Deux envois à la même seconde : le second passe la validation (le premier n'est pas encore
        enregistré) puis bute sur la contrainte unique. Avant : 500."""
        LivreurDistribution.objects.create(matricule='AHMEDBENAL', nom='Ahmed Benali', telephone='0')
        nb_users = User.objects.count()
        with mock.patch.object(LivreurSerializer, 'validate_matricule', side_effect=lambda v: v):
            r = self.admin.post('/API/livreurs/', self._donnees(), format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn('Ce matricule existe déjà', r.json()['error'])
        self.assertEqual(LivreurDistribution.objects.filter(matricule='AHMEDBENAL').count(), 1)
        self.assertEqual(User.objects.count(), nb_users)   # aucun compte orphelin

    def test_modification_sans_changer_le_matricule(self):
        r = self.admin.patch(f'/API/livreurs/{self.livreur.id}/', {'matricule': 'LIV1', 'telephone': '9'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)


class SyncDeltasTests(Base):
    def setUp(self):
        super().setUp()
        self.t = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=timezone.localdate(),
                                              numero_tournee='T-1', statut='en_cours', argent_depart=Decimal('5000'))
        self.arret = ArretTourneeMobile.objects.create(tournee=self.t, client=self.client_a, ordre_passage=1,
                                                       statut='livre')

    def test_deltas_existe_et_format_du_telephone(self):
        r = self.api.get('/API/sync/deltas/')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual(set(d) >= {'tournees', 'arrets', 'clients', 'suppressions'}, True)
        self.assertEqual(d['tournees'][0]['id'], str(self.t.id))
        self.assertEqual(d['tournees'][0]['status'], 'in_progress')
        self.assertEqual(d['tournees'][0]['assigned_to'], str(self.livreur.id))
        self.assertEqual(d['tournees'][0]['argent_depart'], 5000.0)
        a = d['arrets'][0]
        self.assertEqual((a['tournee_id'], a['client_id'], a['client_nom'], a['statut']),
                         (str(self.t.id), str(self.client_a.id), 'MINI market', 'success'))
        # Alias sous /API/distribution/
        self.assertEqual(self.api.get(f'{BASE}/sync/deltas/').status_code, 200)

    def test_meme_selection_que_pull(self):
        pull = self.api.post(f'{BASE}/sync/pull/', {'livreur_id': self.livreur.id}, format='json').json()
        deltas = self.api.get('/API/sync/deltas/').json()
        self.assertEqual([str(t['id']) for t in pull['tournees']], [t['id'] for t in deltas['tournees']])
        self.assertEqual(pull['nb_arrets'], deltas['nb_arrets'])

    def test_since(self):
        futur = (timezone.now() + timedelta(hours=1)).isoformat()
        self.assertEqual(self.api.get('/API/sync/deltas/', {'since': futur}).json()['tournees'], [])
        passe = (timezone.now() - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.000Z')   # format du téléphone
        self.assertEqual(len(self.api.get('/API/sync/deltas/', {'since': passe}).json()['tournees']), 1)
        self.assertEqual(self.api.get('/API/sync/deltas/', {'since': 'hier'}).status_code, 400)

    def test_permissions(self):
        autre = LivreurDistribution.objects.create(matricule='LIV2', nom='Autre', telephone='0', entrepot=self.van,
                                                   user=User.objects.create_user('liv2', password='x'))
        self.assertEqual(self.api.get('/API/sync/deltas/', {'livreur_id': autre.id}).status_code, 403)
        bureau = APIClient()
        bureau.force_authenticate(User.objects.create_user('bureau', password='x'))
        r = bureau.get('/API/sync/deltas/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('livreur_id', r.json()['error'])
        self.assertEqual(APIClient().get('/API/sync/deltas/').status_code, 401)


class ComptesClientsTests(Base):
    def test_tournee_sans_arret_200_liste_vide(self):
        """Cause des 400 de 42 octets : l'app envoie ?tournees=<id> d'une tournée sans arrêt."""
        t = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=timezone.localdate(),
                                         numero_tournee='T-VIDE', statut='en_cours')
        r = self.api.get(f'{BASE}/comptes-clients/', {'tournees': str(t.id)})
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json(), [])

    def test_sans_parametre_livreur_clients_de_ses_tournees_en_cours(self):
        t = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=timezone.localdate(),
                                         numero_tournee='T-2', statut='en_cours')
        ArretTourneeMobile.objects.create(tournee=t, client=self.client_a, ordre_passage=1)
        r = self.api.get(f'{BASE}/comptes-clients/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual([c['client_id'] for c in r.json()], [self.client_a.id])

    def test_sans_parametre_hors_livreur_message_clair(self):
        bureau = APIClient()
        bureau.force_authenticate(User.objects.create_user('bureau', password='x'))
        r = bureau.get(f'{BASE}/comptes-clients/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('tournees', r.json()['error'])

    def test_clients_toujours_servis(self):
        r = self.api.get(f'{BASE}/comptes-clients/', {'clients': str(self.client_a.id)})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 1)


class StockVanSansVanTests(Base):
    def test_sans_van_200_liste_vide(self):
        self.livreur.entrepot = None
        self.livreur.save()
        r = self.api.get(f'{BASE}/livreurs/{self.livreur.id}/stock_van/')
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        self.assertEqual((d['a_van'], d['sans_van'], d['stocks'], d['van']), (False, True, [], None))
        self.assertIn("pas de van", d['message'])
        # Champs lus sans condition par l'écran « Stock du van » de l'application installée
        self.assertEqual(d['statistiques']['nb_references'], 0)
        self.assertIn('currency_symbol', d['statistiques'])

    def test_avec_van_a_van_true(self):
        r = self.api.get(f'{BASE}/livreurs/{self.livreur.id}/stock_van/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['a_van'])

    def test_livreur_inconnu_reste_404(self):
        self.assertEqual(self.api.get(f'{BASE}/livreurs/999999/stock_van/').status_code, 404)


class VanSansEntrepriseTests(Base):
    """Entrepôt « CENTRAL » sans entreprise partagé par tous les livreurs (production du 28/11)."""

    def setUp(self):
        super().setUp()
        self.central = Warehouse.objects.create(company=None, name='CENTRAL', code='CENTRAL')
        self.livreur.entrepot = self.central
        self.livreur.save()
        UserProfile.objects.update_or_create(user=self.user, defaults={'company': self.co})
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='EAU', designation='Eau', prixU=Decimal('100'),
                                          categorie=cat, company=self.co)
        ProductStock.objects.create(produit=self.eau, warehouse=self.central, quantity=10)
        TypePrix.objects.create(company=self.co, code='DETAIL', libelle='Détail', is_default=True)

    def test_entreprise_du_livreur_depuis_son_compte(self):
        self.assertEqual(company_id_du_livreur(self.livreur), self.co.id)
        self.livreur.entrepot = self.van
        self.assertEqual(company_id_du_livreur(self.livreur), self.co.id)
        sans = LivreurDistribution(matricule='X', nom='X', entrepot=self.central)
        self.assertIsNone(company_id_du_livreur(sans))

    def test_promotion_d_une_autre_entreprise_non_appliquee(self):
        maintenant = timezone.now()
        Promotion.objects.create(code='B50', nom='Promo B', type_promotion='pourcentage',
                                 valeur_pourcentage=Decimal('50'), company=self.co_b, statut='active',
                                 date_debut=maintenant - timedelta(days=1), date_fin=maintenant + timedelta(days=5))
        r = self.api.get(f'{BASE}/livreurs/{self.livreur.id}/stock_van/')
        self.assertEqual(r.status_code, 200, r.content)
        eau = r.json()['stocks'][0]
        self.assertIn('DETAIL', eau['prix_par_type'])   # type de prix de l'entreprise du livreur
        self.assertFalse(any(p['has_promotion'] for p in eau['prix_par_type'].values()), eau['prix_par_type'])
