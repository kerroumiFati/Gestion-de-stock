"""Tests du journal d'audit lisible (/API/audit-journal/)."""
import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AuditLog


class AuditJournalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin_au', password='x', is_staff=True,
                                              first_name='Karim', last_name='B')
        self.user = User.objects.create_user('simple_au', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        AuditLog.objects.create(actor=self.admin, action='produit.delete', target_repr='Coca 1L',
                                metadata=json.dumps({'reference': 'COCA'}),
                                user_agent='Mozilla/5.0 (Windows NT 10.0) Chrome/120.0 Safari/537')
        AuditLog.objects.create(actor=None, action='client.create', target_repr='Boutique')
        AuditLog.objects.create(actor=self.admin, action='report.export_sales')

    def test_libelles_lisibles(self):
        r = self.client.get('/API/audit-journal/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 3)
        par_action = {x['action']: x for x in r.data['results']}
        p = par_action['produit.delete']
        self.assertEqual(p['action_label'], 'Produit supprimé (désactivé)')
        self.assertEqual(p['categorie'], 'delete')
        self.assertEqual(p['acteur'], 'Karim B')
        self.assertEqual(p['details'], [{'label': 'Référence', 'valeur': 'COCA'}])
        self.assertEqual(p['appareil'], 'Chrome · Windows')
        self.assertEqual(par_action['client.create']['action_label'], 'Création — Clients')
        self.assertEqual(par_action['client.create']['acteur'], 'Système')
        self.assertEqual(par_action['report.export_sales']['categorie'], 'export')
        self.assertEqual(r.data['stats']['suppressions'], 1)

    def test_filtres(self):
        self.assertEqual(self.client.get('/API/audit-journal/?module=produit').data['count'], 1)
        self.assertEqual(self.client.get('/API/audit-journal/?acteur=systeme').data['count'], 1)
        self.assertEqual(self.client.get('/API/audit-journal/?q=coca').data['count'], 1)
        self.assertEqual(self.client.get('/API/audit-journal/?date_debut=2000-01-01&date_fin=2000-01-02').data['count'], 0)

    def test_pagination(self):
        r = self.client.get('/API/audit-journal/?page_size=10&page=5')
        self.assertEqual(r.data['page'], 1)  # page bornée
        self.assertEqual(r.data['pages'], 1)

    def test_listes_de_filtres(self):
        r = self.client.get('/API/audit-journal/filtres/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('produit', [m['value'] for m in r.data['modules']])
        self.assertEqual(r.data['acteurs'][0]['label'], 'Karim B')

    def test_export_csv(self):
        r = self.client.get('/API/audit-journal/?export=csv')
        self.assertEqual(r.status_code, 200)
        contenu = r.content.decode('utf-8-sig')
        self.assertIn('Produit supprimé (désactivé)', contenu)

    def test_reserve_aux_administrateurs(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get('/API/audit-journal/').status_code, 403)
        self.assertEqual(self.client.get('/API/audit-journal/filtres/').status_code, 403)
