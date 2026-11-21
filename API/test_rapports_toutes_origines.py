"""Point 18 : les rapports « Ventes » et « Bénéfices » du PC comptent les ventes du PC, les ventes
du téléphone et les commandes livrées (avant : seulement les ventes du PC)."""
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import Achat, Categorie, Client, Fournisseur, LigneVente, Produit, Vente, Warehouse
from .distribution_models import (CommandeClient, LigneCommandeClient, LigneVenteTourneeMobile,
                                  LivreurDistribution, TourneeMobile, VenteTourneeMobile)
from .reports import (_get_profit_data, generate_profit_report_excel, generate_profit_report_pdf,
                      generate_sales_report_excel, generate_sales_report_pdf, quantites_vendues,
                      ventes_toutes_origines)


def _dt(j, h=10):
    return timezone.make_aware(datetime(2026, 11, j, h, 0))


class RapportsToutesOriginesTests(TestCase):
    def setUp(self):
        cat = Categorie.objects.create(nom='Boissons')
        self.eau = Produit.objects.create(reference='EAU', code_barre='1', designation='Eau',
                                          prixU=Decimal('10'), categorie=cat)
        f = Fournisseur.objects.create(libelle='Fourn')
        depot = Warehouse.objects.create(name='Dépôt', code='DEP')
        Achat.objects.create(produit=self.eau, fournisseur=f, warehouse=depot, quantite=100,
                             prix_achat=Decimal('6'), date_Achat=date(2026, 11, 1))
        self.client_ = Client.objects.create(nom='Client', prenom='A', telephone='0')
        livreur = LivreurDistribution.objects.create(matricule='L1', nom='Ahmed', telephone='0')
        tournee = TourneeMobile.objects.create(livreur=livreur, date_tournee=date(2026, 11, 10), numero_tournee='T1')

        # PC : 2 x 10 = 20 (validée), + une vente brouillon ignorée
        v = Vente.objects.create(client=self.client_, statut='completed', total_ht=Decimal('20'),
                                 total_ttc=Decimal('20'), date_vente=_dt(10))
        LigneVente.objects.create(vente=v, produit=self.eau, quantite=2, prixU_snapshot=Decimal('10'))
        Vente.objects.filter(pk=v.pk).update(date_vente=_dt(10, 23))   # tard le dernier jour
        brouillon = Vente.objects.create(client=self.client_, statut='draft', total_ttc=Decimal('999'))
        LigneVente.objects.create(vente=brouillon, produit=self.eau, quantite=50, prixU_snapshot=Decimal('10'))

        # Téléphone : 3 x 10 = 30
        vm = VenteTourneeMobile.objects.create(tournee=tournee, client=self.client_, numero_vente='VM-1',
                                               date_vente=_dt(10), type_paiement='especes',
                                               montant_ht=Decimal('30'), montant_total=Decimal('30'))
        LigneVenteTourneeMobile.objects.create(vente=vm, produit=self.eau, quantite=3, prix_unitaire=Decimal('10'),
                                               taux_tva=0, montant_ht=Decimal('30'), montant_tva=0,
                                               montant_ttc=Decimal('30'))

        # Commande livrée : 5 x 10 = 50, + une commande en attente ignorée
        c = CommandeClient.objects.create(client=self.client_, livreur=livreur, reference='CMD-1')
        LigneCommandeClient.objects.create(commande=c, produit=self.eau, quantite=5,
                                           prix_unitaire_ht=Decimal('10'), taux_tva=0)
        c.calculer_totaux()
        CommandeClient.objects.filter(pk=c.pk).update(statut='delivered', date_livraison_reelle=_dt(10))
        c2 = CommandeClient.objects.create(client=self.client_, livreur=livreur, reference='CMD-2')
        LigneCommandeClient.objects.create(commande=c2, produit=self.eau, quantite=40,
                                           prix_unitaire_ht=Decimal('10'), taux_tva=0)

    def test_rapport_ventes_toutes_origines(self):
        docs = ventes_toutes_origines(date(2026, 11, 10), date(2026, 11, 10))
        self.assertEqual(sorted((d['origine'], float(d['ttc'])) for d in docs),
                         [('commande', 50.0), ('pc', 20.0), ('telephone', 30.0)])
        # Hors période
        self.assertEqual(ventes_toutes_origines(date(2026, 11, 11), date(2026, 11, 30)), [])

    def test_quantites_et_benefice_realise(self):
        vendus, par_origine = quantites_vendues()
        self.assertEqual(vendus[self.eau.id]['qte'], Decimal('10'))      # 2 + 3 + 5
        self.assertEqual(vendus[self.eau.id]['ca'], Decimal('100'))
        self.assertEqual({k: float(v) for k, v in par_origine.items()},
                         {'pc': 20.0, 'telephone': 30.0, 'commande': 50.0})
        rows, _ = _get_profit_data()
        eau = next(r for r in rows if r['reference'] == 'EAU')
        self.assertEqual(eau['benefice_realise'], Decimal('40'))         # 100 - 10 x 6

    def test_exports_generes(self):
        for gen in (lambda: generate_sales_report_excel(date(2026, 11, 1), date(2026, 11, 30)),
                    lambda: generate_sales_report_pdf(date(2026, 11, 1), date(2026, 11, 30)),
                    generate_profit_report_excel, generate_profit_report_pdf):
            contenu = gen()
            contenu = contenu.getvalue() if hasattr(contenu, 'getvalue') else contenu
            self.assertTrue(len(contenu) > 500)
