"""Historique des quantités d'une commande client : quantité commandée au départ, quantité juste
avant la livraison (après les modifications), quantité livrée, et produits retirés après la commande.
Affiché dans Rapports & Analyses → Récapitulatif des commandes → Tableau détaillé."""
from datetime import date
from decimal import Decimal
from importlib import import_module

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Produit, ProductStock, Warehouse
from .distribution_models import CommandeClient, LigneCommandeClient, LivreurDistribution, TourneeMobile

migration = import_module('API.migrations.0099_historique_quantites_commande')


class HistoriqueQuantitesTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau', prixU=Decimal('10'), categorie=cat)
        self.jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus', prixU=Decimal('20'), categorie=cat)
        self.chips = Produit.objects.create(reference='CHIPS', code_barre='3', designation='Chips', prixU=Decimal('5'), categorie=cat)
        self.van = Warehouse.objects.create(name='Van 1', code='VAN1')
        for p in (self.eau, self.jus, self.chips):
            ProductStock.objects.create(produit=p, warehouse=self.van, quantity=100)
        self.user = User.objects.create_user('livreur', password='x')
        self.livreur = LivreurDistribution.objects.create(matricule='L1', nom='Ahmed', telephone='0', user=self.user,
                                                          entrepot=self.van)
        self.tournee = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=date.today(),
                                                    numero_tournee='T1', statut='en_cours')
        self.client_ = Client.objects.create(nom='Client', prenom='Test', telephone='0')
        self.commande = CommandeClient.objects.create(client=self.client_, livreur=self.livreur, reference='CMD-1')
        LigneCommandeClient.objects.create(commande=self.commande, produit=self.eau, quantite=10,
                                           prix_unitaire_ht=Decimal('10'), taux_tva=0)
        LigneCommandeClient.objects.create(commande=self.commande, produit=self.chips, quantite=5,
                                           prix_unitaire_ht=Decimal('5'), taux_tva=0)
        self.commande.calculer_totaux()
        self.tel = APIClient()
        self.tel.force_authenticate(self.user)
        self.pc = APIClient()
        self.pc.force_authenticate(User.objects.create_user('bureau', password='x', is_staff=True, is_superuser=True))

    def ligne(self, produit):
        return LigneCommandeClient.objects.get(commande=self.commande, produit=produit)

    def modifier(self, lignes):
        r = self.tel.post('/API/distribution/commandes/modifier_lignes/', {'id': self.commande.id, 'lignes': lignes},
                          format='json')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def livrer(self, lignes=None):
        data = {'statut': 'delivered', 'tournee_livraison': self.tournee.id}
        if lignes is not None:
            data['lignes'] = lignes
        r = self.tel.patch(f'/API/distribution/commandes/{self.commande.id}/', data, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_creation_quantite_commandee(self):
        self.assertEqual(self.ligne(self.eau).quantite_commandee, Decimal('10'))
        self.assertIsNone(self.ligne(self.eau).quantite_livree)

    def test_modifiee_puis_livree_garde_les_trois_quantites(self):
        # Eau 10 -> 8, Jus ajouté (3), Chips retiré
        self.modifier([{'produit': self.eau.id, 'quantite': 8}, {'produit': self.jus.id, 'quantite': 3}])
        eau, jus = self.ligne(self.eau), self.ligne(self.jus)
        self.assertEqual((eau.quantite_commandee, eau.quantite), (Decimal('10'), Decimal('8')))
        self.assertEqual(jus.quantite_commandee, Decimal('0'))                  # ajouté après la commande
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.lignes_retirees,
                         [{'produit': self.chips.id, 'designation': 'Chips', 'reference': 'CHIPS', 'quantite_commandee': '5.00'}])
        # Livraison : 7 eaux au lieu de 8
        data = self.livrer([{'produit': self.eau.id, 'quantite': 7}, {'produit': self.jus.id, 'quantite': 3}])
        eau = self.ligne(self.eau)
        self.assertEqual((eau.quantite_commandee, eau.quantite_avant_livraison, eau.quantite_livree, eau.quantite),
                         (Decimal('10'), Decimal('8'), Decimal('7'), Decimal('7')))
        self.assertEqual(self.ligne(self.jus).quantite_livree, Decimal('3'))
        # L'API renvoie l'historique et les produits retirés (avec les unités par carton)
        l_eau = [l for l in data['lignes'] if l['produit'] == self.eau.id][0]
        self.assertEqual((l_eau['quantite_commandee'], l_eau['quantite_avant_livraison'], l_eau['quantite_livree']),
                         ('10.00', '8.00', '7.00'))
        self.assertEqual(data['lignes_retirees'][0]['designation'], 'Chips')
        self.assertEqual(data['lignes_retirees'][0]['produit_unites_par_carton'], 1)

    def test_livraison_sans_changement(self):
        self.livrer()
        eau = self.ligne(self.eau)
        self.assertEqual((eau.quantite_commandee, eau.quantite_avant_livraison, eau.quantite_livree),
                         (Decimal('10'), Decimal('10'), Decimal('10')))

    def test_produit_retire_puis_remis_retrouve_sa_quantite_commandee(self):
        self.modifier([{'produit': self.eau.id, 'quantite': 10}])                              # chips retiré
        self.modifier([{'produit': self.eau.id, 'quantite': 10}, {'produit': self.chips.id, 'quantite': 2}])
        self.assertEqual(self.ligne(self.chips).quantite_commandee, Decimal('5'))
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.lignes_retirees, [])

    def test_produit_ajoute_puis_retire_n_est_pas_garde(self):
        self.modifier([{'produit': self.eau.id, 'quantite': 10}, {'produit': self.chips.id, 'quantite': 5},
                       {'produit': self.jus.id, 'quantite': 1}])
        self.modifier([{'produit': self.eau.id, 'quantite': 10}, {'produit': self.chips.id, 'quantite': 5}])
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.lignes_retirees, [])

    def test_modification_depuis_le_site_garde_les_quantites_commandees(self):
        r = self.pc.patch(f'/API/distribution/commandes/{self.commande.id}/', {
            'lignes': [{'produit': self.eau.id, 'quantite': 6, 'prix_unitaire_ht': '10'},
                       {'produit': self.jus.id, 'quantite': 2, 'prix_unitaire_ht': '20'}]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual((self.ligne(self.eau).quantite_commandee, self.ligne(self.eau).quantite), (Decimal('10'), Decimal('6')))
        self.assertEqual(self.ligne(self.jus).quantite_commandee, Decimal('0'))
        self.commande.refresh_from_db()
        self.assertEqual([r['designation'] for r in self.commande.lignes_retirees], ['Chips'])

    def test_lecture_des_traces_pour_la_reprise(self):
        notes = ('[01/11/2026 10:00] Modifiée par ali : Eau 12→10, +Jus x3, -Chips\n'
                 '[02/11/2026 09:00] Modifiée par ali : Eau 10→8, Jus 3→4, notes modifiées')
        self.assertEqual(migration.premiers_evenements(notes), {
            'Eau': ('change', Decimal('12')), 'Jus': ('ajout', None), 'Chips': ('retrait', None)})
