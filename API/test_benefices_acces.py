"""Sécurisation du tableau de bord des bénéfices : administrateur de l'entreprise + code PIN."""
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import AccesTableauBenefices, Categorie, Company, Produit, UserProfile
from . import benefices_acces

URL_DATA = '/API/reports/profit-data/'
URL_EXPORT_API = '/API/reports/profit/'
URL_EXPORT_SITE = '/reports/profit/'
URL_ACCES = '/API/reports/benefices/acces/'
URL_OUVRIR = '/API/reports/benefices/deverrouiller/'
URL_FERMER = '/API/reports/benefices/verrouiller/'
URL_PIN = '/API/reports/benefices/pin/'


class BeneficesAccesTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(name='Entreprise A', code='ENTA')
        self.b = Company.objects.create(name='Entreprise B', code='ENTB')
        self.admin_a = self.user('admin_a', self.a, 'admin')
        self.admin_a2 = self.user('admin_a2', self.a, 'admin')
        self.employe_a = self.user('employe_a', self.a, 'employee')
        self.admin_b = self.user('admin_b', self.b, 'admin')
        cat = Categorie.objects.create(nom='Divers')
        Produit.objects.create(reference='PA', code_barre='1', designation='Produit A', prixU=Decimal('10'), company=self.a, categorie=cat)
        Produit.objects.create(reference='PB', code_barre='2', designation='Produit B', prixU=Decimal('10'), company=self.b, categorie=cat)

    def user(self, nom, company, role, staff=False):
        u = User.objects.create_user(nom, password='mdp-test', is_staff=staff)
        UserProfile.objects.update_or_create(user=u, defaults={'company': company, 'role': role})
        return u

    def client_de(self, user):
        c = APIClient()
        c.login(username=user.username, password='mdp-test')
        return c

    def definir(self, c, pin='4821'):
        return c.post(URL_PIN, {'pin': pin, 'confirmation': pin}, format='json')

    # ---------------------------------------------------------------- droits
    def test_non_admin_refuse_partout(self):
        employe = self.client_de(self.employe_a)
        self.assertEqual(employe.get(URL_ACCES).json(), {'admin': False})
        for url in (URL_DATA, URL_EXPORT_API, URL_EXPORT_SITE):
            self.assertEqual(employe.get(url).status_code, 403, url)
        self.assertEqual(self.definir(employe).status_code, 403)
        page = employe.get('/page/rapport_benefices/')
        self.assertContains(page, 'réservé à l&#x27;administrateur', html=False) if b'&#x27;' in page.content else self.assertContains(page, 'Accès réservé')
        self.assertNotContains(page, 'profit-table-container')   # pas le tableau, juste le message

    def test_staff_sans_role_admin_refuse(self):
        staff = self.user('staff_a', self.a, 'employee', staff=True)
        self.assertEqual(self.client_de(staff).get(URL_DATA).status_code, 403)

    def test_anonyme_refuse(self):
        self.assertIn(APIClient().get(URL_DATA).status_code, (401, 403))

    # ---------------------------------------------------------------- PIN
    def test_admin_sans_pin_doit_le_choisir_avant_les_donnees(self):
        c = self.client_de(self.admin_a)
        etat = c.get(URL_ACCES).json()
        self.assertEqual((etat['admin'], etat['pin_defini'], etat['deverrouille']), (True, False, False))
        r = c.get(URL_DATA)
        self.assertEqual((r.status_code, r.json()['raison']), (403, 'pin_requis'))
        self.assertEqual(self.definir(c).status_code, 200)
        self.assertEqual(c.get(URL_DATA).status_code, 200)

    def test_pin_stocke_chiffre(self):
        self.definir(self.client_de(self.admin_a), '4821')
        h = AccesTableauBenefices.objects.get(company=self.a).pin_hash
        self.assertNotIn('4821', h)
        self.assertTrue(h.startswith(('pbkdf2', 'argon2', 'bcrypt', 'scrypt', 'md5')))

    def test_format_et_confirmation(self):
        c = self.client_de(self.admin_a)
        self.assertEqual(c.post(URL_PIN, {'pin': '12', 'confirmation': '12'}, format='json').status_code, 400)
        self.assertEqual(c.post(URL_PIN, {'pin': 'abcd', 'confirmation': 'abcd'}, format='json').status_code, 400)
        self.assertEqual(c.post(URL_PIN, {'pin': '1234', 'confirmation': '1235'}, format='json').status_code, 400)

    def test_pin_commun_aux_admins_de_l_entreprise(self):
        self.definir(self.client_de(self.admin_a), '4821')
        autre = self.client_de(self.admin_a2)
        self.assertTrue(autre.get(URL_ACCES).json()['pin_defini'])
        self.assertEqual(autre.get(URL_DATA).status_code, 403)          # sa session n'est pas ouverte
        self.assertEqual(autre.post(URL_OUVRIR, {'pin': '4821'}, format='json').status_code, 200)
        self.assertEqual(autre.get(URL_DATA).status_code, 200)

    def test_mauvais_pin_puis_blocage(self):
        self.definir(self.client_de(self.admin_a), '4821')
        c = self.client_de(self.admin_a2)
        for i in range(4):
            r = c.post(URL_OUVRIR, {'pin': '0000'}, format='json')
            self.assertEqual(r.status_code, 403)
            self.assertIn(f'Il reste {4 - i} essai', r.json()['detail'])
        r = c.post(URL_OUVRIR, {'pin': '0000'}, format='json')
        self.assertEqual((r.status_code, r.json()['raison']), (429, 'bloque'))
        # Même le bon PIN est refusé pendant le blocage
        self.assertEqual(c.post(URL_OUVRIR, {'pin': '4821'}, format='json').status_code, 429)
        # Après le blocage, le bon PIN passe
        plus_tard = timezone.now() + timedelta(minutes=16)
        with mock.patch.object(benefices_acces, '_maintenant', return_value=plus_tard):
            self.assertEqual(c.post(URL_OUVRIR, {'pin': '4821'}, format='json').status_code, 200)

    def test_changement_exige_le_pin_actuel(self):
        c = self.client_de(self.admin_a)
        self.definir(c, '4821')
        self.assertEqual(c.post(URL_PIN, {'pin': '9999', 'confirmation': '9999'}, format='json').status_code, 403)
        self.assertEqual(c.post(URL_PIN, {'pin': '9999', 'confirmation': '9999', 'pin_actuel': '1111'}, format='json').status_code, 403)
        self.assertEqual(c.post(URL_PIN, {'pin': '9999', 'confirmation': '9999', 'pin_actuel': '4821'}, format='json').status_code, 200)
        autre = self.client_de(self.admin_a2)
        self.assertEqual(autre.post(URL_OUVRIR, {'pin': '4821'}, format='json').status_code, 403)
        self.assertEqual(autre.post(URL_OUVRIR, {'pin': '9999'}, format='json').status_code, 200)

    def test_verrouiller_et_expiration(self):
        c = self.client_de(self.admin_a)
        self.definir(c)
        self.assertEqual(c.get(URL_DATA).status_code, 200)
        c.post(URL_FERMER, {}, format='json')
        self.assertEqual(c.get(URL_DATA).status_code, 403)
        c.post(URL_OUVRIR, {'pin': '4821'}, format='json')
        plus_tard = timezone.now() + timedelta(minutes=16)
        with mock.patch.object(benefices_acces, '_maintenant', return_value=plus_tard):
            self.assertEqual(c.get(URL_DATA).status_code, 403)

    def test_session_d_une_autre_entreprise_inutilisable(self):
        """Le PIN de A n'ouvre rien chez B, et B a son propre PIN."""
        self.definir(self.client_de(self.admin_a), '4821')
        b = self.client_de(self.admin_b)
        self.assertFalse(b.get(URL_ACCES).json()['pin_defini'])
        self.assertEqual(b.post(URL_OUVRIR, {'pin': '4821'}, format='json').status_code, 400)  # aucun PIN chez B

    # ---------------------------------------------------------------- données
    def test_donnees_limitees_a_l_entreprise(self):
        c = self.client_de(self.admin_a)
        self.definir(c)
        refs = [p['reference'] for p in c.get(URL_DATA).json()['products']]
        self.assertIn('PA', refs)
        self.assertNotIn('PB', refs)

    def test_exports_ouverts_apres_pin(self):
        c = self.client_de(self.admin_a)
        self.definir(c)
        # NB : sur l'API, `format` est réservé par DRF (404) ; sans paramètre l'export est en Excel
        self.assertEqual(c.get(URL_EXPORT_API).status_code, 200)
        self.assertEqual(c.get(URL_EXPORT_SITE, {'format': 'pdf'}).status_code, 200)
        self.assertEqual(self.client_de(self.admin_a).get('/page/rapport_benefices/').status_code, 200)
        self.assertEqual(c.get(URL_EXPORT_SITE, {'format': 'excel'}).status_code, 200)

    def test_page_pose_le_cookie_csrf_et_le_pin_passe_avec(self):
        """Comme le navigateur : contrôle CSRF actif, le jeton vient de l'appel d'état."""
        c = APIClient(enforce_csrf_checks=True)
        c.login(username='admin_a', password='mdp-test')
        self.assertEqual(c.post(URL_PIN, {'pin': '4821', 'confirmation': '4821'}, format='json').status_code, 403)
        c.get(URL_ACCES)
        token = c.cookies['csrftoken'].value
        r = c.post(URL_PIN, {'pin': '4821', 'confirmation': '4821'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)
