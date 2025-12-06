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
    generate_inventory_report_pdf
)
from API.audit import log_event


@login_required
def export_stock_valuation(request):
    """Export du rapport de valorisation du stock"""
    export_format = request.GET.get('format', 'excel').lower()
    warehouse_id = request.GET.get('warehouse', None)

    try:
        if export_format == 'pdf':
            buffer = generate_stock_valuation_pdf(warehouse_id)
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'valorisation_stock_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        else:
            buffer = generate_stock_valuation_excel(warehouse_id)
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'valorisation_stock_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Enregistrer l'audit log
        log_event(
            request=request,
            action='report.export_stock_valuation',
            target=None,
            metadata={'format': export_format, 'warehouse_id': warehouse_id, 'filename': filename}
        )

        return response
    except Exception as e:
        return HttpResponse(f'Erreur: {str(e)}', status=500)


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
            buffer = generate_sales_report_pdf(start_date, end_date)
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'rapport_ventes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        else:
            buffer = generate_sales_report_excel(start_date, end_date)
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
    """Export du rapport d'inventaire complet"""
    export_format = request.GET.get('format', 'excel').lower()

    try:
        if export_format == 'pdf':
            buffer = generate_inventory_report_pdf()
            response = HttpResponse(buffer, content_type='application/pdf')
            filename = f'inventaire_complet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        else:
            buffer = generate_inventory_report_excel()
            response = HttpResponse(
                buffer,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            filename = f'inventaire_complet_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'

        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # Enregistrer l'audit log
        log_event(
            request=request,
            action='report.export_inventory',
            target=None,
            metadata={'format': export_format, 'filename': filename}
        )

        return response
    except Exception as e:
        return HttpResponse(f'Erreur: {str(e)}', status=500)
