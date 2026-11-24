"""Planning de la semaine (sans dates) : un prévendeur visite, chaque jour de la semaine, des
secteurs et/ou des clients choisis un par un. Le web, le téléphone et les tournées utilisent le
même calcul : les trois chiffres sont toujours identiques."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Client, Company, Secteur, Warehouse
from .distribution_models import (ArretTourneeMobile, ClientLivreurHebdo, LivreurDistribution,
                                  PlanningHebdomadaire, TourneeMobile)
from .securite_encaissements import _client_du_livreur

BASE = '/API/distribution'


class PlanningSemaineTests(TestCase):
    def setUp(self):
        self.co = Company.objects.create(name='Société A', code='A')
        self.depot = Warehouse.objects.create(company=self.co, name='Camion', code='CAM')
        self.today = timezone.localdate()
        self.jour = self.today.weekday() + 1
        self.autre_jour = self.jour % 7 + 1
        self.user = User.objects.create_user('mourad', password='x')
        self.mourad = LivreurDistribution.objects.create(matricule='M', nom='Mourad', telephone='0',
                                                         user=self.user, entrepot=self.depot)
        self.karim = LivreurDistribution.objects.create(matricule='K', nom='Karim', telephone='0', entrepot=self.depot)
        self.sa = Secteur.objects.create(company=self.co, code='SA', nom='Secteur A')
        self.sb = Secteur.objects.create(company=self.co, code='SB', nom='Secteur B')
        self.a1 = Client.objects.create(company=self.co, nom='A1', prenom='x', telephone='0', secteur=self.sa)
        self.a2 = Client.objects.create(company=self.co, nom='A2', prenom='x', telephone='0', secteur=self.sa)
        self.b1 = Client.objects.create(company=self.co, nom='B1', prenom='x', telephone='0', secteur=self.sb)
        self.seul = Client.objects.create(company=self.co, nom='Seul', prenom='x', telephone='0')   # sans secteur
        self.tournee = TourneeMobile.objects.create(livreur=self.mourad, date_tournee=self.today,
                                                    numero_tournee='T-M', statut='planifiee')
        admin = User.objects.create_superuser('admin', 'a@a.fr', 'x')
        self.bureau = APIClient(); self.bureau.force_authenticate(admin)
        self.tel = APIClient(); self.tel.force_authenticate(self.user)

    # -- outils
    def _post(self, chemin, data, attendu=200):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.bureau.post(f'{BASE}/livreurs/{self.mourad.id}/{chemin}/', data, format='json')
        self.assertEqual(r.status_code, attendu, r.content)
        return r.json()

    def _secteurs(self, jour, ids):
        return self._post('planning/secteurs', {'jour': jour, 'secteurs': ids})

    def _web(self):
        return {c['id'] for c in self.bureau.get(f'{BASE}/livreurs/{self.mourad.id}/clients_assignes/').json()['clients']}

    def _telephone(self):
        r = self.tel.get(f'{BASE}/livreurs/{self.mourad.id}/clients_du_jour/', {'date': self.today.isoformat()})
        return {c['id'] for c in r.json()['clients']}

    def _tournee(self):
        return set(ArretTourneeMobile.objects.filter(tournee=self.tournee).values_list('client_id', flat=True))

    def _planning_jour(self, jour):
        r = self.bureau.get(f'{BASE}/livreurs/{self.mourad.id}/planning/')
        self.assertEqual(r.status_code, 200, r.content)
        return r.json(), r.json()['jours'][jour - 1]

    # -- tests
    def test_par_secteur_les_trois_chiffres_sont_identiques(self):
        self._secteurs(self.jour, [self.sa.id])
        attendu = {self.a1.id, self.a2.id}
        self.assertEqual(self._telephone(), attendu)
        self.assertEqual(self._tournee(), attendu)
        self.assertEqual(self._web(), attendu)
        planning, jour = self._planning_jour(self.jour)
        self.assertEqual(jour['total'], 2)
        self.assertEqual(planning['total_clients'], 2)
        self.assertEqual([s['nom'] for s in jour['secteurs']], ['Secteur A'])

    def test_secteurs_et_clients_choisis_un_par_un_sans_doublon(self):
        self._secteurs(self.jour, [self.sa.id])
        self._post('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.jour]})
        self._post('planning/ajouter-client', {'client_id': self.a1.id, 'jours': [self.jour]})   # déjà via secteur
        attendu = {self.a1.id, self.a2.id, self.seul.id}
        self.assertEqual(self._telephone(), attendu)
        self.assertEqual(self._tournee(), attendu)
        _, jour = self._planning_jour(self.jour)
        self.assertEqual(jour['total'], 3)
        self.assertEqual(len(jour['liste']), 3)

    def test_jour_different_non_visite(self):
        self._secteurs(self.autre_jour, [self.sb.id])
        self.assertEqual(self._telephone(), set())
        self.assertEqual(self._tournee(), set())
        self.assertEqual(self._web(), {self.b1.id})   # client de la semaine, pas d'aujourd'hui

    def test_changer_le_secteur_d_un_client_met_a_jour_la_tournee(self):
        self._secteurs(self.jour, [self.sa.id])
        with self.captureOnCommitCallbacks(execute=True):
            self.b1.secteur = self.sa
            self.b1.save()
        self.assertIn(self.b1.id, self._tournee())
        with self.captureOnCommitCallbacks(execute=True):
            self.a2.secteur = self.sb
            self.a2.save()
        self.assertEqual(self._tournee(), {self.a1.id, self.b1.id})
        self.assertEqual(self._telephone(), self._tournee())

    def test_nouveau_client_du_secteur_ajoute_a_la_tournee(self):
        self._secteurs(self.jour, [self.sa.id])
        with self.captureOnCommitCallbacks(execute=True):
            nouveau = Client.objects.create(company=self.co, nom='Nouveau', prenom='x', telephone='0', secteur=self.sa)
        self.assertIn(nouveau.id, self._tournee())

    def test_retirer_un_secteur_retire_les_arrets_en_attente(self):
        self._secteurs(self.jour, [self.sa.id, self.sb.id])
        ArretTourneeMobile.objects.filter(tournee=self.tournee, client=self.a1).update(statut='livre')
        self._secteurs(self.jour, [self.sb.id])
        # a2 (en attente) disparaît ; a1, déjà visité, est conservé
        self.assertEqual(self._tournee(), {self.a1.id, self.b1.id})

    def test_conflit_avec_un_autre_prevendeur_puis_transfert(self):
        ClientLivreurHebdo.objects.create(client=self.seul, livreur=self.karim, jour_semaine=self.jour,
                                          company=self.co)
        r = self._post('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.jour]}, attendu=409)
        self.assertEqual(r['conflits'][0]['livreur_nom'], 'Karim')
        self.assertNotIn(self.seul.id, self._telephone())
        self._post('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.jour], 'transferer': True})
        self.assertEqual(self._telephone(), {self.seul.id})
        self.assertFalse(ClientLivreurHebdo.objects.filter(client=self.seul, livreur=self.karim).exists())

    def test_retirer_un_client_d_un_jour(self):
        self._post('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.jour, self.autre_jour]})
        self.assertEqual(self._tournee(), {self.seul.id})
        self._post('planning/retirer-client', {'client_id': self.seul.id, 'jour': self.jour})
        self.assertEqual(self._tournee(), set())
        self.assertEqual(self._telephone(), set())
        self.assertEqual(self._web(), {self.seul.id})   # toujours visité l'autre jour
        self.assertTrue(self.mourad.clients_assignes.filter(pk=self.seul.pk).exists())
        self._post('planning/retirer-client', {'client_id': self.seul.id})
        self.assertEqual(self._web(), set())
        self.assertFalse(self.mourad.clients_assignes.filter(pk=self.seul.pk).exists())

    def test_retirer_un_client_du_secteur_puis_le_remettre(self):
        self._secteurs(self.jour, [self.sa.id])
        r = self._post('planning/retirer-client', {'client_id': self.a1.id, 'jour': self.jour})
        self.assertIn('Secteur A', r['message'])
        # a1 n'est plus visité, a2 (même secteur) l'est toujours — web, téléphone, tournée identiques
        self.assertEqual(self._telephone(), {self.a2.id})
        self.assertEqual(self._tournee(), {self.a2.id})
        self.assertEqual(self._web(), {self.a2.id})
        _, jour = self._planning_jour(self.jour)
        self.assertEqual([(c['id'], c['chez']) for c in jour['exclus']], [(self.a1.id, None)])
        # un nouveau client du secteur reste ajouté automatiquement
        with self.captureOnCommitCallbacks(execute=True):
            nouveau = Client.objects.create(company=self.co, nom='A3', prenom='x', telephone='0', secteur=self.sa)
        self.assertEqual(self._tournee(), {self.a2.id, nouveau.id})
        self._post('planning/remettre-client', {'client_id': self.a1.id, 'jour': self.jour})
        self.assertEqual(self._telephone(), {self.a1.id, self.a2.id, nouveau.id})
        self.assertEqual(self._tournee(), self._telephone())

    def test_donner_un_client_du_secteur_a_un_autre_prevendeur(self):
        self._secteurs(self.jour, [self.sa.id])
        karim_tournee = TourneeMobile.objects.create(livreur=self.karim, date_tournee=self.today,
                                                     numero_tournee='T-K', statut='planifiee')
        url = f'{BASE}/livreurs/{self.karim.id}/planning/ajouter-client/'
        # sans confirmation : conflit, car Mourad le visite via son secteur
        r = self.bureau.post(url, {'client_id': self.a1.id, 'jours': [self.jour]}, format='json')
        self.assertEqual(r.status_code, 409, r.content)
        self.assertEqual(r.json()['conflits'][0]['livreur_nom'], 'Mourad')
        self.assertEqual(r.json()['conflits'][0]['secteur_nom'], 'Secteur A')
        with self.captureOnCommitCallbacks(execute=True):
            r = self.bureau.post(url, {'client_id': self.a1.id, 'jours': [self.jour], 'transferer': True}, format='json')
        self.assertEqual(r.status_code, 200, r.content)
        # Mourad ne le visite plus (téléphone + tournée), Karim oui
        self.assertEqual(self._telephone(), {self.a2.id})
        self.assertEqual(self._tournee(), {self.a2.id})
        self.assertEqual(set(ArretTourneeMobile.objects.filter(tournee=karim_tournee).values_list('client_id', flat=True)),
                         {self.a1.id})
        _, jour = self._planning_jour(self.jour)
        self.assertEqual([(c['id'], c['chez']) for c in jour['exclus']], [(self.a1.id, 'Karim')])
        # Mourad le reprend : il revient dans son secteur et Karim le perd
        self._post('planning/remettre-client', {'client_id': self.a1.id, 'jour': self.jour})
        self.assertEqual(self._tournee(), {self.a1.id, self.a2.id})
        self.assertEqual(set(ArretTourneeMobile.objects.filter(tournee=karim_tournee).values_list('client_id', flat=True)), set())

    def test_reajouter_un_client_retire_du_secteur(self):
        self._secteurs(self.jour, [self.sa.id])
        self._post('planning/retirer-client', {'client_id': self.a1.id, 'jour': self.jour})
        self._post('planning/ajouter-client', {'client_id': self.a1.id, 'jours': [self.jour]})
        self.assertEqual(self._telephone(), {self.a1.id, self.a2.id})
        _, jour = self._planning_jour(self.jour)
        self.assertEqual(jour['exclus'], [])

    # -- Un client n'a qu'UN prévendeur par jour de la semaine
    def _post_karim(self, chemin, data, attendu=200):
        with self.captureOnCommitCallbacks(execute=True):
            r = self.bureau.post(f'{BASE}/livreurs/{self.karim.id}/{chemin}/', data, format='json')
        self.assertEqual(r.status_code, attendu, r.content)
        return r.json()

    def _karim(self, jour=None):
        from .distribution_prix_stock import clients_planifies
        return {it['client'].id for it in clients_planifies(self.karim.id, jour or self.jour)}

    def test_meme_secteur_refuse_puis_transfere(self):
        self._secteurs(self.jour, [self.sa.id])
        r = self._post_karim('planning/secteurs', {'jour': self.jour, 'secteurs': [self.sa.id]}, attendu=409)
        self.assertEqual((r['conflits'][0]['livreur_nom'], r['conflits'][0]['secteur_nom']), ('Mourad', 'Secteur A'))
        self.assertEqual(self._karim(), set())
        self._post_karim('planning/secteurs', {'jour': self.jour, 'secteurs': [self.sa.id], 'transferer': True})
        self.assertEqual(self._karim(), {self.a1.id, self.a2.id})
        self.assertEqual(self._telephone(), set())
        self.assertEqual(self._tournee(), set())
        # autre jour : le même secteur reste possible
        self._post_karim('planning/secteurs', {'jour': self.autre_jour, 'secteurs': [self.sa.id]})
        self._secteurs(self.autre_jour, [self.sb.id])

    def test_retirer_un_secteur_ne_bloque_pas_a_cause_d_un_ancien_doublon(self):
        self._secteurs(self.jour, [self.sa.id, self.sb.id])
        # ancien doublon créé avant la vérification (directement en base)
        p = PlanningHebdomadaire.objects.create(livreur=self.karim, jour_semaine=self.jour, company=self.co)
        p.secteurs.add(self.sa)
        self._secteurs(self.jour, [self.sa.id])   # on retire seulement Secteur B : pas de 409
        _, jour = self._planning_jour(self.jour)
        self.assertEqual({(d['id'], tuple(d['chez'])) for d in jour['doublons']},
                         {(self.a1.id, ('Karim',)), (self.a2.id, ('Karim',))})

    def test_jamais_un_client_chez_deux_prevendeurs_le_meme_jour(self):
        self._secteurs(self.jour, [self.sa.id])
        self._post_karim('planning/ajouter-client', {'client_id': self.a1.id, 'jours': [self.jour], 'transferer': True})
        self._post_karim('planning/secteurs', {'jour': self.jour, 'secteurs': [self.sb.id]})
        self._post('planning/ajouter-client', {'client_id': self.b1.id, 'jours': [self.jour], 'transferer': True})
        self._post_karim('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.jour]})
        self._post('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.jour], 'transferer': True})
        mourad, karim = self._telephone(), self._karim()
        self.assertEqual(mourad & karim, set(), (mourad, karim))
        self.assertEqual(mourad, {self.a2.id, self.b1.id, self.seul.id})
        self.assertEqual(karim, {self.a1.id})
        _, jour = self._planning_jour(self.jour)
        self.assertEqual(jour['doublons'], [])

    def test_vue_d_ensemble_des_jours_pris_par_tous_les_prevendeurs(self):
        self._secteurs(self.jour, [self.sa.id])
        self._post_karim('planning/ajouter-client', {'client_id': self.seul.id, 'jours': [self.autre_jour]})
        r = self.bureau.get(f'{BASE}/livreurs/planning-clients/')
        self.assertEqual(r.status_code, 200, r.content)
        clients = r.json()['clients']
        self.assertEqual([(e['jour'], e['livreur_nom']) for e in clients[str(self.a1.id)]], [(self.jour, 'Mourad')])
        self.assertEqual([(e['jour'], e['livreur_nom']) for e in clients[str(self.seul.id)]], [(self.autre_jour, 'Karim')])
        self.assertEqual([(e['jour'], e['livreur_nom']) for e in r.json()['secteurs'][str(self.sa.id)]], [(self.jour, 'Mourad')])

    def test_jour_invalide_et_secteur_inconnu(self):
        self._post('planning/secteurs', {'jour': 9, 'secteurs': []}, attendu=400)
        self._post('planning/secteurs', {'jour': self.jour, 'secteurs': [99999]}, attendu=400)

    def test_un_seul_planning_par_jour(self):
        self._secteurs(self.jour, [self.sa.id])
        self._secteurs(self.jour, [self.sb.id])
        self.assertEqual(PlanningHebdomadaire.objects.filter(livreur=self.mourad, jour_semaine=self.jour).count(), 1)
        self.assertEqual(self._telephone(), {self.b1.id})

    def test_prevendeur_peut_encaisser_chez_un_client_de_son_secteur(self):
        self.assertFalse(_client_du_livreur(self.mourad, self.a1))
        self._secteurs(self.autre_jour, [self.sa.id])
        self.assertTrue(_client_du_livreur(self.mourad, self.a1))

    def test_liste_des_clients_visible_par_le_telephone(self):
        self._secteurs(self.autre_jour, [self.sb.id])
        r = self.tel.get('/API/clients/')
        ids = {c['id'] for c in (r.json() if isinstance(r.json(), list) else r.json().get('results', []))}
        self.assertIn(self.b1.id, ids)
