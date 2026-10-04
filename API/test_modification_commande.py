"""Tests de la modification d'une commande depuis l'application mobile
(POST /API/distribution/commandes/modifier_lignes/)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Produit
from .distribution_models import CommandeClient, LigneCommandeClient, LivreurDistribution

URL = '/API/distribution/commandes/modifier_lignes/'


class ModificationCommandeTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau', prixU=Decimal('10'), categorie=cat)
        self.jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus', prixU=Decimal('20'), categorie=cat)
        self.chips = Produit.objects.create(reference='CHIPS', code_barre='3', designation='Chips', prixU=Decimal('5'), categorie=cat)
        self.inactif = Produit.objects.create(reference='OLD', code_barre='4', designation='Ancien', prixU=Decimal('5'),
                                              categorie=cat, is_active=False)
        self.user = User.objects.create_user('vendeur', password='x')
        self.vendeur = LivreurDistribution.objects.create(matricule='V1', nom='Ahmed', telephone='0', user=self.user)
        self.client_ = Client.objects.create(nom='Client', prenom='Test', telephone='0')
        self.commande = CommandeClient.objects.create(client=self.client_, livreur=self.vendeur, reference='CMD-1',
                                                      app_id='commande-123-1')
        # Eau : prix negocie 8 (different du prix catalogue 10), 12 unites ; Chips : 4 unites
        LigneCommandeClient.objects.create(commande=self.commande, produit=self.eau, quantite=12,
                                           prix_unitaire_ht=Decimal('8'), taux_tva=0)
        LigneCommandeClient.objects.create(commande=self.commande, produit=self.chips, quantite=4,
                                           prix_unitaire_ht=Decimal('5'), taux_tva=0)
        self.commande.calculer_totaux()   # 96 + 20 = 116
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def _post(self, lignes, **extra):
        data = {'id': self.commande.id, 'lignes': lignes}
        data.update(extra)
        return self.api.post(URL, data, format='json')

    def _lignes(self):
        return {l.produit.reference: (l.quantite, l.prix_unitaire_ht)
                for l in LigneCommandeClient.objects.filter(commande=self.commande)}

    # ---------------------------------------------------------------- cas nominaux
    def test_changer_quantites_ajouter_et_retirer_un_produit(self):
        r = self._post([
            {'produit': self.eau.id, 'quantite': 10, 'prix_unitaire_ht': '999'},   # baisse ; prix envoye ignore
            {'produit': self.jus.id, 'quantite': 3, 'prix_unitaire_ht': '18'},     # ajout au prix client
        ])                                                                          # chips retire
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._lignes(), {'EAU': (Decimal('10'), Decimal('8')), 'JUS': (Decimal('3'), Decimal('18'))})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_total_ttc, Decimal('134'))   # 80 + 54
        self.assertEqual(float(r.json()['montant_total_ttc']), 134.0)
        self.assertEqual(len(r.json()['modifications']), 3)
        trace = self.commande.notes_preparation
        for attendu in ('Modifiée par vendeur', 'Eau 12→10', '+Jus x3', '-Chips'):
            self.assertIn(attendu, trace)

    def test_augmenter_une_quantite(self):
        r = self._post([{'produit': self.eau.id, 'quantite': 24}, {'produit': self.chips.id, 'quantite': 4}])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._lignes()['EAU'][0], Decimal('24'))
        self.assertEqual(r.json()['modifications'], ['Eau 12→24'])

    def test_produit_ajoute_sans_prix_prend_le_prix_catalogue(self):
        r = self._post([{'produit': self.eau.id, 'quantite': 12}, {'produit': self.chips.id, 'quantite': 4},
                        {'produit_id': self.jus.id, 'quantite': 1}])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._lignes()['JUS'], (Decimal('1'), Decimal('20')))

    def test_recherche_par_app_id_et_notes(self):
        r = self.api.post(URL, {'app_id': 'commande-123-1', 'notes': 'Livrer avant 10h',
                                'lignes': [{'produit': self.eau.id, 'quantite': 12},
                                           {'produit': self.chips.id, 'quantite': 4}]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.notes, 'Livrer avant 10h')
        self.assertEqual(r.json()['modifications'], ['notes modifiées'])

    def test_sans_changement_aucune_trace(self):
        r = self._post([{'produit': self.eau.id, 'quantite': 12}, {'produit': self.chips.id, 'quantite': 4}])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['modifications'], [])
        self.commande.refresh_from_db()
        self.assertFalse(self.commande.notes_preparation)

    # ---------------------------------------------------------------- refus
    def _assert_refus(self, reponse, code):
        self.assertEqual(reponse.status_code, code, reponse.content)
        self.assertIn('detail', reponse.json())
        self.assertEqual(self._lignes(), {'EAU': (Decimal('12'), Decimal('8')), 'CHIPS': (Decimal('4'), Decimal('5'))})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_total_ttc, Decimal('116'))

    def test_commande_livree_ou_annulee_refusee(self):
        for statut in ('delivered', 'cancelled'):
            CommandeClient.objects.filter(pk=self.commande.pk).update(statut=statut)
            self._assert_refus(self._post([{'produit': self.eau.id, 'quantite': 1}]), 409)

    def test_commande_payee_refusee(self):
        CommandeClient.objects.filter(pk=self.commande.pk).update(est_paye=True, montant_paye=Decimal('116'))
        self._assert_refus(self._post([{'produit': self.eau.id, 'quantite': 1}]), 409)

    def test_total_inferieur_au_montant_encaisse_refuse_et_annule(self):
        CommandeClient.objects.filter(pk=self.commande.pk).update(montant_paye=Decimal('100'))
        self._assert_refus(self._post([{'produit': self.eau.id, 'quantite': 2}]), 400)   # total 16 < 100

    def test_lignes_invalides_refusees(self):
        cas = [
            [],                                                                     # commande vide
            [{'produit': self.eau.id, 'quantite': 0}],                              # quantite nulle
            [{'produit': self.eau.id, 'quantite': -3}],                             # negative
            [{'produit': self.eau.id, 'quantite': 'abc'}],                          # non numerique
            [{'produit': 999999, 'quantite': 1}],                                   # produit inconnu
            [{'quantite': 1}],                                                      # produit absent
            [{'produit': self.eau.id, 'quantite': 1}, {'produit': self.eau.id, 'quantite': 2}],   # doublon
            [{'produit': self.inactif.id, 'quantite': 1}],                          # produit retire de la vente
        ]
        for lignes in cas:
            self._assert_refus(self._post(lignes), 400)

    def test_commande_introuvable(self):
        r = self.api.post(URL, {'id': 999999, 'lignes': [{'produit': self.eau.id, 'quantite': 1}]}, format='json')
        self.assertEqual(r.status_code, 404)
        r = self.api.post(URL, {'lignes': [{'produit': self.eau.id, 'quantite': 1}]}, format='json')
        self.assertEqual(r.status_code, 400)

    # ---------------------------------------------------------------- droits
    def test_droits(self):
        lignes = [{'produit': self.eau.id, 'quantite': 5}, {'produit': self.chips.id, 'quantite': 4}]
        anonyme = APIClient()
        self.assertIn(anonyme.post(URL, {'id': self.commande.id, 'lignes': lignes}, format='json').status_code, (401, 403))

        simple = APIClient()
        simple.force_authenticate(User.objects.create_user('bureau', password='x'))
        self._assert_refus(simple.post(URL, {'id': self.commande.id, 'lignes': lignes}, format='json'), 403)

        # un autre vendeur (le livreur qui livre la commande prise par le prevendeur)
        autre_user = User.objects.create_user('livreur', password='x')
        LivreurDistribution.objects.create(matricule='L2', nom='Yacine', telephone='0', user=autre_user)
        autre = APIClient()
        autre.force_authenticate(autre_user)
        self.assertEqual(autre.post(URL, {'id': self.commande.id, 'lignes': lignes}, format='json').status_code, 200)

        admin = APIClient()
        admin.force_authenticate(User.objects.create_user('admin', password='x', is_staff=True))
        self.assertEqual(admin.post(URL, {'id': self.commande.id, 'lignes': lignes}, format='json').status_code, 200)

        # vendeur suspendu
        LivreurDistribution.objects.filter(pk=self.vendeur.pk).update(statut='suspendu')
        self.assertEqual(self._post(lignes).status_code, 403)
