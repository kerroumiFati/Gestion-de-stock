from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import pandas as pd
import io
import csv
from decimal import Decimal
from .models import Produit, Categorie, Fournisseur, Client, Secteur, Currency
from django.db import transaction


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication sans vérification CSRF"""
    def enforce_csrf(self, request):
        return  # Ne pas vérifier le CSRF


@method_decorator(csrf_exempt, name='dispatch')
class ImportPreviewView(APIView):
    """
    Prévisualisation d'un fichier d'import avant traitement
    """
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            file = request.FILES.get('file')
            import_type = request.POST.get('type', 'products')

            if not file:
                return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

            # Lire le fichier selon le type
            if file.name.endswith('.csv'):
                # Lire le contenu brut
                content = file.read()
                # Essayer différents encodages
                for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                    try:
                        text = content.decode(encoding)
                        df = pd.read_csv(io.StringIO(text), sep=None, engine='python')
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError):
                        continue
                else:
                    return Response({'error': 'Impossible de décoder le fichier CSV'}, status=status.HTTP_400_BAD_REQUEST)
            elif file.name.endswith(('.xlsx', '.xls')):
                # Pour Excel, lire directement depuis le fichier uploadé
                file.seek(0)
                df = pd.read_excel(file, engine='openpyxl')
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


@method_decorator(csrf_exempt, name='dispatch')
class ImportExecuteView(APIView):
    """
    Exécution de l'import de données
    """
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            file = request.FILES.get('file')
            import_type = request.POST.get('type', 'products')

            if not file:
                return Response({'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

            # Lire le fichier
            if file.name.endswith('.csv'):
                # Lire le contenu brut
                content = file.read()
                # Essayer différents encodages
                for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                    try:
                        text = content.decode(encoding)
                        df = pd.read_csv(io.StringIO(text), sep=None, engine='python')
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError):
                        continue
                else:
                    return Response({'error': 'Impossible de décoder le fichier CSV'}, status=status.HTTP_400_BAD_REQUEST)
            elif file.name.endswith(('.xlsx', '.xls')):
                # Pour Excel, lire directement depuis le fichier uploadé
                file.seek(0)
                df = pd.read_excel(file, engine='openpyxl')
            else:
                return Response({'error': 'Format de fichier non supporté'}, status=status.HTTP_400_BAD_REQUEST)

            # Remplacer les NaN par des chaînes vides
            df = df.fillna('')

            # Récupérer la company de l'utilisateur
            company = None
            if hasattr(request, 'company') and request.company is not None:
                company = request.company

            # Traiter selon le type
            if import_type == 'products':
                result = self.import_products(df, request.user, company)
            elif import_type == 'categories':
                result = self.import_categories(df, request.user, company)
            elif import_type == 'fournisseurs':
                result = self.import_fournisseurs(df, request.user, company)
            elif import_type == 'clients':
                result = self.import_clients(df, request.user, company)
            elif import_type == 'pricelists':
                result = self.import_pricelists(df, request.user, company)
            else:
                return Response({'error': 'Type d\'import non supporté'}, status=status.HTTP_400_BAD_REQUEST)

            return Response(result)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def import_products(self, df, user, company=None):
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

                    # Assigner la company
                    if company:
                        data['company'] = company

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

    def import_categories(self, df, user, company=None):
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

                    # Assigner la company
                    if company:
                        data['company'] = company

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

    def import_fournisseurs(self, df, user, company=None):
        """Importer des fournisseurs"""
        created = 0
        updated = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    # Vérifier les champs requis
                    if not row.get('libelle') or not str(row.get('libelle')).strip():
                        errors.append({'row': idx + 2, 'message': 'Libellé manquant'})
                        skipped += 1
                        continue

                    # Préparer les données
                    data = {
                        'libelle': str(row['libelle']).strip(),
                    }

                    # Assigner la company
                    if company:
                        data['company'] = company

                    # Champs optionnels
                    if row.get('telephone'):
                        data['telephone'] = str(row['telephone']).strip()

                    if row.get('email'):
                        data['email'] = str(row['email']).strip()

                    if row.get('adresse'):
                        data['adresse'] = str(row['adresse']).strip()

                    if row.get('nif'):
                        data['nif'] = str(row['nif']).strip()

                    if row.get('nis'):
                        data['nis'] = str(row['nis']).strip()

                    if row.get('ai'):
                        data['ai'] = str(row['ai']).strip()

                    if row.get('rc'):
                        data['rc'] = str(row['rc']).strip()

                    # Créer ou mettre à jour le fournisseur
                    try:
                        fournisseur = Fournisseur.objects.get(libelle__iexact=data['libelle'])
                        # Mettre à jour
                        for key, value in data.items():
                            setattr(fournisseur, key, value)
                        fournisseur.save()
                        is_created = False
                    except Fournisseur.DoesNotExist:
                        # Créer
                        fournisseur = Fournisseur.objects.create(**data)
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

    def import_clients(self, df, user, company=None):
        """Importer des clients"""
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

                    # Assigner la company
                    if company:
                        data['company'] = company

                    # Champs optionnels
                    if row.get('prenom'):
                        data['prenom'] = str(row['prenom']).strip()

                    if row.get('telephone'):
                        data['telephone'] = str(row['telephone']).strip()

                    if row.get('email'):
                        data['email'] = str(row['email']).strip()

                    if row.get('adresse'):
                        data['adresse'] = str(row['adresse']).strip()

                    if row.get('lat'):
                        try:
                            data['lat'] = float(row['lat'])
                        except:
                            pass

                    if row.get('lng'):
                        try:
                            data['lng'] = float(row['lng'])
                        except:
                            pass

                    if row.get('nif'):
                        data['nif'] = str(row['nif']).strip()

                    if row.get('nis'):
                        data['nis'] = str(row['nis']).strip()

                    if row.get('ai'):
                        data['ai'] = str(row['ai']).strip()

                    if row.get('rc'):
                        data['rc'] = str(row['rc']).strip()

                    # Gérer le secteur
                    if row.get('secteur'):
                        secteur_name = str(row['secteur']).strip()
                        try:
                            secteur = Secteur.objects.get(nom__iexact=secteur_name)
                            data['secteur'] = secteur
                        except Secteur.DoesNotExist:
                            errors.append({'row': idx + 2, 'message': f'Secteur "{secteur_name}" introuvable'})

                    # Créer ou mettre à jour le client (basé sur nom + prénom pour unicité)
                    prenom = data.get('prenom', '')
                    try:
                        client = Client.objects.get(nom__iexact=data['nom'], prenom__iexact=prenom)
                        # Mettre à jour
                        for key, value in data.items():
                            setattr(client, key, value)
                        client.save()
                        is_created = False
                    except Client.DoesNotExist:
                        # Créer
                        client = Client.objects.create(**data)
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

    def import_pricelists(self, df, user, company=None):
        """Importer une liste de prix"""
        created = 0
        updated = 0
        skipped = 0
        errors = []

        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    # Vérifier les champs requis
                    code_article = str(row.get('code_article', '')).strip() if row.get('code_article') else ''
                    reference = str(row.get('reference', '')).strip() if row.get('reference') else ''

                    if not code_article and not reference:
                        errors.append({'row': idx + 2, 'message': 'Code article ou référence manquant'})
                        skipped += 1
                        continue

                    if not row.get('prix'):
                        errors.append({'row': idx + 2, 'message': 'Prix manquant'})
                        skipped += 1
                        continue

                    try:
                        prix = Decimal(str(row['prix']))
                        if prix <= 0:
                            raise ValueError('Le prix doit être positif')
                    except (ValueError, Exception) as e:
                        errors.append({'row': idx + 2, 'message': f'Prix invalide: {str(e)}'})
                        skipped += 1
                        continue

                    # Chercher le produit par code_barre ou référence
                    produit = None
                    if code_article:
                        try:
                            produit = Produit.objects.get(code_barre=code_article)
                        except Produit.DoesNotExist:
                            pass

                    if not produit and reference:
                        try:
                            produit = Produit.objects.get(reference=reference)
                        except Produit.DoesNotExist:
                            pass

                    if not produit:
                        errors.append({'row': idx + 2, 'message': f'Produit "{code_article or reference}" introuvable'})
                        skipped += 1
                        continue

                    # Mettre à jour le prix
                    produit.prixU = prix

                    # Mettre à jour les autres prix si fournis
                    if row.get('prix_achat'):
                        try:
                            produit.prix_achat = Decimal(str(row['prix_achat']))
                        except:
                            pass

                    if row.get('prix_gros'):
                        try:
                            produit.prix_gros = Decimal(str(row['prix_gros']))
                        except:
                            pass

                    if row.get('prix_detail'):
                        try:
                            produit.prix_detail = Decimal(str(row['prix_detail']))
                        except:
                            pass

                    if row.get('remise'):
                        try:
                            produit.remise = Decimal(str(row['remise']))
                        except:
                            pass

                    produit.save()
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

            elif import_type == 'fournisseurs':
                columns = ['libelle', 'telephone', 'email', 'adresse', 'nif', 'nis', 'ai', 'rc']
                filename = 'template_fournisseurs'

                # Données d'exemple
                example_data = [{
                    'libelle': 'Fournisseur Exemple',
                    'telephone': '0555123456',
                    'email': 'contact@fournisseur.com',
                    'adresse': '123 Rue Principale, Alger',
                    'nif': '123456789012345',
                    'nis': '123456789012345',
                    'ai': '12345678901',
                    'rc': '12/00-1234567B89'
                }]

            elif import_type == 'clients':
                columns = ['nom', 'prenom', 'telephone', 'email', 'adresse', 'lat', 'lng',
                          'secteur', 'nif', 'nis', 'ai', 'rc']
                filename = 'template_clients'

                # Données d'exemple
                example_data = [{
                    'nom': 'Superette Centrale',
                    'prenom': '',
                    'telephone': '0555987654',
                    'email': 'contact@superette.com',
                    'adresse': '45 Avenue des Palmiers, Oran',
                    'lat': '35.6976',
                    'lng': '-0.6337',
                    'secteur': 'Centre',
                    'nif': '123456789012345',
                    'nis': '123456789012345',
                    'ai': '12345678901',
                    'rc': '12/00-1234567B89'
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
