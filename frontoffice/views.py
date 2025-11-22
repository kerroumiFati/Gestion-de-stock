from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect
from django.views.generic import TemplateView
from django.conf import settings
from django.contrib import messages
from .forms import *
from .forms_users import UserAdminForm, GroupAdminForm
from API.models import Produit
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import user_passes_test
from API.audit import log_event
import json

def login_view(request):
    return render(request, "login.html",)


from django.contrib.auth.decorators import login_required

@login_required
def dashboard(request):
    # Render the original master page layout
    return render(request, 'frontoffice/master_page.html')


@login_required
def page(request, name: str):
    # Serve partial pages used by the sidebar navigation
    # Protect the admin page for staff only
    if name == 'admin' and not (request.user.is_authenticated and request.user.is_staff):
        return HttpResponse('Accès refusé', status=403)

    # Handle stock management pages with data
    if name == 'entrepots_list':
        return entrepots_list(request)
    elif name == 'stocks_list':
        return stocks_list(request)
    elif name == 'transferts_list':
        return transferts_list(request)
    elif name == 'charger_van':
        return charger_van(request)
    elif name == 'stock_dashboard':
        return stock_dashboard(request)
    elif name == 'stock_management':
        return render(request, 'frontoffice/page/stock_management.html')
    elif name == 'livreur_mobile':
        # Vérifier que l'utilisateur est dans le groupe "livreurs" ou est admin
        if not (request.user.is_staff or request.user.groups.filter(name='livreurs').exists()):
            return HttpResponse('Accès refusé. Seuls les livreurs et administrateurs peuvent accéder à cette application.', status=403)
        return render(request, 'frontoffice/page/livreur_mobile.html')
    elif name == 'config_clients_chauffeurs':
        return render(request, 'frontoffice/page/config_clients_chauffeurs.html')
    elif name == 'livreurs':
        return render(request, 'frontoffice/page/livreurs.html')
    elif name == 'tournees':
        return render(request, 'frontoffice/page/tournees.html')
    elif name == 'distribution_dashboard':
        return render(request, 'frontoffice/page/distribution_dashboard.html')
    elif name == 'commandes_clients_mobile':
        return commandes_clients_mobile(request)
    elif name == 'distribution_test':
        return render(request, 'frontoffice/page/distribution_test.html')
    elif name == 'nav_test':
        return render(request, 'frontoffice/page/nav_test.html')

    # Protect currency management under paramètres: page accessible but section is guarded in template
    template_path = f'frontoffice/page/{name}.html'
    try:
        return render(request, template_path)
    except Exception:
        # Basic 404 content for missing pages
        return HttpResponse(f'Page {name} introuvable', status=404)


class LoginView(TemplateView):

  template_name = 'login.html'

  def post(self, request, **kwargs):

    username = request.POST.get('username', False)
    password = request.POST.get('password', False)
    user = authenticate(username=username, password=password)
    if user is not None and user.is_active:
        login(request, user)
        return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL )
    messages.success(request, 'mot de passe ou nom d''utilisateur incorrect')
    return render(request, self.template_name)


class LogoutView(TemplateView):

  template_name = 'login.html'

  def get(self, request, **kwargs):
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return render(request, self.template_name)


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)

@staff_required
def users_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'frontoffice/users_list.html', {'users': users})

@staff_required
def user_create(request):
    if request.method == 'POST':
        form = UserAdminForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            pwd = form.cleaned_data.get('password')
            if pwd:
                user.set_password(pwd)
            else:
                user.set_unusable_password()
            user.save()
            form.save_m2m()
            messages.success(request, 'Utilisateur créé avec succès')
            log_event(request, 'user.create', target=user, metadata={'username': user.username})
            return redirect('users_list')
    else:
        form = UserAdminForm()
    return render(request, 'frontoffice/user_form.html', {'form': form, 'title': 'Nouvel utilisateur'})

@staff_required
def user_edit(request, user_id):
    user = User.objects.get(pk=user_id)
    if request.method == 'POST':
        form = UserAdminForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            pwd = form.cleaned_data.get('password')
            if pwd:
                user.set_password(pwd)
            user.save()
            form.save_m2m()
            messages.success(request, 'Utilisateur mis à jour')
            log_event(request, 'user.update', target=user, metadata={'username': user.username})
            return redirect('users_list')
    else:
        form = UserAdminForm(instance=user)
    return render(request, 'frontoffice/user_form.html', {'form': form, 'title': 'Modifier utilisateur'})

@staff_required
def user_delete(request, user_id):
    user = User.objects.get(pk=user_id)
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, 'Utilisateur supprimé')
        log_event(request, 'user.delete', target=None, metadata={'username': username})
        return redirect('users_list')
    return render(request, 'frontoffice/user_delete_confirm.html', {'user': user})

@staff_required
def user_reset_password_confirm(request, user_id):
    user = User.objects.get(pk=user_id)
    if request.method == 'POST':
        import secrets, string
        provided_pwd = (request.POST.get('password') or '').strip()
        if provided_pwd:
            pwd = provided_pwd
        else:
            alphabet = string.ascii_letters + string.digits + '!@#$%^&*()-_=+'
            pwd = ''.join(secrets.choice(alphabet) for _ in range(12))
        # Optionally add minimal validation
        if len(pwd) < 8:
            messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères.')
            return render(request, 'frontoffice/user_reset_confirm.html', {'user': user, 'prefilled': provided_pwd})
        user.set_password(pwd)
        user.save()
        log_event(request, 'user.password_reset', target=user, metadata={'username': user.username, 'mode': 'provided' if provided_pwd else 'generated'})
        return render(request, 'frontoffice/user_reset_result.html', {'user': user, 'new_password': pwd})
    return render(request, 'frontoffice/user_reset_confirm.html', {'user': user})

@staff_required
def roles_list(request):
    roles = Group.objects.all().order_by('name')
    return render(request, 'frontoffice/roles_list.html', {'roles': roles})

@staff_required
def role_create(request):
    """Créer un nouveau groupe/rôle"""
    if request.method == 'POST':
        form = GroupAdminForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Groupe "{group.name}" créé avec succès')
            log_event(request, 'group.create', target=None, metadata={'group_name': group.name})
            return redirect('roles_list')
    else:
        form = GroupAdminForm()
    return render(request, 'frontoffice/group_form.html', {'form': form, 'title': 'Nouveau Groupe'})

@staff_required
def role_edit(request, role_id):
    """Modifier un groupe/rôle"""
    group = Group.objects.get(pk=role_id)
    if request.method == 'POST':
        form = GroupAdminForm(request.POST, instance=group)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'Groupe "{group.name}" modifié avec succès')
            log_event(request, 'group.update', target=None, metadata={'group_name': group.name})
            return redirect('roles_list')
    else:
        form = GroupAdminForm(instance=group)
    return render(request, 'frontoffice/group_form.html', {'form': form, 'title': 'Modifier Groupe'})

@staff_required
def role_delete(request, role_id):
    """Supprimer un groupe/rôle"""
    group = Group.objects.get(pk=role_id)
    group_name = group.name
    group.delete()
    messages.success(request, f'Groupe "{group_name}" supprimé avec succès')
    log_event(request, 'group.delete', target=None, metadata={'group_name': group_name})
    return redirect('roles_list')

@staff_required
def role_edit_permissions(request, role_id):
    """Interface pour modifier les permissions d'un rôle"""
    from django.contrib.auth.models import Group, Permission
    role = Group.objects.get(pk=role_id)
    all_permissions = Permission.objects.all().order_by('content_type__model', 'codename')

    if request.method == 'POST':
        # Récupérer les permissions cochées
        selected_perms = request.POST.getlist('permissions')
        role.permissions.set(selected_perms)
        from API.views import log_event
        log_event(request, 'role.update_permissions', target=None, metadata={'role': role.name, 'permissions_count': len(selected_perms)})
        return redirect('/roles-admin/')

    return render(request, 'frontoffice/role_permissions.html', {
        'role': role,
        'all_permissions': all_permissions
    })

@staff_required
def admin_users(request):
    """Nouvelle interface moderne pour la gestion des utilisateurs, rôles et permissions"""
    return render(request, 'frontoffice/admin_users.html')

# def post_new(request):
 #   if request.method == "POST":
  #      form = ProduitForm(request.POST)
   #     if form.is_valid():
    #        produit = form.save()
     #       produit.save()
      #      return redirect('produits')
    #else :
     #   form = ProduitForm()
    #return render(request, 'frontoffice/produit_form.html', {'form': form})


def produit_all(request):
    names_from_db = Produit.objects.all()
    context_dict = {'produits_from_context': names_from_db}
    return render(request, 'frontoffice/produit_all.html', context_dict)


@login_required
def caisse(request):
    """Vue pour la page de caisse (point de vente)"""
    return render(request, 'frontoffice/caisse_page.html')


# --- Distribution module simple page views ---
@login_required
def livreurs_page(request):
    # Render the master page - JavaScript will load the livreurs content based on URL
    return render(request, 'frontoffice/master_page.html')

@login_required
def tournees_page(request):
    # Render the master page - JavaScript will load the tournees content based on URL
    return render(request, 'frontoffice/master_page.html')

@login_required
def distribution_page(request):
    # Render the master page - JavaScript will load the distribution dashboard content based on URL
    return render(request, 'frontoffice/master_page.html')

@login_required
def livreur_app_page(request):
    # Vérifier que l'utilisateur est dans le groupe "livreurs"
    if not request.user.groups.filter(name='livreurs').exists():
        messages.error(request, 'Accès refusé. Seuls les livreurs peuvent accéder à cette application.')
        return redirect('login')

    # Render the master page - JavaScript will load the livreur mobile app content based on URL
    return render(request, 'frontoffice/master_page.html')

@login_required
def config_clients_chauffeurs_page(request):
    # Render the master page - JavaScript will load the config clients chauffeurs content based on URL
    return render(request, 'frontoffice/master_page.html')


def counts_all(request):
    produits = Produit.objects.all().count()
    return render(request, 'frontoffice/master_page.html', {'produits': produits})

@login_required
def change_password(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    current = (request.POST.get('current_password') or '').strip()
    newpwd = (request.POST.get('new_password') or '').strip()
    if not request.user.check_password(current):
        return HttpResponse(json.dumps({'error': 'Mot de passe actuel incorrect'}), status=400, content_type='application/json')
    if len(newpwd) < 8:
        return HttpResponse(json.dumps({'error': 'Le nouveau mot de passe doit contenir au moins 8 caractères'}), status=400, content_type='application/json')
    request.user.set_password(newpwd)
    request.user.save()
    # Rester connecté après changement
    user = authenticate(username=request.user.username, password=newpwd)
    if user is not None:
        login(request, user)
    return HttpResponse(json.dumps({'status': 'ok'}), content_type='application/json')


# ===========================
# Gestion de Stock - Vues personnalisées
# ===========================

from API.models import Warehouse, ProductStock, TransfertStock, LigneTransfertStock, StockMove, Produit, Currency
from API.distribution_models import LivreurDistribution
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator

def get_default_currency():
    """Récupérer la devise par défaut du système"""
    currency = Currency.objects.filter(is_default=True, is_active=True).first()
    if not currency:
        # Fallback sur la première devise active
        currency = Currency.objects.filter(is_active=True).first()
    return currency

@login_required
def entrepots_list(request):
    """Liste des entrepôts et vans"""
    entrepots = Warehouse.objects.all().order_by('code')

    # Ajouter les statistiques pour chaque entrepôt
    for entrepot in entrepots:
        # Ne compter que les produits avec stock > 0
        entrepot.nb_produits = entrepot.stocks.filter(quantity__gt=0).count()
        entrepot.total_quantite = entrepot.stocks.aggregate(Sum('quantity'))['quantity__sum'] or 0
        entrepot.valeur_stock = sum(
            stock.quantity * stock.produit.prixU
            for stock in entrepot.stocks.select_related('produit')
            if stock.produit.prixU
        )
        # Vérifier si c'est un van
        entrepot.est_van = entrepot.code.upper().startswith('VAN')
        if entrepot.est_van:
            entrepot.livreur = LivreurDistribution.objects.filter(entrepot=entrepot).first()

    context = {
        'entrepots': entrepots,
        'title': 'Entrepôts & Vans',
        'currency': get_default_currency()
    }
    return render(request, 'frontoffice/page/entrepots_list.html', context)


@login_required
def stocks_list(request):
    """Liste des stocks par entrepôt"""
    entrepot_id = request.GET.get('entrepot')

    stocks = ProductStock.objects.select_related('produit', 'warehouse').all()

    if entrepot_id:
        stocks = stocks.filter(warehouse_id=entrepot_id)

    # Filtrer les stocks vides si demandé
    hide_empty = request.GET.get('hide_empty')
    if hide_empty:
        stocks = stocks.filter(quantity__gt=0)

    stocks = stocks.order_by('warehouse__code', 'produit__reference')

    # Pagination
    paginator = Paginator(stocks, 50)
    page = request.GET.get('page', 1)
    stocks_page = paginator.get_page(page)

    # Ajouter la valeur calculée pour chaque stock de la page
    for stock in stocks_page:
        stock.valeur = stock.quantity * stock.produit.prixU if stock.produit.prixU else 0

    entrepots = Warehouse.objects.all().order_by('code')

    context = {
        'stocks': stocks_page,
        'entrepots': entrepots,
        'selected_entrepot': entrepot_id,
        'hide_empty': hide_empty,
        'title': 'Stocks par Entrepôt',
        'currency': get_default_currency()
    }
    return render(request, 'frontoffice/page/stocks_list.html', context)


@login_required
def transferts_list(request):
    """Liste des transferts de stock"""
    transferts = TransfertStock.objects.select_related(
        'entrepot_source',
        'entrepot_destination',
        'demandeur',
        'valideur'
    ).prefetch_related('lignes__produit').all()

    # Filtres
    statut = request.GET.get('statut')
    if statut:
        transferts = transferts.filter(statut=statut)

    source_id = request.GET.get('source')
    if source_id:
        transferts = transferts.filter(entrepot_source_id=source_id)

    dest_id = request.GET.get('destination')
    if dest_id:
        transferts = transferts.filter(entrepot_destination_id=dest_id)

    transferts = transferts.order_by('-date_creation')

    # Pagination
    paginator = Paginator(transferts, 20)
    page = request.GET.get('page', 1)
    transferts_page = paginator.get_page(page)

    entrepots = Warehouse.objects.all().order_by('code')

    context = {
        'transferts': transferts_page,
        'entrepots': entrepots,
        'statut_filter': statut,
        'source_filter': source_id,
        'dest_filter': dest_id,
        'title': 'Liste des Transferts'
    }
    return render(request, 'frontoffice/page/transferts_list.html', context)


@login_required
def charger_van(request):
    """Formulaire pour charger un van rapidement"""
    from django.http import JsonResponse

    # Récupérer la company de l'utilisateur
    company = getattr(request, 'company', None)

    if request.method == 'POST':
        van_id = request.POST.get('van')
        source_id = request.POST.get('entrepot_source')
        produits_text = request.POST.get('produits')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            van = Warehouse.objects.get(id=van_id)
            source = Warehouse.objects.get(id=source_id)

            # Créer le transfert avec la company du middleware
            transfert = TransfertStock.objects.create(
                company=company,
                entrepot_source=source,
                entrepot_destination=van,
                demandeur=request.user,
                notes='Chargement van créé via interface rapide'
            )

            # Parser les produits
            errors = []
            lignes_count = 0
            for line in produits_text.strip().split('\n'):
                if not line.strip():
                    continue

                try:
                    ref, qty = line.split(',')
                    produit = Produit.objects.get(reference=ref.strip())
                    LigneTransfertStock.objects.create(
                        transfert=transfert,
                        produit=produit,
                        quantite=int(qty.strip())
                    )
                    lignes_count += 1
                except Exception as e:
                    errors.append(f"Ligne '{line}': {str(e)}")

            if not errors:
                # Valider automatiquement
                try:
                    transfert.valider(request.user)
                    if is_ajax:
                        return JsonResponse({
                            'success': True,
                            'message': f'Transfert {transfert.numero} créé et validé avec succès!',
                            'transfert_numero': transfert.numero,
                            'lignes_count': lignes_count
                        })
                    messages.success(request, f'Transfert {transfert.numero} créé et validé avec succès!')
                    return redirect('transferts_list')
                except Exception as e:
                    if is_ajax:
                        return JsonResponse({
                            'success': False,
                            'message': f'Transfert créé mais erreur de validation: {str(e)}'
                        }, status=400)
                    messages.error(request, f'Transfert créé mais erreur de validation: {str(e)}')
                    return redirect('transferts_list')
            else:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': 'Transfert créé avec des erreurs: ' + '; '.join(errors)
                    }, status=400)
                messages.warning(request, 'Transfert créé avec des erreurs: ' + '; '.join(errors))
                return redirect('transferts_list')

        except Exception as e:
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                }, status=400)
            messages.error(request, f'Erreur: {str(e)}')

    # GET - afficher le formulaire
    # Filtrer par company si disponible
    vans_qs = Warehouse.objects.filter(code__icontains='van', is_active=True)
    sources_qs = Warehouse.objects.exclude(code__icontains='van').filter(is_active=True)

    if company:
        vans_qs = vans_qs.filter(company=company)
        sources_qs = sources_qs.filter(company=company)

    vans = vans_qs.order_by('code')
    sources = sources_qs.order_by('code')

    context = {
        'vans': vans,
        'sources': sources,
        'title': 'Charger un Van',
        'currency': get_default_currency()
    }
    return render(request, 'frontoffice/page/charger_van.html', context)


@login_required
def stock_dashboard(request):
    """Tableau de bord des stocks par van"""
    # Récupérer tous les vans
    vans = Warehouse.objects.filter(
        code__istartswith='van',
        is_active=True
    ).prefetch_related('stocks__produit').order_by('code')

    # Statistiques par van
    van_stats = []
    for van in vans:
        stocks = van.stocks.select_related('produit').all()
        total_produits = stocks.count()
        total_quantite = sum(s.quantity for s in stocks)
        valeur_stock = sum(s.quantity * s.produit.prixU for s in stocks)

        # Trouver le livreur associé
        livreur = LivreurDistribution.objects.filter(entrepot=van).first()

        # Stock faible
        stocks_alertes = [s for s in stocks if s.quantity > 0 and s.quantity <= s.produit.seuil_alerte]

        van_stats.append({
            'van': van,
            'livreur': livreur,
            'total_produits': total_produits,
            'total_quantite': total_quantite,
            'valeur_stock': valeur_stock,
            'stocks': stocks[:10],  # Top 10
            'nb_alertes': len(stocks_alertes)
        })

    context = {
        'van_stats': van_stats,
        'title': 'Tableau de Bord des Vans',
        'currency': get_default_currency()
    }
    return render(request, 'frontoffice/page/stock_dashboard.html', context)


@login_required
def commandes_clients_mobile(request):
    """Interface de gestion des commandes clients depuis l'application mobile"""
    from API.distribution_models import LivreurDistribution
    
    context = {
        'title': 'Commandes Clients Mobile',
        'currency': get_default_currency()
    }
    return render(request, 'frontoffice/page/commandes_clients_mobile.html', context)
