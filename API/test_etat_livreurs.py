"""Tests de l'état des livreurs (API/etat_livreurs.py) : net, écart, à contrôler."""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .etat_livreurs import calculer_etat_livreurs
from .distribution_models import LivreurDistribution, RapportCaisseMobile, TourneeMobile

DEBUT, FIN = date(2026, 9, 1), date(2026, 9, 30)


class EtatLivreursTests(TestCase):
    def setUp(self):
        self._n = 0

    def livreur(self, nom, statut='actif'):
        self._n += 1
        return LivreurDistribution.objects.create(matricule=f'L{self._n}', nom=nom, telephone='0', statut=statut)

    def tournee(self, livreur, jour=10, statut='terminee', rapport=None):
        self._n += 1
        t = TourneeMobile.objects.create(livreur=livreur, date_tournee=date(2026, 9, jour),
                                         numero_tournee=f'T{self._n}', statut=statut)
        if rapport is not None:
            fonds, especes, depenses, reel, statut_r = rapport
            r = RapportCaisseMobile(tournee=t, fonds_depart=Decimal(fonds), total_especes=Decimal(especes),
                                    carburant=Decimal(depenses), solde_final_reel=Decimal(reel), statut=statut_r)
            r.calculer_totaux()   # calcule théorique et écart, et enregistre
        return t

    def etat(self, livreur, **kw):
        res = calculer_etat_livreurs(DEBUT, FIN, **kw)
        return next(l for l in res['livreurs'] if l['livreur_id'] == livreur.id)

    def test_net_quand_rapporte_egal_attendu(self):
        l = self.livreur('Net')
        self.tournee(l, rapport=('1000', '5000', '200', '5800', 'valide'))   # attendu 5800
        e = self.etat(l)
        self.assertEqual(e['etat'], 'net')
        self.assertEqual(e['ecart_net'], 0)
        self.assertEqual(e['tournees'][0]['rapport']['solde_theorique'], 5800)

    def test_ecart_tolere_reste_net(self):
        l = self.livreur('Arrondi')
        self.tournee(l, rapport=('0', '1000', '0', '995', 'valide'))   # -5 DA : dans la tolérance
        self.assertEqual(self.etat(l)['etat'], 'net')

    def test_manquant_et_excedent_cumules(self):
        l = self.livreur('Ecart')
        self.tournee(l, jour=10, rapport=('0', '1000', '0', '700', 'valide'))   # manquant 300
        self.tournee(l, jour=11, rapport=('0', '1000', '0', '1050', 'valide'))  # excédent 50
        self.tournee(l, jour=12, rapport=('0', '1000', '0', '1000', 'valide'))  # net
        e = self.etat(l)
        self.assertEqual(e['etat'], 'ecart')
        self.assertEqual((e['manquant'], e['excedent'], e['ecart_net']), (300, 50, -250))
        self.assertEqual(e['nb_ecarts'], 2)
        self.assertEqual([t['etat'] for t in e['tournees']], ['net', 'ecart', 'ecart'])  # plus récente d'abord
        self.assertIn('Manquant de 300,00 DA', e['tournees'][2]['motif'])

    def test_tournee_sans_rapport_a_controler(self):
        l = self.livreur('Sans rapport')
        self.tournee(l, rapport=('0', '100', '0', '100', 'valide'))
        self.tournee(l, jour=11)   # terminée, pas de rapport
        e = self.etat(l)
        self.assertEqual(e['etat'], 'a_controler')
        self.assertIsNone(e['tournees'][0]['rapport'])

    def test_rapport_ouvert_a_controler(self):
        l = self.livreur('Ouvert')
        self.tournee(l, rapport=('0', '100', '0', '100', 'ouvert'))
        self.assertEqual(self.etat(l)['etat'], 'a_controler')

    def test_ecart_prioritaire_sur_a_controler(self):
        l = self.livreur('Les deux')
        self.tournee(l, rapport=('0', '100', '0', '0', 'valide'))
        self.tournee(l, jour=11)
        self.assertEqual(self.etat(l)['etat'], 'ecart')

    def test_tournees_en_cours_et_hors_periode_ignorees(self):
        l = self.livreur('Rien')
        self.tournee(l, statut='en_cours')
        t = self.tournee(l, jour=11, rapport=('0', '100', '0', '0', 'valide'))
        TourneeMobile.objects.filter(pk=t.pk).update(date_tournee=date(2026, 8, 31))
        e = self.etat(l)
        self.assertEqual((e['etat'], e['nb_tournees']), ('aucune', 0))

    def test_livreur_inactif_sans_tournee_masque_et_tri(self):
        inactif = self.livreur('Ancien', statut='inactif')
        net = self.livreur('A net')
        ecart = self.livreur('Z ecart')
        self.tournee(net, rapport=('0', '100', '0', '100', 'valide'))
        self.tournee(ecart, rapport=('0', '100', '0', '0', 'valide'))
        res = calculer_etat_livreurs(DEBUT, FIN)
        ids = [l['livreur_id'] for l in res['livreurs']]
        self.assertNotIn(inactif.id, ids)
        self.assertEqual(ids[:2], [ecart.id, net.id])   # les écarts d'abord
        self.assertEqual(res['synthese']['ecart'], 1)
        self.assertEqual(res['synthese']['manquant_total'], 100)

    def test_api(self):
        l = self.livreur('Api')
        self.tournee(l, rapport=('0', '100', '0', '80', 'valide'))
        client = APIClient()
        client.force_authenticate(User.objects.create_user('chef', password='x', is_staff=True))
        r = client.get('/API/distribution/etat-livreurs/', {'date_debut': '2026-09-01', 'date_fin': '2026-09-30'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['livreurs'][0]['etat'], 'ecart')
        self.assertEqual(client.get('/API/distribution/etat-livreurs/', {'date_debut': 'x'}).status_code, 400)
        self.assertEqual(APIClient().get('/API/distribution/etat-livreurs/').status_code, 401)

    def test_utilisateur_non_admin_ne_voit_que_son_entreprise(self):
        from .models import Company, UserProfile
        a = Company.objects.create(name='Entreprise A', code='ENTA')
        b = Company.objects.create(name='Entreprise B', code='ENTB')
        la, lb = self.livreur('Livreur A'), self.livreur('Livreur B')
        ta = self.tournee(la, rapport=('0', '100', '0', '50', 'valide'))
        tb = self.tournee(lb, rapport=('0', '100', '0', '20', 'valide'))
        TourneeMobile.objects.filter(pk=ta.pk).update(company=a)
        TourneeMobile.objects.filter(pk=tb.pk).update(company=b)
        user = User.objects.create_user('caissier', password='x')   # ni staff ni superuser
        UserProfile.objects.update_or_create(user=user, defaults={'company': a})
        client = APIClient()
        client.login(username='caissier', password='x')   # session : le middleware pose request.company
        r = client.get('/API/distribution/etat-livreurs/', {'date_debut': '2026-09-01', 'date_fin': '2026-09-30'})
        self.assertEqual(r.status_code, 200)
        noms = [l['nom'] for l in r.json()['livreurs']]
        self.assertIn('Livreur A', noms)
        self.assertNotIn('Livreur B', noms)
        self.assertEqual(r.json()['synthese']['manquant_total'], 50)
