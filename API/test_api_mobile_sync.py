"""API de l'application mobile (prévendeurs / livreurs) : isolation par entreprise avec JWT,
stock dépôt, prix par type de client, synchronisation des arrêts, endpoints groupés."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (Categorie, Client, CodePrix, Company, PrixProduit, Produit, ProductStock,
                     SystemConfig, TypePrix, Warehouse)
from .distribution_models import (ArretTourneeMobile, ClientLivreurHebdo, CommandeClient,
                                  LigneCommandeClient, LivreurDistribution, TourneeMobile,
                                  VenteTourneeMobile, LigneVenteTourneeMobile)

BASE = '/API/distribution'


class BaseMobile(TestCase):
    def setUp(self):
        self.co_a = Company.objects.create(name='Société A', code='A')
        self.co_b = Company.objects.create(name='Société B', code='B')
        self.cat = Categorie.objects.create(nom='Boissons')
        self.depot = Warehouse.objects.create(company=self.co_a, name='Dépôt A', code='DEPA')
        self.camion = Warehouse.objects.create(company=self.co_a, name='Camion 1', code='CAM1')  # van sans « van »
        self.depot_b = Warehouse.objects.create(company=self.co_b, name='Dépôt B', code='DEPB')
        self.eau = self._produit('EAU', self.co_a, prix='10')
        self.jus = self._produit('JUS', self.co_a, prix='20')
        self.commun = self._produit('COMMUN', None, prix='5')
        self.secret_b = self._produit('SECRET_B', self.co_b, prix='7')

        self.user = User.objects.create_user('prev1', password='motdepasse')
        # Pas de profil : l'entreprise vient du van du livreur (cas des comptes mobiles)
        self.livreur = LivreurDistribution.objects.create(matricule='P1', nom='Prévendeur 1', telephone='0',
                                                          user=self.user, entrepot=self.camion)
        self.api = APIClient()
        self.api.force_authenticate(self.user)   # comme JWT : request.company du middleware = None

    def _produit(self, ref, company, prix='10', quantite=0):
        return Produit.objects.create(reference=ref, code_barre=ref, designation=ref.title(),
                                      prixU=Decimal(prix), categorie=self.cat, company=company,
                                      quantite=quantite)

    def _produits(self):
        r = self.api.get(f'{BASE}/produits/')
        self.assertEqual(r.status_code, 200, r.content)
        return {p['reference']: p for p in r.json()}


class TenantProduitsTests(BaseMobile):
    def test_prevendeur_ne_voit_que_son_entreprise_et_les_produits_communs(self):
        self.assertEqual(set(self._produits()), {'EAU', 'JUS', 'COMMUN'})

    def test_avec_un_vrai_jeton_jwt(self):
        api = APIClient()
        r = api.post('/API/token/', {'username': 'prev1', 'password': 'motdepasse'}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
        r = api.get(f'{BASE}/produits/')
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('SECRET_B', {p['reference'] for p in r.json()})

    def test_superutilisateur_voit_tout(self):
        admin = User.objects.create_superuser('admin', 'a@a.fr', 'x')
        self.api.force_authenticate(admin)
        self.assertIn('SECRET_B', self._produits())


class StockDepotTests(BaseMobile):
    def test_stock_depot_sans_van_ni_repli_sur_quantite_globale(self):
        self.eau.quantite = 999
        self.eau.save()
        ProductStock.objects.create(produit=self.eau, warehouse=self.camion, quantity=50)   # van lié au livreur
        vieux_van = Warehouse.objects.create(company=self.co_a, name='Vieux', code='VAN9')
        ProductStock.objects.create(produit=self.eau, warehouse=vieux_van, quantity=30)      # code « van »
        inactif = Warehouse.objects.create(company=self.co_a, name='Fermé', code='OLD', is_active=False)
        ProductStock.objects.create(produit=self.eau, warehouse=inactif, quantity=20)
        ProductStock.objects.create(produit=self.eau, warehouse=self.depot_b, quantity=40)  # autre entreprise
        ProductStock.objects.create(produit=self.jus, warehouse=self.depot, quantity=12)
        p = self._produits()
        self.assertEqual(p['EAU']['stock'], 0)      # avant : 999 (Produit.quantite)
        self.assertEqual(p['JUS']['stock'], 12)
        self.assertEqual(p['EAU']['quantite'], 999)  # champ inchangé

    def test_depot_des_commandes_mobiles_configure(self):
        autre = Warehouse.objects.create(company=self.co_a, name='Dépôt 2', code='DEP2')
        ProductStock.objects.create(produit=self.jus, warehouse=self.depot, quantity=12)
        ProductStock.objects.create(produit=self.jus, warehouse=autre, quantity=5)
        self.assertEqual(self._produits()['JUS']['stock'], 17)
        cfg = SystemConfig.get_solo(self.co_a)
        cfg.depot_commandes_mobile = autre
        cfg.save()
        self.assertEqual(self._produits()['JUS']['stock'], 5)

    def test_nombre_de_requetes_constant(self):
        for i in range(15):
            p = self._produit(f'X{i}', self.co_a)
            ProductStock.objects.create(produit=p, warehouse=self.depot, quantity=3)
        with CaptureQueriesContext(connection) as ctx:
            self._produits()
        self.assertLessEqual(len(ctx.captured_queries), 12)


class PrixParTypeTests(BaseMobile):
    def setUp(self):
        super().setUp()
        self.detail = TypePrix.objects.create(code='DETAIL', libelle='Détail', is_default=True)
        self.gros = TypePrix.objects.create(code='GROS', libelle='Gros')
        std = CodePrix.objects.create(code='STANDARD', libelle='Standard', is_default=True)
        PrixProduit.objects.create(produit=self.eau, code_prix=std, type_prix=self.detail, prix=Decimal('12'))
        PrixProduit.objects.create(produit=self.eau, code_prix=std, type_prix=self.gros, prix=Decimal('9.50'))

    def test_catalogue_expose_prix_par_type(self):
        p = self._produits()
        self.assertEqual(p['EAU']['prix_par_type'], {'DETAIL': 12.0, 'GROS': 9.5})
        self.assertEqual(p['JUS']['prix_par_type'], {})
        self.assertEqual(p['EAU']['promotions'], {})
        self.assertEqual(Decimal(p['EAU']['prixU']), Decimal('10'))

    def test_commande_sans_prix_prend_le_prix_du_type_de_client(self):
        client_gros = Client.objects.create(nom='Gros', prenom='Client', telephone='0', type_prix=self.gros)
        r = self.api.post(f'{BASE}/commandes/', {
            'app_id': 'commande-prix-1', 'client': client_gros.id, 'livreur': self.livreur.id,
            'lignes': [{'produit': self.eau.id, 'quantite': 2},
                       {'produit': self.jus.id, 'quantite': 1, 'prix_unitaire_ht': '0'},
                       {'produit': self.commun.id, 'quantite': 1, 'prix_unitaire_ht': '4'}],
        }, format='json')
        self.assertEqual(r.status_code, 201, r.content)
        lignes = {l.produit.reference: l.prix_unitaire_ht
                  for l in LigneCommandeClient.objects.filter(commande__app_id='commande-prix-1')}
        self.assertEqual(lignes, {'EAU': Decimal('9.50'), 'JUS': Decimal('20'), 'COMMUN': Decimal('4')})

    def test_stock_van_garde_son_format_en_peu_de_requetes(self):
        for i in range(10):
            p = self._produit(f'V{i}', self.co_a)
            ProductStock.objects.create(produit=p, warehouse=self.camion, quantity=4)
        ProductStock.objects.create(produit=self.eau, warehouse=self.camion, quantity=6)
        with CaptureQueriesContext(connection) as ctx:
            r = self.api.get(f'{BASE}/livreurs/{self.livreur.id}/stock_van/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertLessEqual(len(ctx.captured_queries), 12)
        eau = next(s for s in r.json()['stocks'] if s['reference'] == 'EAU')
        self.assertEqual(eau['prix_par_type']['GROS'],
                         {'prix': 9.5, 'prix_original': 9.5, 'has_promotion': False,
                          'quantite_min': 1, 'promo_code': None})
        self.assertEqual(eau['prix_unitaire'], 12.0)


class LivreursTests(BaseMobile):
    def test_me(self):
        r = self.api.get(f'{BASE}/livreurs/me/')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['id'], self.livreur.id)
        self.assertIn('tournees_actives_count', r.json())
        self.api.force_authenticate(User.objects.create_user('bureau', password='x'))
        self.assertEqual(self.api.get(f'{BASE}/livreurs/me/').status_code, 404)

    def test_liste_sans_n_plus_1(self):
        for i in range(8):
            l = LivreurDistribution.objects.create(matricule=f'L{i}', nom=f'L{i}', telephone='0')
            TourneeMobile.objects.create(livreur=l, date_tournee=date.today(), numero_tournee=f'T{i}')
        with CaptureQueriesContext(connection) as ctx:
            r = self.api.get(f'{BASE}/livreurs/')
        self.assertEqual(r.status_code, 200)
        self.assertLessEqual(len(ctx.captured_queries), 3)
        l0 = next(l for l in r.json() if l['matricule'] == 'L0')
        self.assertEqual(l0['tournees_actives_count'], 1)
        self.assertFalse(l0['is_disponible'])


class VentesEtTourneesGroupeesTests(BaseMobile):
    def setUp(self):
        super().setUp()
        self.client_ = Client.objects.create(nom='Client', prenom='A', telephone='0')
        today = timezone.localdate()
        self.t_recent = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=today - timedelta(days=2),
                                                     numero_tournee='T-R', statut='terminee')
        self.t_vieux = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=today - timedelta(days=60),
                                                    numero_tournee='T-V', statut='terminee')
        self.t_vieux_en_cours = TourneeMobile.objects.create(
            livreur=self.livreur, date_tournee=today - timedelta(days=45), numero_tournee='T-EC', statut='en_cours')
        autre = LivreurDistribution.objects.create(matricule='P2', nom='Autre', telephone='0')
        self.t_autre = TourneeMobile.objects.create(livreur=autre, date_tournee=today, numero_tournee='T-A')
        self.v_recent = self._vente(self.t_recent, timezone.now() - timedelta(days=2))
        self.v_vieux = self._vente(self.t_vieux, timezone.now() - timedelta(days=60))
        self.v_autre = self._vente(self.t_autre, timezone.now())

    def _vente(self, tournee, quand):
        v = VenteTourneeMobile.objects.create(client=self.client_, tournee=tournee, date_vente=quand,
                                              numero_vente=f'V-{tournee.numero_tournee}', montant_total=Decimal('10'))
        LigneVenteTourneeMobile.objects.create(vente=v, produit=self.eau, quantite=1, prix_unitaire=Decimal('10'),
                                               taux_tva=Decimal('0'))
        return v

    def _ids(self, url):
        r = self.api.get(url)
        self.assertEqual(r.status_code, 200, r.content)
        return {v['id'] for v in r.json()}, r.json()

    def test_ventes_du_livreur_en_une_requete(self):
        ids, data = self._ids(f'{BASE}/ventes/?livreur={self.livreur.id}')
        self.assertEqual(ids, {self.v_recent.id})          # 30 derniers jours par défaut
        self.assertEqual(len(data[0]['lignes']), 1)
        depuis = (timezone.localdate() - timedelta(days=90)).isoformat()
        ids, _ = self._ids(f'{BASE}/ventes/?livreur={self.livreur.id}&depuis={depuis}')
        self.assertEqual(ids, {self.v_recent.id, self.v_vieux.id})
        # Un livreur ne peut pas lire les ventes d'un autre : on lui renvoie les siennes
        ids, _ = self._ids(f'{BASE}/ventes/?livreur={self.t_autre.livreur_id}&depuis={depuis}')
        self.assertEqual(ids, {self.v_recent.id, self.v_vieux.id})
        self.assertEqual(self.api.get(f'{BASE}/ventes/?livreur={self.livreur.id}&depuis=xx').status_code, 400)

    def test_ventes_par_tournee_inchangees(self):
        ids, _ = self._ids(f'{BASE}/ventes/?tournee={self.t_vieux.id}')
        self.assertEqual(ids, {self.v_vieux.id})

    def test_tournees_depuis(self):
        depuis = (timezone.localdate() - timedelta(days=30)).isoformat()
        for url in (f'{BASE}/tournees/', '/API/tournees/'):
            r = self.api.get(url, {'livreur': self.livreur.id, 'depuis': depuis})
            self.assertEqual(r.status_code, 200, r.content)
            self.assertEqual({t['numero_tournee'] for t in r.json()}, {'T-R', 'T-EC'})
            r = self.api.get(url, {'livreur': self.livreur.id})   # sans paramètre : tout l'historique
            self.assertEqual(len(r.json()), 3)


class SyncArretsTests(BaseMobile):
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.jour = self.today.weekday() + 1
        self.tournee = TourneeMobile.objects.create(livreur=self.livreur, date_tournee=self.today,
                                                    numero_tournee='T-1', statut='planifiee')
        self.c1 = Client.objects.create(nom='Un', prenom='C', telephone='0')
        self.c2 = Client.objects.create(nom='Deux', prenom='C', telephone='0')
        self.admin = User.objects.create_superuser('admin', 'a@a.fr', 'x')
        self.bureau = APIClient()
        self.bureau.force_authenticate(self.admin)

    def _clients_arrets(self):
        return set(ArretTourneeMobile.objects.filter(tournee=self.tournee).values_list('client_id', flat=True))

    def test_affectation_apres_creation_de_la_tournee_ajoute_l_arret(self):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.bureau.post(f'{BASE}/clients-livreurs-hebdo/assigner_clients/', {
                'livreur_id': self.livreur.id, 'clients_ids': [self.c1.id, self.c2.id],
                'jours_semaine': [self.jour]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._clients_arrets(), {self.c1.id, self.c2.id})

        # Retrait d'une affectation : l'arrêt « en attente » disparaît, l'autre reste
        a = ClientLivreurHebdo.objects.get(client=self.c2, livreur=self.livreur)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.bureau.delete(f'{BASE}/clients-livreurs-hebdo/supprimer_assignations/',
                                   {'assignations_ids': [a.id]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self._clients_arrets(), {self.c1.id})

    def test_arret_ajoute_a_la_main_conserve_et_jour_different_ignore(self):
        manuel = Client.objects.create(nom='Manuel', prenom='C', telephone='0')
        ArretTourneeMobile.objects.create(tournee=self.tournee, client=manuel, ordre_passage=1)
        autre_jour = self.jour % 7 + 1
        with self.captureOnCommitCallbacks(execute=True):
            ClientLivreurHebdo.objects.create(client=self.c1, livreur=self.livreur, jour_semaine=self.jour)
            ClientLivreurHebdo.objects.create(client=self.c2, livreur=self.livreur, jour_semaine=autre_jour)
        self.assertEqual(self._clients_arrets(), {manuel.id, self.c1.id})
        ordres = list(ArretTourneeMobile.objects.filter(tournee=self.tournee).values_list('ordre_passage', flat=True))
        self.assertEqual(len(ordres), len(set(ordres)))

    def test_demarrage_charge_les_clients_assignes_du_jour(self):
        # Affectation hors synchronisation automatique (rappels on_commit non exécutés) :
        # la tournée n'a pas encore l'arrêt du client assigné
        manuel = Client.objects.create(nom='Manuel', prenom='C', telephone='0')
        ArretTourneeMobile.objects.create(tournee=self.tournee, client=manuel, ordre_passage=1)
        ClientLivreurHebdo.objects.create(client=self.c1, livreur=self.livreur, jour_semaine=self.jour)
        self.assertEqual(self._clients_arrets(), {manuel.id})

        r = self.bureau.post(f'{BASE}/tournees/{self.tournee.id}/demarrer/', {}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()['clients_ajoutes'], 1)
        # Le client assigné est chargé, l'arrêt ajouté à la main est conservé
        self.assertEqual(self._clients_arrets(), {manuel.id, self.c1.id})
        self.tournee.refresh_from_db()
        self.assertEqual(self.tournee.statut, 'en_cours')

    def test_reaffectation_a_un_autre_livreur(self):
        autre = LivreurDistribution.objects.create(matricule='P2', nom='Autre', telephone='0')
        t2 = TourneeMobile.objects.create(livreur=autre, date_tournee=self.today, numero_tournee='T-2')
        with self.captureOnCommitCallbacks(execute=True):
            cfg = ClientLivreurHebdo.objects.create(client=self.c1, livreur=self.livreur, jour_semaine=self.jour)
        self.assertEqual(self._clients_arrets(), {self.c1.id})
        with self.captureOnCommitCallbacks(execute=True):
            cfg.livreur = autre
            cfg.save()
        self.assertEqual(self._clients_arrets(), set())
        self.assertTrue(ArretTourneeMobile.objects.filter(tournee=t2, client=self.c1).exists())

    def test_clients_assignes_sans_tournee(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.bureau.post(f'{BASE}/livreurs/{self.livreur.id}/ajouter_client/', {'client_id': self.c1.id},
                             format='json')
            ClientLivreurHebdo.objects.create(client=self.c2, livreur=self.livreur, jour_semaine=self.jour)
        r = self.api.get(f'{BASE}/livreurs/{self.livreur.id}/clients_assignes/')
        self.assertEqual(r.status_code, 200)
        clients = {c['id']: c for c in r.json()['clients']}
        # Seuls les clients du planning de la semaine comptent (même calcul que le téléphone et
        # les tournées) : c1, affecté sans aucun jour de passage, n'y est plus...
        self.assertEqual(set(clients), {self.c2.id})
        self.assertEqual(clients[self.c2.id]['jours_semaine'], [self.jour])
        # ... il est signalé à part dans le planning, pour être complété ou retiré
        r = self.bureau.get(f'{BASE}/livreurs/{self.livreur.id}/planning/')
        self.assertEqual([c['id'] for c in r.json()['clients_sans_jour']], [self.c1.id])


class AvertissementStockVanTests(BaseMobile):
    def test_hausse_sur_commande_affectee_sans_stock_van(self):
        c = Client.objects.create(nom='C', prenom='X', telephone='0')
        cmd = CommandeClient.objects.create(client=c, livreur=self.livreur, reference='CMD-V', statut='confirmed')
        LigneCommandeClient.objects.create(commande=cmd, produit=self.eau, quantite=5,
                                           prix_unitaire_ht=Decimal('10'), taux_tva=0)
        cmd.calculer_totaux()
        ProductStock.objects.create(produit=self.eau, warehouse=self.camion, quantity=6)
        url = f'{BASE}/commandes/modifier_lignes/'
        r = self.api.post(url, {'id': cmd.id, 'lignes': [{'produit': self.eau.id, 'quantite': 6}]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIsNone(r.json()['avertissement_stock_van'])
        r = self.api.post(url, {'id': cmd.id, 'lignes': [{'produit': self.eau.id, 'quantite': 9}]}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn('Eau : 9 à livrer, 6 dans le van', r.json()['avertissement_stock_van'])
        self.assertEqual(ProductStock.objects.get(produit=self.eau, warehouse=self.camion).quantity, 6)
