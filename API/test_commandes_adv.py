"""Commandes clients côté bureau (ADV) et visibilité des dettes clients.

- ajout d'un produit à une commande depuis la fenêtre « Modifier » (PATCH) : totaux justes,
  enregistrement atomique ;
- clients sans entreprise (créés sur les téléphones) visibles par le bureau, avec leurs dettes ;
- encaissements d'un livreur sans entreprise sur SES commandes / SES clients ;
- ventes mobiles de « toutes les ventes » limitées à l'entreprise de l'utilisateur.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Categorie, Client, Company, Produit, UserProfile, Warehouse
from .distribution_models import (CommandeClient, LigneCommandeClient, LivreurDistribution,
                                  VenteTourneeMobile)


class _Base(TestCase):
    def setUp(self):
        self.co_a = Company.objects.create(name='Entreprise A', code='A')
        self.co_b = Company.objects.create(name='Entreprise B', code='B')
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau',
                                          prixU=Decimal('10'), categorie=cat, company=self.co_a)
        self.jus = Produit.objects.create(reference='JUS', code_barre='2', designation='Jus',
                                          prixU=Decimal('20'), categorie=cat, company=self.co_a)

        self.bureau_a = User.objects.create_user('bureau_a', password='x')
        UserProfile.objects.create(user=self.bureau_a, company=self.co_a)
        self.bureau_b = User.objects.create_user('bureau_b', password='x')
        UserProfile.objects.create(user=self.bureau_b, company=self.co_b)

        # Livreur dont le van n'a pas d'entreprise (cas réel des téléphones)
        self.u_livreur = User.objects.create_user('livreur', password='x')
        van = Warehouse.objects.create(name='Van sans entreprise', code='VAN0')
        self.livreur = LivreurDistribution.objects.create(matricule='L1', nom='Livreur', telephone='0',
                                                          user=self.u_livreur, entrepot=van)
        self.u_autre = User.objects.create_user('autre_livreur', password='x')
        self.autre = LivreurDistribution.objects.create(matricule='L2', nom='Autre', telephone='0',
                                                        user=self.u_autre)

        self.client_a = Client.objects.create(nom='Client A', prenom='', telephone='1', company=self.co_a)
        self.client_b = Client.objects.create(nom='Client B', prenom='', telephone='2', company=self.co_b)
        # Client créé sur un téléphone par un livreur sans entreprise, avec une dette antérieure
        self.client_tel = Client.objects.create(nom='Client Tel', prenom='', telephone='3',
                                                solde=Decimal('-500'))

        self.commande = CommandeClient.objects.create(client=self.client_a, livreur=self.livreur,
                                                      reference='CMD-A1', statut='confirmed')
        LigneCommandeClient.objects.create(commande=self.commande, produit=self.eau, quantite=10,
                                           prix_unitaire_ht=Decimal('8'), taux_tva=0)
        self.commande.calculer_totaux()   # 80
        self.api = APIClient()

    def connecter(self, user):
        # force_login : le TenantMiddleware renseigne request.company comme en production
        self.api.logout()
        self.api.force_login(user)


class AjoutProduitCommandeTests(_Base):
    URL = '/API/distribution/commandes/{}/'

    def _lignes(self):
        return {l.produit.reference: (l.quantite, l.prix_unitaire_ht)
                for l in LigneCommandeClient.objects.filter(commande=self.commande)}

    def test_ajout_d_un_produit_par_le_bureau_recalcule_les_totaux(self):
        self.connecter(self.bureau_a)
        r = self.api.patch(self.URL.format(self.commande.id), {
            'notes': '', 'type_paiement': 'non_paye',
            'lignes': [
                {'produit': self.eau.id, 'quantite': 10, 'prix_unitaire_ht': 8, 'taux_tva': 0},
                {'produit': self.jus.id, 'quantite': 3, 'prix_unitaire_ht': 18, 'taux_tva': 0},
            ]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._lignes(), {'EAU': (Decimal('10'), Decimal('8')),
                                          'JUS': (Decimal('3'), Decimal('18'))})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_total_ttc, Decimal('134'))

    def test_ajout_refuse_laisse_la_commande_intacte(self):
        self.connecter(self.bureau_a)
        r = self.api.patch(self.URL.format(self.commande.id), {
            'lignes': [
                {'produit': self.eau.id, 'quantite': 10, 'prix_unitaire_ht': 8, 'taux_tva': 0},
                {'produit': 999999, 'quantite': 1, 'prix_unitaire_ht': 5, 'taux_tva': 0},
            ]}, format='json')
        self.assertEqual(r.status_code, 400, r.content)
        self.assertEqual(self._lignes(), {'EAU': (Decimal('10'), Decimal('8'))})
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_total_ttc, Decimal('80'))


class ClientsSansEntrepriseTests(_Base):
    def test_le_bureau_voit_les_clients_sans_entreprise_mais_pas_ceux_d_une_autre(self):
        self.connecter(self.bureau_a)
        r = self.api.get('/API/clients/')
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        ids = {c['id'] for c in (data['results'] if isinstance(data, dict) else data)}
        self.assertIn(self.client_a.id, ids)
        self.assertIn(self.client_tel.id, ids)
        self.assertNotIn(self.client_b.id, ids)
        self.assertEqual(self.api.get(f'/API/clients/{self.client_tel.id}/').status_code, 200)
        self.assertEqual(self.api.get(f'/API/clients/{self.client_b.id}/').status_code, 404)

    def test_la_dette_d_un_client_sans_entreprise_apparait_au_tableau_de_bord(self):
        self.connecter(self.bureau_a)
        r = self.api.get('/API/clients/dashboard_stats/')
        self.assertEqual(r.status_code, 200, r.content)
        ids_dettes = {c['id'] for c in r.json()['top_dettes']}
        self.assertIn(self.client_tel.id, ids_dettes)
        self.assertNotIn(self.client_b.id, ids_dettes)


class EncaissementLivreurSansEntrepriseTests(_Base):
    URL_CMD = '/API/distribution/commandes/encaisser/'
    URL_CLIENT = '/API/distribution/comptes-clients/encaisser/'

    def _encaisser_commande(self, app_id, montant=30):
        return self.api.post(self.URL_CMD, {'app_id': app_id, 'commande_id': self.commande.id,
                                            'montant': montant, 'type_paiement': 'especes'}, format='json')

    def test_livreur_sans_entreprise_encaisse_sa_commande(self):
        self.api.force_authenticate(self.u_livreur)
        r = self._encaisser_commande('enc-1')
        self.assertEqual(r.status_code, 201, r.content)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_paye, Decimal('30'))

    def test_vendeur_passee_par_encaisse_aussi(self):
        CommandeClient.objects.filter(pk=self.commande.pk).update(livreur=self.autre, passee_par=self.livreur)
        self.api.force_authenticate(self.u_livreur)
        self.assertEqual(self._encaisser_commande('enc-2').status_code, 201)

    def test_autre_livreur_sans_entreprise_refuse(self):
        self.api.force_authenticate(self.u_autre)
        self.assertEqual(self._encaisser_commande('enc-3').status_code, 404)

    def test_bureau_d_une_autre_entreprise_refuse(self):
        self.connecter(self.bureau_b)
        self.assertEqual(self._encaisser_commande('enc-4').status_code, 404)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.montant_paye or Decimal('0'), Decimal('0'))

    def test_bureau_de_l_entreprise_encaisse(self):
        self.connecter(self.bureau_a)
        self.assertEqual(self._encaisser_commande('enc-5').status_code, 201)

    def test_compte_client_du_livreur(self):
        client_c = Client.objects.create(nom='Client C', prenom='', telephone='4', company=self.co_a,
                                         solde=Decimal('-100'))
        self.api.force_authenticate(self.u_livreur)
        donnees = {'app_id': 'cc-1', 'client': client_c.id, 'montant': 40, 'mode_paiement': 'especes'}
        # Client d'une entreprise, sans lien avec ce livreur : refusé
        self.assertEqual(self.api.post(self.URL_CLIENT, donnees, format='json').status_code, 404)
        # Client assigné au livreur : accepté malgré l'entreprise différente
        self.livreur.clients_assignes.add(client_c)
        r = self.api.post(self.URL_CLIENT, donnees, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        # Client d'une de ses commandes : accepté
        r = self.api.post(self.URL_CLIENT, {'app_id': 'cc-2', 'client': self.client_a.id, 'montant': 10,
                                            'mode_paiement': 'especes'}, format='json')
        self.assertNotEqual(r.status_code, 404, r.content)
        # Un autre livreur n'y a pas accès
        self.api.force_authenticate(self.u_autre)
        r = self.api.post(self.URL_CLIENT, {'app_id': 'cc-3', 'client': client_c.id, 'montant': 10,
                                            'mode_paiement': 'especes'}, format='json')
        self.assertEqual(r.status_code, 404)


class VentesMobilesParEntrepriseTests(_Base):
    def setUp(self):
        super().setUp()
        self.v_a = VenteTourneeMobile.objects.create(client=self.client_a, numero_vente='VM-A',
                                                     type_paiement='especes', montant_total=Decimal('10'))
        self.v_b = VenteTourneeMobile.objects.create(client=self.client_b, numero_vente='VM-B',
                                                     type_paiement='especes', montant_total=Decimal('20'))
        self.v_tel = VenteTourneeMobile.objects.create(client=self.client_tel, numero_vente='VM-T',
                                                       type_paiement='credit', montant_total=Decimal('30'))

    def _numeros(self):
        r = self.api.get('/API/ventes/all_sales/')
        self.assertEqual(r.status_code, 200, r.content)
        return {v['numero'] for v in r.json() if v['source'] == 'mobile'}

    def test_bureau_ne_voit_que_son_entreprise_et_les_ventes_sans_entreprise(self):
        self.connecter(self.bureau_a)
        self.assertEqual(self._numeros(), {'VM-A', 'VM-T'})
        self.connecter(self.bureau_b)
        self.assertEqual(self._numeros(), {'VM-B', 'VM-T'})

    def test_superutilisateur_voit_tout(self):
        admin = User.objects.create_superuser('admin', 'admin@x.local', 'x')
        self.connecter(admin)
        self.assertEqual(self._numeros(), {'VM-A', 'VM-B', 'VM-T'})
