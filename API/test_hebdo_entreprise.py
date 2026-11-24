"""Affectations clients/prévendeurs (/API/distribution/clients-livreurs-hebdo/) : chaque entreprise
ne voit et ne modifie que ses livreurs, ses clients et ses affectations — liste, modèle Excel et
import compris. Avant : filtre sur request.user.company (inexistant) -> toutes les entreprises."""
import io

import openpyxl
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client, Company, UserProfile, Warehouse
from .distribution_models import ClientLivreurHebdo, LivreurDistribution

URL = '/API/distribution/clients-livreurs-hebdo/'


class HebdoEntrepriseTests(TestCase):
    def setUp(self):
        self.a = Company.objects.create(name='Société A', code='A')
        self.b = Company.objects.create(name='Société B', code='B')
        depot_a = Warehouse.objects.create(company=self.a, name='Camion A', code='CA')
        depot_b = Warehouse.objects.create(company=self.b, name='Camion B', code='CB')
        self.liv_a = LivreurDistribution.objects.create(matricule='LA', nom='Livreur A', telephone='0', entrepot=depot_a)
        self.liv_b = LivreurDistribution.objects.create(matricule='LB', nom='Livreur B', telephone='0', entrepot=depot_b)
        self.cli_a = Client.objects.create(company=self.a, nom='Client A', prenom='x', telephone='0')
        self.cli_a2 = Client.objects.create(company=self.a, nom='Client A2', prenom='x', telephone='0')
        self.cli_b = Client.objects.create(company=self.b, nom='Client B', prenom='x', telephone='0')
        self.h_a = ClientLivreurHebdo.objects.create(client=self.cli_a, livreur=self.liv_a, jour_semaine=1, company=self.a)
        # ancienne ligne sans entreprise (créée avant la correction) : rattachée par le client
        self.h_a_ancien = ClientLivreurHebdo.objects.create(client=self.cli_a2, livreur=self.liv_a, jour_semaine=2)
        self.h_b = ClientLivreurHebdo.objects.create(client=self.cli_b, livreur=self.liv_b, jour_semaine=1, company=self.b)
        user = User.objects.create_user('bureau_a', password='x', is_staff=True)
        UserProfile.objects.update_or_create(user=user, defaults={'company': self.a})
        self.web = APIClient()
        self.web.login(username='bureau_a', password='x')   # session : le middleware pose request.company

    def _ids(self, r):
        self.assertEqual(r.status_code, 200, r.content)
        d = r.json()
        return {x['id'] for x in (d if isinstance(d, list) else d.get('results', []))}

    def test_liste_seulement_mon_entreprise(self):
        self.assertEqual(self._ids(self.web.get(URL)), {self.h_a.id, self.h_a_ancien.id})

    def test_authentification_par_jeton_filtre_aussi(self):
        tel = APIClient()
        tel.force_authenticate(User.objects.get(username='bureau_a'))
        self.assertEqual(self._ids(tel.get(URL)), {self.h_a.id, self.h_a_ancien.id})

    def test_creation_refuse_un_client_d_une_autre_entreprise(self):
        r = self.web.post(URL, {'client': self.cli_b.id, 'livreur': self.liv_a.id, 'jour_semaine': 3}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        r = self.web.post(URL, {'client': self.cli_a.id, 'livreur': self.liv_b.id, 'jour_semaine': 3}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        r = self.web.post(URL, {'client': self.cli_a.id, 'livreur': self.liv_a.id, 'jour_semaine': 3}, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(ClientLivreurHebdo.objects.get(client=self.cli_a, jour_semaine=3).company, self.a)

    def test_modele_excel_sans_les_donnees_des_autres(self):
        r = self.web.get(URL + 'template-excel/')
        self.assertEqual(r.status_code, 200)
        wb = openpyxl.load_workbook(io.BytesIO(r.content), data_only=True)
        texte = ' '.join(str(c) for ws in wb.worksheets for row in ws.iter_rows(values_only=True) for c in row if c)
        self.assertIn('Livreur A', texte)
        self.assertIn('Client A', texte)
        self.assertNotIn('Livreur B', texte)
        self.assertNotIn('Client B', texte)

    def _fichier(self, lignes):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['Livreur ID', 'Livreur', 'Client ID', 'Client', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'])
        for ligne in lignes:
            ws.append(ligne)
        buf = io.BytesIO()
        wb.save(buf)
        return SimpleUploadedFile('import.xlsx', buf.getvalue(),
                                  content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_import_refuse_les_ids_d_une_autre_entreprise(self):
        f = self._fichier([[self.liv_a.id, '', self.cli_b.id, '', 'X'],
                           [self.liv_b.id, '', self.cli_a.id, '', 'X']])
        r = self.web.post(URL + 'import-excel/', {'file': f}, format='multipart')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(len(r.json().get('errors') or []), 2, r.content)
        self.assertFalse(ClientLivreurHebdo.objects.filter(client=self.cli_b, livreur=self.liv_a).exists())
        self.assertFalse(ClientLivreurHebdo.objects.filter(client=self.cli_a, livreur=self.liv_b).exists())

    def test_import_met_a_jour_la_ligne_existante_sans_doublon(self):
        # Mercredi : ancienne ligne sans entreprise -> mise à jour (et rattachée), pas de 2e ligne
        f = self._fichier([[self.liv_a.id, '', self.cli_a2.id, '', '', 'X']])
        r = self.web.post(URL + 'import-excel/', {'file': f}, format='multipart')
        self.assertEqual(r.status_code, 200, r.content)
        lignes = ClientLivreurHebdo.objects.filter(client=self.cli_a2, jour_semaine=2)
        self.assertEqual(lignes.count(), 1)
        self.assertEqual(lignes.get().company, self.a)
