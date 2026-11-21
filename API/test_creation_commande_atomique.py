"""Une commande envoyée par le téléphone est créée EN ENTIER ou PAS DU TOUT
(POST /API/distribution/commandes/)."""
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Produit
from .distribution_models import CommandeClient, LigneCommandeClient, LivreurDistribution

URL = '/API/distribution/commandes/'


class CreationCommandeAtomiqueTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau', prixU=Decimal('10'), categorie=cat)
        self.jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus', prixU=Decimal('20'), categorie=cat)
        user = User.objects.create_user('vendeur', password='x')
        self.vendeur = LivreurDistribution.objects.create(matricule='V1', nom='Ahmed', telephone='0', user=user)
        self.client_ = Client.objects.create(nom='Client', prenom='Test', telephone='0')
        self.api = APIClient()
        self.api.force_authenticate(user)
        self.payload = {
            'app_id': 'commande-999-1', 'client': self.client_.id, 'livreur': self.vendeur.id,
            'lignes': [{'produit': self.eau.id, 'quantite': 3, 'prix_unitaire_ht': '10'},
                       {'produit': self.jus.id, 'quantite': 2, 'prix_unitaire_ht': '20'}],
            'type_paiement': 'especes', 'montant_paye': '30', 'est_paye': False,
        }

    def test_panne_pendant_les_lignes_rien_n_est_enregistre_puis_renvoi_complet(self):
        vrai_create = LigneCommandeClient.objects.create
        appels = {'n': 0}

        def create_en_panne(*a, **kw):
            appels['n'] += 1
            if appels['n'] == 2:          # panne sur la 2e ligne
                raise RuntimeError('panne simulée')
            return vrai_create(*a, **kw)

        with mock.patch.object(LigneCommandeClient.objects, 'create', side_effect=create_en_panne):
            r = self.api.post(URL, self.payload, format='json')
        self.assertGreaterEqual(r.status_code, 400)
        # Avant : une commande avec 1 seule ligne restait, et le renvoi répondait « déjà reçue »
        self.assertFalse(CommandeClient.objects.filter(app_id='commande-999-1').exists())
        self.assertEqual(LigneCommandeClient.objects.count(), 0)

        # Le téléphone renvoie (élément toujours dans sa file) : commande complète
        r = self.api.post(URL, self.payload, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        commande = CommandeClient.objects.get(app_id='commande-999-1')
        self.assertEqual(commande.lignes.count(), 2)
        self.assertEqual(commande.montant_total_ttc, Decimal('70'))
        self.assertEqual(commande.montant_paye, Decimal('30'))

        # Second renvoi (réponse perdue) : pas de doublon
        r = self.api.post(URL, self.payload, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(CommandeClient.objects.filter(app_id='commande-999-1').count(), 1)
