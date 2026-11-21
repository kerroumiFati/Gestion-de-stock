"""
Vues simplifiées pour l'export de rapports
"""
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from datetime import datetime
from API.reports import (
    generate_stock_valuation_excel,
    generate_stock_valuation_pdf,
    generate_sales_report_excel,
    generate_sales_report_pdf,
    generate_inventory_report_excel,
    generate_inventory_report_pdf,
    generate_profit_report_excel,
    generate_profit_report_pdf,
    nom_societe_rapport,
    parametres_etat_stock,
    perimetre_rapport,
)
from API.audit import log_event
from API.models import Warehouse


XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _reponse_fichier(buffer, export_format, base, inline=False):
    """Réponse fichier (PDF ou .xlsx) avec un nom horodaté."""
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    if export_format == 'pdf':
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f'{base}_{horodatage}.pdf'
    else:
        response = HttpResponse(buffer, content_type=XLSX)
        filename = f'{base}_{horodatage}.xlsx'
    response['Content-Disposition'] = f'{"inline" if inline else "attachment"}; filename="{filename}"'
    return response, filename


def _texte(message, status):
    return HttpResponse(message, status=status, content_type='text/plain; charset=utf-8')


@login_required
def export_stock_valuation(request):
    """Export de l'état de valorisation du stock.
    GET : format=excel|pdf, warehouse=<id>, par_depot=1 (détail et sous-totaux par dépôt),
    prix=vente|achat (achat : administrateur + PIN bénéfices), inline=1 (PDF ouvert dans le navigateur)."""
    from API.benefices_acces import AccesRefuse
    export_format = request.GET.get('format', 'excel').lower()
    try:
        warehouse_id, par_depot, prix = parametres_etat_stock(request)
        company = perimetre_rapport(request)
        societe = nom_societe_rapport(request)
        generer = generate_stock_valuation_pdf if export_format == 'pdf' else generate_stock_valuation_excel
        buffer = generer(warehouse_id, company, par_depot=par_depot, prix=prix, societe=societe)
    except AccesRefuse as e:
        return _texte(e.message, e.code)
    except Warehouse.DoesNotExist:
        return _texte('Entrepôt introuvable.', 404)
    except Exception as e:
        return _texte(f'Erreur: {e}', 500)

    # ?inline=1 : ouvrir le PDF dans le navigateur (impression) au lieu de le telecharger
    inline = export_format == 'pdf' and request.GET.get('inline') == '1'
    response, filename = _reponse_fichier(buffer, export_format, 'valorisation_stock', inline)
    log_event(
        request=request,
        action='report.export_stock_valuation',
        target=None,
        metadata={'format': export_format, 'warehouse_id': warehouse_id, 'par_depot': par_depot,
                  'prix': prix, 'filename': filename}
    )
    return response


@login_required
def export_sales_report(request):
    """Export du rapport des ventes"""
    export_format = request.GET.get('format', 'excel').lower()
    start_date_str = request.GET.get('start_date', None)
    end_date_str = request.GET.get('end_date', None)

    start_date = None
    end_date = None

    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        if export_format == 'pdf':
            buffer = generate_sales_report_pdf(start_date, end_date, perimetre_rapport(request))
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'rapport_ventes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        else:
            buffer = generate_sales_report_excel(start_date, end_date, perimetre_rapport(request))
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'rapport_ventes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Enregistrer l'audit log
        log_event(
            request=request,
            action='report.export_sales',
            target=None,
            metadata={
                'format': export_format,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'filename': filename
            }
        )

        return response
    except Exception as e:
        return HttpResponse(f'Erreur: {str(e)}', status=500)


@login_required
def export_inventory_report(request):
    """Export de l'état du stock / inventaire complet (tous les produits actifs, même à 0).
    GET : format=excel|pdf, warehouse=<id> (dépôt affiché dans Gestion des stocks), inline=1."""
    export_format = request.GET.get('format', 'excel').lower()
    warehouse_id = (request.GET.get('warehouse') or '').strip() or None
    try:
        if warehouse_id is not None and not warehouse_id.isdigit():
            raise Warehouse.DoesNotExist(warehouse_id)
        company = perimetre_rapport(request)
        societe = nom_societe_rapport(request)
        generer = generate_inventory_report_pdf if export_format == 'pdf' else generate_inventory_report_excel
        buffer = generer(company, warehouse_id=warehouse_id, societe=societe)
    except Warehouse.DoesNotExist:
        return _texte('Entrepôt introuvable.', 404)
    except Exception as e:
        return _texte(f'Erreur: {e}', 500)

    inline = export_format == 'pdf' and request.GET.get('inline') == '1'
    response, filename = _reponse_fichier(buffer, export_format, 'etat_stock', inline)
    log_event(
        request=request,
        action='report.export_inventory',
        target=None,
        metadata={'format': export_format, 'warehouse_id': warehouse_id, 'filename': filename}
    )
    return response


@login_required
def export_profit_report(request):
    """Export du rapport des bénéfices (prix vente - prix achat).
    Réservé à l'administrateur de l'entreprise, après saisie du code PIN."""
    from API.benefices_acces import AccesRefuse, verifier_acces
    try:
        company = verifier_acces(request)
    except AccesRefuse as e:
        return HttpResponse(e.message, status=e.code, content_type='text/plain; charset=utf-8')
    export_format = request.GET.get('format', 'excel').lower()

    try:
        if export_format == 'pdf':
            buffer = generate_profit_report_pdf(company)
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'rapport_benefices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        else:
            buffer = generate_profit_report_excel(company)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'rapport_benefices_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        log_event(
            request=request,
            action='report.export_profit',
            target=None,
            metadata={'format': export_format, 'filename': filename}
        )

        return response
    except Exception as e:
        return HttpResponse(f'Erreur: {str(e)}', status=500)
