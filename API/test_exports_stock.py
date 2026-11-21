"""États du stock (valorisation + inventaire) en PDF et Excel : contenu, mise en page, totaux."""
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from openpyxl import load_workbook
from rest_framework.test import APIClient

from .models import (Categorie, Company, ProductStock, Produit, SystemConfig, UserProfile, Warehouse)
from .reports import (donnees_etat_stock, fmt_da, generate_inventory_report_pdf,
                      generate_stock_valuation_pdf, nom_societe, statut_stock)

XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def texte_pdf(contenu):
    """Texte de toutes les pages (pymupdf si présent, sinon on se contente de l'en-tête %PDF)."""
    try:
        import pymupdf
    except ImportError:  # pragma: no cover
        try:
            import fitz as pymupdf
        except ImportError:
            return None
    doc = pymupdf.open(stream=contenu, filetype='pdf')
    return '\n'.join(page.get_text() for page in doc)


class ExportsEtatStockTests(TestCase):
    def setUp(self):
        self.ent = Company.objects.create(name='Société Test', code='STE')
        autre = Company.objects.create(name='Autre', code='AUT')
        SystemConfig.objects.create(company=self.ent, ticket_company_name='Rayanne Distribution')
        self.user = User.objects.create_user('gerant', password='mdp-test')
        UserProfile.objects.update_or_create(user=self.user, defaults={'company': self.ent, 'role': 'employee'})
        cat = Categorie.objects.create(nom='Boissons')
        self.depot = Warehouse.objects.create(name='Dépôt Central', code='DC', company=self.ent)
        self.van = Warehouse.objects.create(name='Camion 1', code='VAN-01', company=self.ent)
        self.inactif = Warehouse.objects.create(name='Ancien dépôt', code='OLD', company=self.ent, is_active=False)
        etranger = Warehouse.objects.create(name='Dépôt autre', code='X', company=autre)

        def produit(ref, prix, quantite_fiche, **kw):
            return Produit.objects.create(reference=ref, code_barre=ref, designation=f'Produit {ref} avec une '
                                          'désignation volontairement très longue pour tester le retour à la ligne',
                                          prixU=Decimal(prix), categorie=cat, company=self.ent,
                                          quantite=quantite_fiche, seuil_alerte=10, seuil_critique=5, **kw)
        # Produit.quantite (fiche) volontairement différent du stock des dépôts
        self.eau = produit('EAU', '1250.50', 0)
        self.jus = produit('JUS', '80', 999)
        self.sel = produit('SEL', '10', 3)           # aucun stock en dépôt -> rupture à l'inventaire
        ProductStock.objects.create(produit=self.eau, warehouse=self.depot, quantity=1000)
        ProductStock.objects.create(produit=self.eau, warehouse=self.van, quantity=20)
        ProductStock.objects.create(produit=self.jus, warehouse=self.depot, quantity=4)
        ProductStock.objects.create(produit=self.jus, warehouse=self.inactif, quantity=500)   # ignoré
        ProductStock.objects.create(produit=self.jus, warehouse=etranger, quantity=700)       # autre entreprise
        self.c = APIClient()
        self.c.login(username='gerant', password='mdp-test')

    # ------------------------------------------------------------ données
    def test_donnees_depots_actifs_et_statut_sur_quantite_affichee(self):
        d = donnees_etat_stock(self.ent)
        lignes = {l['reference']: l for l in d['lignes']}
        self.assertEqual(lignes['EAU']['qty'], 1020)                 # dépôt + van, pas la fiche (0)
        self.assertEqual(lignes['EAU']['statut'], 'normal')          # avant : out_of_stock (fiche à 0)
        self.assertEqual(lignes['JUS']['qty'], 4)                    # dépôt inactif / autre entreprise exclus
        self.assertEqual(lignes['JUS']['statut'], 'critique')
        self.assertNotIn('SEL', lignes)                               # valorisation : stock > 0 seulement
        self.assertEqual(d['total_qty'], 1024)
        self.assertEqual(d['total_valeur'], Decimal('1020') * Decimal('1250.50') + 4 * 80)
        rep = {r['nom']: r for r in d['repartition']}
        self.assertEqual(rep['Camion 1']['type'], 'Van')
        self.assertEqual(rep['Dépôt Central']['type'], 'Dépôt')
        self.assertNotIn('Ancien dépôt', rep)

    def test_donnees_par_depot_et_inventaire(self):
        d = donnees_etat_stock(self.ent, par_depot=True)
        self.assertEqual([(g['nom'], len(l)) for g, l in d['groupes']], [('Camion 1', 1), ('Dépôt Central', 2)])
        self.assertEqual(d['total_qty'], 1024)
        inv = donnees_etat_stock(self.ent, warehouse_id=self.van.pk, inclure_zero=True)
        q = {l['reference']: (l['qty'], l['statut']) for l in inv['lignes']}
        self.assertEqual(q, {'EAU': (20, 'normal'), 'JUS': (0, 'rupture'), 'SEL': (0, 'rupture')})

    def test_formats_et_societe(self):
        self.assertEqual(statut_stock(0, 10, 5), 'rupture')
        self.assertEqual(statut_stock(5, 10, 5), 'critique')
        self.assertEqual(statut_stock(10, 10, 5), 'alerte')
        self.assertEqual(statut_stock(11, 10, 5), 'normal')
        self.assertEqual(fmt_da(Decimal('1234567.5')), '1 234 567,50 DA')
        self.assertEqual(nom_societe(self.ent), 'Rayanne Distribution')
        SystemConfig.objects.filter(company=self.ent).update(ticket_company_name='')
        self.assertEqual(nom_societe(self.ent), 'Société Test')

    # ------------------------------------------------------------ PDF
    def test_pdf_valorisation(self):
        r = self.c.get('/reports/stock-valuation/', {'format': 'pdf'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename="valorisation_stock_', r['Content-Disposition'])
        self.assertTrue(r.content.startswith(b'%PDF'))
        texte = texte_pdf(r.content)
        if texte is not None:
            self.assertIn('Rayanne Distribution', texte)
            self.assertNotIn('GestionStock', texte)
            self.assertIn('Page 1 / ', texte)
            self.assertIn('1 275 830,00 DA', texte)     # 1020 x 1250,50 + 4 x 80
            self.assertIn('Critique', texte)
            self.assertNotIn('out_of_stock', texte)
            self.assertIn('Répartition par dépôt', texte)

    def test_pdf_par_depot_et_inline(self):
        r = self.c.get('/reports/stock-valuation/', {'format': 'pdf', 'par_depot': '1', 'inline': '1'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Disposition'].startswith('inline;'))
        texte = texte_pdf(r.content)
        if texte is not None:
            self.assertIn('Van : Camion 1', texte)
            self.assertIn('Sous-total Dépôt Central', texte)
            self.assertNotIn('Ancien dépôt', texte)

    def test_pdf_longue_liste_entete_repete(self):
        cat = Categorie.objects.first()
        for i in range(120):
            p = Produit.objects.create(reference=f'P{i:03}', code_barre=f'C{i}', designation=f'Article {i}',
                                       prixU=Decimal('1'), categorie=cat, company=self.ent)
            ProductStock.objects.create(produit=p, warehouse=self.depot, quantity=50)
        contenu = generate_inventory_report_pdf(self.ent).read()
        try:
            import pymupdf
        except ImportError:  # pragma: no cover
            return
        pages = [p.get_text() for p in pymupdf.open(stream=contenu, filetype='pdf')]
        self.assertGreaterEqual(len(pages), 3)
        n = len(pages)
        for i, texte in enumerate(pages, start=1):
            self.assertIn(f'Page {i} / {n}', texte)                  # pied « Page X / Y »
            if i < n:
                self.assertIn('Désignation', texte)                  # en-tête répété (repeatRows)

    # ------------------------------------------------------------ Excel
    def classeur(self, r):
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], XLSX)
        return load_workbook(BytesIO(r.content))

    def test_excel_valorisation(self):
        wb = self.classeur(self.c.get('/reports/stock-valuation/', {'format': 'excel'}))
        ws = wb.active
        self.assertIn('A1:G1', [str(m) for m in ws.merged_cells.ranges])      # titre sur toutes les colonnes
        self.assertEqual(ws['B2'].value, 'Rayanne Distribution')
        self.assertIsInstance(ws['B3'].value, datetime)                       # vraie date
        h = 7
        self.assertEqual([c.value for c in ws[h]],
                         ['Référence', 'Désignation', 'Catégorie', 'Qté', 'Prix de vente unit.',
                          'Valeur du stock', 'Statut'])
        self.assertEqual(ws.freeze_panes, f'A{h + 1}')
        self.assertEqual(ws.auto_filter.ref, f'A{h}:G{h + 2}')
        self.assertEqual(ws.print_title_rows, f'${h}:${h}')
        self.assertEqual(ws.page_setup.orientation, 'landscape')
        self.assertTrue(ws.sheet_properties.pageSetUpPr.fitToPage)
        lignes = {ws.cell(row=r, column=1).value: r for r in range(h + 1, h + 3)}
        r_eau = lignes['EAU']
        self.assertEqual(ws.cell(row=r_eau, column=4).value, 1020)
        self.assertEqual(ws.cell(row=r_eau, column=6).number_format, '#,##0.00 "DA"')
        self.assertEqual(ws.cell(row=lignes['JUS'], column=7).value, 'Critique')
        total = h + 3
        self.assertEqual(ws.cell(row=total, column=1).value, 'TOTAL')
        self.assertEqual(ws.cell(row=total, column=4).value, f'=SUBTOTAL(9,D{h + 1}:D{h + 2})')
        self.assertEqual(ws.cell(row=total, column=6).value, f'=SUBTOTAL(9,F{h + 1}:F{h + 2})')
        somme = sum(ws.cell(row=r, column=6).value for r in range(h + 1, h + 3))
        self.assertAlmostEqual(somme, 1020 * 1250.50 + 4 * 80, places=2)
        dep = wb['Par dépôt']
        self.assertEqual({dep.cell(row=r, column=1).value: dep.cell(row=r, column=3).value for r in (2, 3)},
                         {'Camion 1': 'Van', 'Dépôt Central': 'Dépôt'})
        self.assertEqual(dep['E4'].value, '=SUM(E2:E3)')

    def test_excel_inventaire_depot_filtre(self):
        wb = self.classeur(self.c.get('/reports/inventory/', {'format': 'excel', 'warehouse': self.van.pk}))
        ws = wb.active
        self.assertIn('A1:J1', [str(m) for m in ws.merged_cells.ranges])
        self.assertIn('Camion 1', ws['B4'].value)
        data = {ws.cell(row=r, column=1).value: (ws.cell(row=r, column=6).value, ws.cell(row=r, column=10).value)
                for r in range(8, 11)}
        self.assertEqual(data, {'EAU': (20, 'Normal'), 'JUS': (0, 'Rupture'), 'SEL': (0, 'Rupture')})
        self.assertEqual(ws['F11'].value, '=SUBTOTAL(9,F8:F10)')
        self.assertEqual(ws['I11'].value, '=SUBTOTAL(9,I8:I10)')

    # ------------------------------------------------------------ droits / erreurs / route API
    def test_prix_achat_reserve(self):
        r = self.c.get('/reports/stock-valuation/', {'format': 'pdf', 'prix': 'achat'})
        self.assertEqual(r.status_code, 403)

    def test_depot_invalide_ou_d_une_autre_entreprise(self):
        self.assertEqual(self.c.get('/reports/inventory/', {'warehouse': 'abc'}).status_code, 404)
        autre = Warehouse.objects.get(code='X')
        self.assertEqual(self.c.get('/reports/stock-valuation/', {'warehouse': autre.pk}).status_code, 404)

    def test_route_api(self):
        r = self.c.get('/API/reports/stock-valuation/', {'format': 'excel', 'par_depot': '1'})
        wb = self.classeur(r)
        self.assertEqual(wb.active['A7'].value, 'Dépôt')
        r = self.c.get('/API/reports/inventory/', {'format': 'pdf', 'warehouse': self.depot.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_generateurs_sans_requete(self):
        # Appel direct (staff / toutes entreprises) : pas d'erreur, nom de société par défaut
        self.assertTrue(generate_stock_valuation_pdf().read().startswith(b'%PDF'))
