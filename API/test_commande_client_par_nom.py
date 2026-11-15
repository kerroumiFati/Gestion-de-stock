"""Création d'une commande depuis l'app mobile pour un client créé sur le téléphone.

L'app envoie alors client=null, app_client_id=<id local> et client_nom="prénom nom".
Le serveur doit retrouver le client sur son nom COMPLET (jamais approximatif).
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Produit
from .distribution_models import CommandeClient, LivreurDistribution

URL = '/API/distribution/commandes/'


class CommandeClientParNomTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau',
                                          prixU=Decimal('10'), categorie=cat)
        self.user = User.objects.create_user('vendeur', password='x')
        self.livreur = LivreurDistribution.objects.create(matricule='V1', nom='Ahmed', telephone='0', user=self.user)
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def _post(self, client_nom, app_id='cmd-1'):
        return self.api.post(URL, {
            'app_id': app_id, 'client': None, 'app_client_id': 'client_1700000000_abc',
            'client_nom': client_nom, 'livreur': self.livreur.id,
            'lignes': [{'produit': self.eau.id, 'quantite': 2, 'prix_unitaire_ht': '10'}],
        }, format='json')

    def test_client_trouve_par_prenom_et_nom(self):
        c = Client.objects.create(nom='Boudiaf', prenom='Samira', telephone='0', adresse='Oran')
        r = self._post('Samira Boudiaf')
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertEqual(CommandeClient.objects.get().client_id, c.id)

    def test_insensible_a_la_casse_et_aux_espaces(self):
        c = Client.objects.create(nom='Boudiaf', prenom='Samira', telephone='0', adresse='Oran')
        r = self._post('  samira   BOUDIAF ')
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertEqual(CommandeClient.objects.get().client_id, c.id)

    def test_pas_de_correspondance_approximative(self):
        # Avant : recherche « contient le dernier mot » -> commande sur un autre client
        Client.objects.create(nom='Boudiaf', prenom='Karim', telephone='0', adresse='Oran')
        r = self._post('Samira Boudiaf')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(CommandeClient.objects.count(), 0)

    def test_homonymes_departages_par_le_livreur(self):
        Client.objects.create(nom='Boudiaf', prenom='Samira', telephone='1', adresse='Oran')
        le_bon = Client.objects.create(nom='Boudiaf', prenom='Samira', telephone='2', adresse='Alger')
        self.livreur.clients_assignes.add(le_bon)
        r = self._post('Samira Boudiaf')
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertEqual(CommandeClient.objects.get().client_id, le_bon.id)

    def test_homonymes_non_departages_refuses(self):
        Client.objects.create(nom='Boudiaf', prenom='Samira', telephone='1', adresse='Oran')
        Client.objects.create(nom='Boudiaf', prenom='Samira', telephone='2', adresse='Alger')
        r = self._post('Samira Boudiaf')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(CommandeClient.objects.count(), 0)

    def test_client_absent_refuse_proprement(self):
        r = self._post('Inconnu Total')
        self.assertEqual(r.status_code, 400, r.content)   # avant : 500 (ImportError)
