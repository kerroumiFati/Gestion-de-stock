"""Tests : entrepôt de départ d'une tournée (enregistrement, détail, report sur le livreur)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .distribution_models import LivreurDistribution, TourneeMobile
from .models import Warehouse

User = get_user_model()


class TourneeEntrepotDepartTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_t', 'a@t.dz', 'pass')
        self.van_a = Warehouse.objects.create(code='VAN-A', name='Van A')
        self.van_b = Warehouse.objects.create(code='VAN-B', name='Van B')
        self.livreur = LivreurDistribution.objects.create(
            matricule='LIV-T1', nom='Livreur Test', telephone='0550000000',
            entrepot=self.van_a,
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.admin)

    def _payload(self, **extra):
        data = {
            'date_tournee': '2026-10-05',
            'numero_tournee': 'T-TEST-0001',
            'livreur': self.livreur.id,
            'statut': 'planifiee',
            'notes': '',
        }
        data.update(extra)
        return data

    def test_creation_enregistre_entrepot_et_met_a_jour_le_livreur(self):
        r = self.client_api.post('/API/tournees/', self._payload(warehouse=self.van_b.id), format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['warehouse'], self.van_b.id)

        self.livreur.refresh_from_db()
        self.assertEqual(self.livreur.entrepot_id, self.van_b.id)

    def test_detail_affiche_entrepot(self):
        r = self.client_api.post('/API/tournees/', self._payload(warehouse=self.van_b.id), format='json')
        detail = self.client_api.get('/API/tournees/%s/' % r.json()['id']).json()
        self.assertEqual(detail['warehouse'], self.van_b.id)
        self.assertEqual(detail['warehouse_nom'], 'Van B')
        self.assertEqual(detail['warehouse_code'], 'VAN-B')

    def test_creation_sans_entrepot_reprend_celui_du_livreur(self):
        r = self.client_api.post('/API/tournees/', self._payload(warehouse=None), format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()['warehouse'], self.van_a.id)
        self.livreur.refresh_from_db()
        self.assertEqual(self.livreur.entrepot_id, self.van_a.id)

    def test_modification_change_entrepot_et_livreur(self):
        r = self.client_api.post('/API/tournees/', self._payload(warehouse=self.van_a.id), format='json')
        tid = r.json()['id']
        r2 = self.client_api.put('/API/tournees/%s/' % tid, self._payload(warehouse=self.van_b.id), format='json')
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.json()['warehouse_nom'], 'Van B')
        self.livreur.refresh_from_db()
        self.assertEqual(self.livreur.entrepot_id, self.van_b.id)

    def test_modification_sans_entrepot_conserve_celui_enregistre(self):
        r = self.client_api.post('/API/tournees/', self._payload(warehouse=self.van_b.id), format='json')
        tid = r.json()['id']
        r2 = self.client_api.put('/API/tournees/%s/' % tid, self._payload(warehouse=None), format='json')
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.json()['warehouse'], self.van_b.id)

    def test_tournee_terminee_ne_change_pas_le_van_du_livreur(self):
        tournee = TourneeMobile.objects.create(
            livreur=self.livreur, date_tournee='2026-09-01',
            numero_tournee='T-OLD-1', statut='terminee', entrepot_depart=self.van_a,
        )
        payload = self._payload(date_tournee='2026-09-01', numero_tournee='T-OLD-1',
                                statut='terminee', warehouse=self.van_b.id)
        r = self.client_api.put('/API/tournees/%s/' % tournee.id, payload, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['warehouse'], self.van_b.id)
        self.livreur.refresh_from_db()
        self.assertEqual(self.livreur.entrepot_id, self.van_a.id)
