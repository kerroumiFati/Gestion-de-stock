"""Points 13 et 14 : changement de statut d'une commande et sortie du stock du van.

- 14 : stock du van insuffisant (ou pas de livreur / pas de van) -> la livraison est REFUSÉE en
  entier. Avant : la commande passait « livrée » sans aucune sortie de stock.
- 13 : « livrée » depuis le PC passe par le vrai traitement de livraison (stock, tournée en cours
  du livreur) ; une commande livrée ne change plus de statut ; une commande annulée rend
  l'argent déjà payé sous forme d'avance sur le compte du client.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, PaiementSolde, Produit, ProductStock, StockMove, Warehouse
from .distribution_models import CommandeClient, LigneCommandeClient, LivreurDistribution, TourneeMobile


class StatutCommandeTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau',
                                          prixU=Decimal('10'), categorie=cat)
        self.van = Warehouse.objects.create(name='Van 1', code='VAN1')
        self.user_livreur = User.objects.create_user('livreur', password='x')
        self.livreur = LivreurDistribution.objects.create(matricule='L1', nom='Ahmed', telephone='0',
                                                          user=self.user_livreur, entrepot=self.van)
        self.tournee = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=date.today(),
                                                    numero_tournee='T1', statut='en_cours')
        self.client_ = Client.objects.create(nom='Client', prenom='Test', telephone='0')
        self.commande = CommandeClient.objects.create(client=self.client_, livreur=self.livreur, reference='CMD-1')
        LigneCommandeClient.objects.create(commande=self.commande, produit=self.eau, quantite=10,
                                           prix_unitaire_ht=Decimal('10'), taux_tva=0)
        self.commande.calculer_totaux()   # 100 DA
        self.pc = APIClient()
        self.pc.force_authenticate(User.objects.create_user('bureau', password='x', is_staff=True))
        self.tel = APIClient()
        self.tel.force_authenticate(self.user_livreur)

    def _stock_van(self, quantite):
        ProductStock.objects.update_or_create(produit=self.eau, warehouse=self.van, defaults={'quantity': quantite})

    def _changer(self, statut):
        return self.pc.patch(f'/API/distribution/commandes/{self.commande.id}/changer_statut/',
                             {'statut': statut}, format='json')

    def _recharger(self):
        self.commande.refresh_from_db()
        return self.commande

    # ------------------------------------------------------------------ point 14
    def test_pc_stock_van_insuffisant_livraison_refusee(self):
        self._stock_van(3)
        r = self._changer('delivered')
        self.assertEqual(r.status_code, 409, r.content)
        self.assertIn('Stock insuffisant', r.json()['error'])
        self.assertEqual(self._recharger().statut, 'pending')
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.van).quantity, 3)
        self.assertFalse(StockMove.objects.filter(ref_id='CMD-1').exists())

    def test_telephone_stock_van_insuffisant_livraison_refusee(self):
        self._stock_van(3)
        r = self.tel.patch(f'/API/distribution/commandes/{self.commande.id}/',
                           {'statut': 'delivered', 'tournee_livraison': self.tournee.id,
                            'lignes': [{'produit': self.eau.id, 'quantite': 5}]}, format='json')
        self.assertEqual(r.status_code, 409, r.content)
        c = self._recharger()
        self.assertEqual(c.statut, 'pending')
        self.assertEqual(c.montant_total_ttc, Decimal('100'))          # quantités non modifiées
        self.assertEqual(LigneCommandeClient.objects.get(commande=c).quantite, 10)

    def test_livreur_sans_van_refusee(self):
        LivreurDistribution.objects.filter(pk=self.livreur.pk).update(entrepot=None)
        r = self._changer('delivered')
        self.assertEqual(r.status_code, 409, r.content)
        self.assertIn("pas de van", r.json()['error'])
        self.assertEqual(self._recharger().statut, 'pending')

    # ------------------------------------------------------------------ point 13
    def test_pc_livree_deduit_le_stock_et_prend_la_tournee_en_cours(self):
        self._stock_van(25)
        r = self._changer('delivered')
        self.assertEqual(r.status_code, 200, r.content)
        c = self._recharger()
        self.assertEqual(c.statut, 'delivered')
        self.assertEqual(c.tournee_livraison_id, self.tournee.id)
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.van).quantity, 15)

    def test_commande_livree_ne_change_plus_de_statut(self):
        self._stock_van(25)
        self._changer('delivered')
        for statut in ('pending', 'cancelled'):
            r = self._changer(statut)
            self.assertEqual(r.status_code, 409, r.content)
        r = self.pc.patch(f'/API/distribution/commandes/{self.commande.id}/', {'statut': 'pending'}, format='json')
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(self._recharger().statut, 'delivered')
        # Pas de seconde sortie de stock possible
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.van).quantity, 15)

    def test_annulation_acompte_passe_en_avance_client(self):
        CommandeClient.objects.filter(pk=self.commande.pk).update(montant_paye=Decimal('30'))
        r = self._changer('cancelled')
        self.assertEqual(r.status_code, 200, r.content)
        c = self._recharger()
        self.assertEqual((c.statut, c.montant_paye, c.est_paye), ('cancelled', Decimal('0'), False))
        self.client_.refresh_from_db()
        self.assertEqual(self.client_.solde, Decimal('30'))             # avance du client
        p = PaiementSolde.objects.get(app_id=f'annulation-{c.id}')
        self.assertEqual((p.montant, p.mode_paiement), (Decimal('30'), 'avoir'))
        # Une seconde annulation ne crédite pas deux fois
        self.assertEqual(self._changer('cancelled').status_code, 200)
        self.client_.refresh_from_db()
        self.assertEqual(self.client_.solde, Decimal('30'))

    def test_annulation_par_patch_meme_regle(self):
        CommandeClient.objects.filter(pk=self.commande.pk).update(montant_paye=Decimal('40'))
        r = self.pc.patch(f'/API/distribution/commandes/{self.commande.id}/', {'statut': 'cancelled'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        c = self._recharger()
        self.assertEqual((c.statut, c.montant_paye), ('cancelled', Decimal('0')))
        self.client_.refresh_from_db()
        self.assertEqual(self.client_.solde, Decimal('40'))

    def test_annulation_sans_paiement_ne_touche_pas_au_compte(self):
        self.assertEqual(self._changer('cancelled').status_code, 200)
        self.client_.refresh_from_db()
        self.assertEqual(self.client_.solde or Decimal('0'), Decimal('0'))
        self.assertFalse(PaiementSolde.objects.exists())

    def test_commande_annulee_ne_peut_plus_etre_livree(self):
        self._stock_van(25)
        self.assertEqual(self._changer('cancelled').status_code, 200)
        r = self.tel.patch(f'/API/distribution/commandes/{self.commande.id}/',
                           {'statut': 'delivered', 'tournee_livraison': self.tournee.id}, format='json')
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(self._recharger().statut, 'cancelled')
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.van).quantity, 25)
