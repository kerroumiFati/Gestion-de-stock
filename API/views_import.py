from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import pandas as pd
import io
import csv
from decimal import Decimal
from .models import Produit, Categorie, Fournisseur, Currency
from django.db import transaction


class ImportPreviewView(APIView):
    """
    Prévisualisation d'un fichier d'import avant traitement
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            file = request.FILES.get('file')
            import_type = request.POST.get('type', 'products')

            if not file:
                return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

            # Lire le fichier selon le type
            if file.name.endswith('.csv'):
                df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
            elif file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                return Response({'error': 'Format de fichier non supporté'}, status=status.HTTP_400_BAD_REQUEST)

            # Remplacer les NaN par des chaînes vides
            df = df.fillna('')

            # Convertir en format JSON
            headers = df.columns.tolist()
            rows = df.to_dict('records')

            return Response({
                'headers': headers,
                'rows': rows,
                'count': len(rows)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ImportExecuteView(APIView):
    """
    Exécution de l'import de données
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            file = request.FILES.get('file')
            import_type = request.POST.get('type', 'products')

            if not file:
                return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

            # Lire le fichier
            if file.name.endswith('.csv'):
                df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
            elif file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
            else:
                return Response({'error': 'Format de fichier non supporté'}, status=status.HTTP_400_BAD_REQUEST)

            # Remplacer les NaN par des chaînes vides
            df = df.fillna('')

            # Traiter selon le type
            if import_type == 'products':
                result = self.import_products(df, request.user)
            elif import_type == 'categories':
                result = self.import_categories(df, request.user)
            else:
                return Response({'error': 'Type d\'import non supporté'}, status=status.HTTP_400_BAD_REQUEST)

            return Response(result)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def import_products(self, df, user):
        """Importer des produits"""
        created = 0
        updated = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    # Vérifier les champs requis
                    if not row.get('reference') or not str(row.get('reference')).strip():
                        errors.append({'row': idx + 2, 'message': 'Référence manquante'})
                        skipped += 1
                        continue

                    if not row.get('designation') or not str(row.get('designation')).strip():
                        errors.append({'row': idx + 2, 'message': 'Désignation manquante'})
                        skipped += 1
                        continue

                    if not row.get('prixU'):
                        errors.append({'row': idx + 2, 'message': 'Prix manquant'})
                        skipped += 1
                        continue

                    try:
                        prix = Decimal(str(row['prixU']))
                        if prix <= 0:
                            raise ValueError('Le prix doit être positif')
                    except (ValueError, Exception) as e:
                        errors.append({'row': idx + 2, 'message': f'Prix invalide: {str(e)}'})
                        skipped += 1
                        continue

                    # Préparer les données
                    data = {
                        'reference': str(row['reference']).strip(),
                        'designation': str(row['designation']).strip(),
                        'prixU': prix,
                    }

                    # Champs optionnels
                    if row.get('code_barre'):
                        data['code_barre'] = str(row['code_barre']).strip()

                    if row.get('description'):
                        data['description'] = str(row['description']).strip()

                    if row.get('quantite'):
                        try:
                            data['quantite'] = int(float(row['quantite']))
                        except:
                            pass

                    if row.get('stock_min'):
                        try:
                            data['stock_min'] = int(float(row['stock_min']))
                        except:
                            pass

                    if row.get('stock_max'):
                        try:
                            data['stock_max'] = int(float(row['stock_max']))
                        except:
                            pass

                    if row.get('unite_mesure'):
                        data['unite_mesure'] = str(row['unite_mesure']).strip()

                    # Gérer la catégorie
                    if row.get('categorie'):
                        cat_name = str(row['categorie']).strip()
                        try:
                            categorie = Categorie.objects.get(nom__iexact=cat_name)
                            data['categorie'] = categorie
                        except Categorie.DoesNotExist:
                            errors.append({'row': idx + 2, 'message': f'Catégorie "{cat_name}" introuvable'})

                    # Gérer le fournisseur
                    if row.get('fournisseur'):
                        fournisseur_name = str(row['fournisseur']).strip()
                        try:
                            fournisseur = Fournisseur.objects.get(libelle__iexact=fournisseur_name)
                            data['fournisseur'] = fournisseur
                        except Fournisseur.DoesNotExist:
                            errors.append({'row': idx + 2, 'message': f'Fournisseur "{fournisseur_name}" introuvable'})

                    # Créer ou mettre à jour le produit
                    produit, is_created = Produit.objects.update_or_create(
                        reference=data['reference'],
                        defaults=data
                    )

                    if is_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append({'row': idx + 2, 'message': str(e)})
                    skipped += 1

        return {
            'stats': {
                'created': created,
                'updated': updated,
                'skipped': skipped,
                'total': len(df)
            },
            'errors': errors
        }

    def import_categories(self, df, user):
        """Importer des catégories"""
        created = 0
        updated = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    # Vérifier les champs requis
                    if not row.get('nom') or not str(row.get('nom')).strip():
                        errors.append({'row': idx + 2, 'message': 'Nom manquant'})
                        skipped += 1
                        continue

                    # Préparer les données
                    data = {
                        'nom': str(row['nom']).strip(),
                    }

                    # Champs optionnels
                    if row.get('description'):
                        data['description'] = str(row['description']).strip()

                    if row.get('couleur'):
                        data['couleur'] = str(row['couleur']).strip()

                    if row.get('icone'):
                        data['icone'] = str(row['icone']).strip()

                    # Gérer la catégorie parente
                    if row.get('parent'):
                        parent_name = str(row['parent']).strip()
                        try:
                            parent = Categorie.objects.get(nom__iexact=parent_name)
                            data['parent'] = parent
                        except Categorie.DoesNotExist:
                            errors.append({'row': idx + 2, 'message': f'Catégorie parente "{parent_name}" introuvable'})

                    # Créer ou mettre à jour la catégorie
                    # Chercher d'abord si existe (case insensitive)
                    try:
                        categorie = Categorie.objects.get(nom__iexact=data['nom'])
                        # Mettre à jour
                        for key, value in data.items():
                            setattr(categorie, key, value)
                        categorie.save()
                        is_created = False
                    except Categorie.DoesNotExist:
                        # Créer
                        categorie = Categorie.objects.create(**data)
                        is_created = True

                    if is_created:
                        created += 1
                    else:
                        updated += 1

                except Exception as e:
                    errors.append({'row': idx + 2, 'message': str(e)})
                    skipped += 1

        return {
            'stats': {
                'created': created,
                'updated': updated,
                'skipped': skipped,
                'total': len(df)
            },
            'errors': errors
        }


class ImportTemplateView(APIView):
    """
    Télécharger un template d'import
    """
    permission_classes = []  # Pas de permissions requises
    authentication_classes = []  # Pas d'authentification requise

    def get(self, request):
        try:
            import_type = request.GET.get('type', 'products')
            format_type = request.GET.get('format', 'excel')

            if import_type == 'products':
                columns = ['reference', 'code_barre', 'designation', 'description', 'prixU',
                          'categorie', 'fournisseur', 'quantite', 'stock_min', 'stock_max', 'unite_mesure']
                filename = 'template_produits'

                # Données d'exemple
                example_data = [{
                    'reference': 'PROD-001',
                    'code_barre': '1234567890123',
                    'designation': 'Exemple Produit 1',
                    'description': 'Description du produit',
                    'prixU': '99.99',
                    'categorie': 'Électronique',
                    'fournisseur': 'Fournisseur A',
                    'quantite': '100',
                    'stock_min': '10',
                    'stock_max': '500',
                    'unite_mesure': 'unité'
                }]

            elif import_type == 'categories':
                columns = ['nom', 'parent', 'description', 'couleur', 'icone']
                filename = 'template_categories'

                # Données d'exemple
                example_data = [{
                    'nom': 'Électronique',
                    'parent': '',
                    'description': 'Produits électroniques',
                    'couleur': '#3B82F6',
                    'icone': 'fas fa-laptop'
                }]

            else:
                return JsonResponse({'error': 'Type non supporté'}, status=400)

            # Créer le DataFrame
            df = pd.DataFrame(example_data, columns=columns)

            if format_type == 'excel':
                # Générer un fichier Excel
                output = io.BytesIO()

                # Essayer plusieurs moteurs Excel dans l'ordre de préférence
                excel_engines = ['openpyxl', 'xlsxwriter']
                engine_used = None

                for engine in excel_engines:
                    try:
                        with pd.ExcelWriter(output, engine=engine) as writer:
                            df.to_excel(writer, index=False, sheet_name='Données')
                        engine_used = engine
                        break
                    except ImportError:
                        continue
                    except Exception as e:
                        if engine == excel_engines[-1]:  # Last engine
                            raise e
                        continue

                if engine_used is None:
                    # Si aucun moteur n'est disponible, retourner un CSV à la place
                    return self._generate_csv_response(df, filename)

                output.seek(0)

                response = HttpResponse(
                    output.read(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'

            else:  # CSV
                response = self._generate_csv_response(df, filename)

            return response

        except Exception as e:
            # En cas d'erreur, retourner un message JSON
            return JsonResponse({
                'error': 'Erreur lors de la génération du template',
                'details': str(e)
            }, status=500)

    def _generate_csv_response(self, df, filename):
        """Génère une réponse HTTP avec un fichier CSV"""
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')  # utf-8-sig pour Excel Windows
        output.seek(0)

        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
