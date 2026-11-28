"""Signalement client : « les commandes du Prévendeur 1 disparaissent ou se retrouvent sur
l'application d'un autre prévendeur ».

Une commande (ou une vente) arrivée sans livreur était attribuée AUTOMATIQUEMENT au premier
livreur ayant ce client dans ses clients assignés (ventes : aussi planning et tournées du jour).
Règle : aucune affectation automatique. Sans livreur envoyé, c'est le livreur du compte qui
envoie ; sinon personne (affectation à la main au bureau).
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Company, ProductStock, Produit, Warehouse
from .distribution_models import CommandeClient, LivreurDistribution, VenteTourneeMobile

BASE = '/API/distribution'


class SansAffectationAutomatiqueTests(TestCase):
    def setUp(self):
        self.co = Company.objects.create(name='Société A', code='A')
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='EAU', designation='Eau',
                                          prixU=Decimal('10'), categorie=cat, company=self.co)
        self.van1 = Warehouse.objects.create(company=self.co, name='Van 1', code='VAN1')
        self.van2 = Warehouse.objects.create(company=self.co, name='Van 2', code='VAN2')
        ProductStock.objects.create(produit=self.eau, warehouse=self.van1, quantity=20)
        ProductStock.objects.create(produit=self.eau, warehouse=self.van2, quantity=20)
        self.u1 = User.objects.create_user('prev1', password='x')
        self.p1 = LivreurDistribution.objects.create(matricule='P1', nom='Prévendeur 1', telephone='0',
                                                     user=self.u1, entrepot=self.van1)
        self.p2 = LivreurDistribution.objects.create(matricule='P2', nom='Prévendeur 2', telephone='0',
                                                     user=User.objects.create_user('prev2', password='x'),
                                                     entrepot=self.van2)
        self.client_c = Client.objects.create(nom='MINI market', prenom='ahmed', telephone='1', company=self.co)
        self.p2.clients_assignes.add(self.client_c)     # le client est assigné à P2
        self.api = APIClient()
        self.api.force_authenticate(self.u1)            # téléphone de P1

    def _commande(self, app_id, **extra):
        data = {'app_id': app_id, 'client': self.client_c.id, 'notes': '',
                'lignes': [{'produit': self.eau.id, 'quantite': 2, 'prix_unitaire_ht': 10}]}
        data.update(extra)
        return self.api.post(f'{BASE}/commandes/', data, format='json')

    def test_commande_sans_livreur_reste_a_son_auteur(self):
        r = self._commande('cmd-sans-livreur')                      # ancien APK : livreur absent
        self.assertIn(r.status_code, (200, 201), r.content)
        cmd = CommandeClient.objects.get(app_id='cmd-sans-livreur')
        self.assertEqual((cmd.livreur_id, cmd.passee_par_id), (self.p1.id, self.p1.id))
        # Visible chez P1, pas chez P2
        ids_p1 = [c['id'] for c in self.api.get(f'{BASE}/commandes/', {'passee_par': self.p1.id}).json()]
        ids_p2 = [c['id'] for c in self.api.get(f'{BASE}/commandes/', {'passee_par': self.p2.id}).json()]
        self.assertIn(cmd.id, ids_p1)
        self.assertNotIn(cmd.id, ids_p2)

    def test_commande_livreur_null_meme_regle(self):
        r = self._commande('cmd-null', livreur=None)                 # parseInt(null) -> NaN -> null
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertEqual(CommandeClient.objects.get(app_id='cmd-null').livreur_id, self.p1.id)

    def test_commande_du_bureau_sans_livreur_refusee_pas_devinee(self):
        bureau = User.objects.create_user('bureau', password='x', is_staff=True)
        self.api.force_authenticate(bureau)
        r = self._commande('cmd-bureau')
        self.assertEqual(r.status_code, 400, r.content)               # avant : affectée à P2 (client assigné)
        self.assertIn('Précisez le prévendeur', str(r.json()))
        self.assertFalse(CommandeClient.objects.filter(app_id='cmd-bureau').exists())

    def test_vente_sans_livreur_compte_et_stock_de_son_auteur(self):
        r = self.api.post(f'{BASE}/ventes/', {
            'app_id': 'vente-sans-livreur', 'client': str(self.client_c.id), 'livreur': None,
            'mode_paiement': 'especes', 'montant_total': 20, 'montant_paye': 20,
            'lignes_vente': [{'produit': self.eau.id, 'quantite': 2, 'prix_unitaire': 10, 'montant': 20}],
        }, format='json')
        self.assertIn(r.status_code, (200, 201), r.content)
        self.assertTrue(VenteTourneeMobile.objects.filter(app_id='vente-sans-livreur').exists())
        # Stock sorti du van de P1 (auteur), pas de celui de P2 (avant : P2, client assigné)
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.van1).quantity, 18)
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.van2).quantity, 20)
