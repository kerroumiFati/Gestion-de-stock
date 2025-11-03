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
