"""Isolement des données entre entreprises (multi-tenant).

Avant : les administrateurs d'entreprise (is_staff) voyaient les données de TOUTES les
entreprises ; les prix, types de prix, codes de prix, livreurs et l'export des produits n'étaient
filtrés pour personne ; l'import Excel écrasait la fiche d'une autre entreprise portant le même nom ;
choisir son type de prix par défaut retirait celui des autres entreprises."""
import io
from decimal import Decimal

import openpyxl
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (Categorie, Client, CodePrix, Company, Fournisseur, PrixProduit, Produit, TypePrix,
                     UserProfile, Warehouse)
from .distribution_models import LivreurDistribution


def _ids(r):
    d = r.json()
    return {x['id'] for x in (d if isinstance(d, list) else d.get('results', []))}


class IsolementEntreprisesTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(name='Société A', code='A')
        self.b = Company.objects.create(name='Société B', code='B')
        cat_a = Categorie.objects.create(company=self.a, nom='Catégorie A')
        cat_b = Categorie.objects.create(company=self.b, nom='Catégorie B')
        self.prod_a = Produit.objects.create(company=self.a, reference='RA', designation='Produit A', prixU=Decimal('10'), categorie=cat_a)
        self.prod_b = Produit.objects.create(company=self.b, reference='RB', designation='Produit B', prixU=Decimal('10'), categorie=cat_b)
        self.cli_a = Client.objects.create(company=self.a, nom='Client A', prenom='x', telephone='0')
        self.cli_b = Client.objects.create(company=self.b, nom='Client B', prenom='x', telephone='0')
        self.tp_a = TypePrix.objects.create(company=self.a, code='DETAIL', libelle='Détail A', is_default=True)
        self.tp_b = TypePrix.objects.create(company=self.b, code='DETAIL', libelle='Détail B', is_default=True)
        self.tp_partage = TypePrix.objects.create(code='ANCIEN', libelle='Ancien partagé')
        self.cp_b = CodePrix.objects.create(company=self.b, code='STANDARD', libelle='Standard B', is_default=True)
        self.pp_a = PrixProduit.objects.create(produit=self.prod_a, type_prix=self.tp_a, prix=Decimal('9'))
        self.pp_b = PrixProduit.objects.create(produit=self.prod_b, type_prix=self.tp_b, prix=Decimal('9'))
        dep_a = Warehouse.objects.create(company=self.a, name='Dépôt A', code='DA')
        dep_b = Warehouse.objects.create(company=self.b, name='Dépôt B', code='DB')
        self.liv_a = LivreurDistribution.objects.create(matricule='LA', nom='Livreur A', telephone='0', entrepot=dep_a)
        self.liv_b = LivreurDistribution.objects.create(matricule='LB', nom='Livreur B', telephone='0', entrepot=dep_b)
        # Administrateur d'entreprise : is_staff, comme ceux créés depuis l'écran Entreprises
        self.admin_a = User.objects.create_user('admin_a', password='x', is_staff=True)
        UserProfile.objects.update_or_create(user=self.admin_a, defaults={'company': self.a})
        self.web = APIClient()
        self.web.login(username='admin_a', password='x')

    def test_admin_d_entreprise_ne_voit_que_son_entreprise(self):
        for url, a, b in (('/API/produits/', self.prod_a, self.prod_b), ('/API/clients/', self.cli_a, self.cli_b),
                          ('/API/prix-produits/', self.pp_a, self.pp_b),
                          ('/API/distribution/livreurs/', self.liv_a, self.liv_b)):
            ids = _ids(self.web.get(url))
            self.assertIn(a.id, ids, url)
            self.assertNotIn(b.id, ids, url)
        types = _ids(self.web.get('/API/types-prix/'))
        self.assertEqual(types, {self.tp_a.id, self.tp_partage.id})
        self.assertNotIn(self.cp_b.id, _ids(self.web.get('/API/codes-prix/')))

    def test_superutilisateur_voit_tout(self):
        su = User.objects.create_superuser('su', 'su@x.fr', 'x')
        c = APIClient(); c.force_authenticate(su)
        self.assertTrue({self.prod_a.id, self.prod_b.id} <= _ids(c.get('/API/produits/')))

    def test_telephone_jeton_jwt_voit_son_entreprise(self):
        tel = APIClient(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(self.admin_a).access_token))
        ids = _ids(tel.get('/API/produits/'))
        self.assertIn(self.prod_a.id, ids)
        self.assertNotIn(self.prod_b.id, ids)

    def test_livreur_voit_toujours_sa_propre_fiche(self):
        u = User.objects.create_user('livreur_sans_profil', password='x')
        self.liv_b.user = u
        self.liv_b.save()
        c = APIClient(); c.force_authenticate(u)
        self.assertEqual(c.get('/API/distribution/livreurs/me/').status_code, 200)

    def test_export_produits_seulement_mon_entreprise(self):
        r = self.web.get('/API/import/export-products/')
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.content))
        texte = ' '.join(str(c) for row in wb.active.iter_rows(values_only=True) for c in row if c)
        self.assertIn('Produit A', texte)
        self.assertNotIn('Produit B', texte)

    def test_type_de_prix_par_defaut_propre_a_chaque_entreprise(self):
        nouveau = TypePrix.objects.create(company=self.a, code='GROS', libelle='Gros A', is_default=True)
        self.tp_b.refresh_from_db()
        self.tp_a.refresh_from_db()
        self.assertTrue(self.tp_b.is_default)       # avant : retiré à l'entreprise B
        self.assertFalse(self.tp_a.is_default)
        self.assertEqual(TypePrix.get_default(self.a), nouveau)
        self.assertEqual(TypePrix.get_default(self.b), self.tp_b)

    def test_meme_code_possible_dans_deux_entreprises_mais_pas_deux_fois(self):
        r = self.web.post('/API/codes-prix/', {'code': 'STANDARD', 'libelle': 'Standard A'}, format='json')
        self.assertEqual(r.status_code, 201, r.content)   # B a déjà STANDARD : autorisé pour A
        self.assertEqual(CodePrix.objects.get(pk=r.json()['id']).company, self.a)
        r = self.web.post('/API/codes-prix/', {'code': 'standard', 'libelle': 'Doublon'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        r = self.web.post('/API/types-prix/', {'code': 'ANCIEN', 'libelle': 'Doublon du partagé'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)

    def test_prix_refuse_un_produit_ou_type_d_une_autre_entreprise(self):
        r = self.web.post('/API/prix-produits/', {'produit': self.prod_b.id, 'type_prix': self.tp_a.id, 'prix': '5'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        r = self.web.post('/API/prix-produits/', {'produit': self.prod_a.id, 'type_prix': self.tp_b.id, 'prix': '5'}, format='json')
        self.assertEqual(r.status_code, 400, r.content)

    def _import(self, type_import, lignes):
        wb = openpyxl.Workbook()
        for ligne in lignes:
            wb.active.append(ligne)
        buf = io.BytesIO()
        wb.save(buf)
        f = SimpleUploadedFile('i.xlsx', buf.getvalue(),
                               content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        return self.web.post('/API/import/execute/', {'file': f, 'type': type_import}, format='multipart')

    def test_import_n_ecrase_pas_la_fiche_d_une_autre_entreprise(self):
        Categorie.objects.create(company=self.b, nom='Boissons')
        Fournisseur.objects.create(company=self.b, libelle='Fournisseur commun', telephone='0')
        r = self._import('clients', [['nom', 'prenom', 'telephone'], ['Client B', 'x', '0555']])
        self.assertEqual(r.status_code, 200, r.content)
        self.cli_b.refresh_from_db()
        self.assertEqual((self.cli_b.company, self.cli_b.telephone), (self.b, '0'))   # intacte
        self.assertTrue(Client.objects.filter(company=self.a, nom='Client B').exists())
        self._import('categories', [['nom'], ['Boissons']])
        self.assertEqual(Categorie.objects.filter(nom='Boissons').count(), 2)
        self._import('fournisseurs', [['libelle', 'telephone'], ['Fournisseur commun', '0']])
        self.assertEqual(Fournisseur.objects.filter(libelle='Fournisseur commun', company=self.b).count(), 1)

    def test_import_prix_ne_touche_pas_les_produits_d_une_autre_entreprise(self):
        r = self._import('pricelists', [['reference', 'prix', 'type_prix'], ['RB', '1', 'DETAIL']])
        self.assertEqual(r.status_code, 200, r.content)
        self.pp_b.refresh_from_db()
        self.assertEqual(self.pp_b.prix, Decimal('9'))
        self.assertFalse(PrixProduit.objects.filter(produit=self.prod_b, prix=Decimal('1')).exists())
