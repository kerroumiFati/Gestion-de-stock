"""
Vues pour gérer les Companies (Sessions) manuellement
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from API.models import Company, UserProfile

User = get_user_model()

def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def create_company_view(request):
    """Vue pour créer une nouvelle company/session"""

    if request.method == 'POST':
        # Récupérer les données du formulaire
        company_name = request.POST.get('company_name')
        company_code = request.POST.get('company_code').upper()
        company_email = request.POST.get('company_email')
        company_phone = request.POST.get('company_phone')
        company_address = request.POST.get('company_address')

        username = request.POST.get('username')
        password = request.POST.get('password')
        user_email = request.POST.get('user_email')

        try:
            # Vérifier si le code existe déjà
            if Company.objects.filter(code=company_code).exists():
                messages.error(request, f"Le code '{company_code}' existe déjà. Choisissez un autre code.")
                return render(request, 'create_company.html')

            # Vérifier si le username existe déjà
            if User.objects.filter(username=username).exists():
                messages.error(request, f"Le nom d'utilisateur '{username}' existe déjà. Choisissez un autre.")
                return render(request, 'create_company.html')

            # Créer la Company
            company = Company.objects.create(
                name=company_name,
                code=company_code,
                email=company_email,
                telephone=company_phone,
                adresse=company_address,
                is_active=True
            )

            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                password=password,
                email=user_email,
                is_staff=True,
                is_active=True
            )

            # Créer le profil
            UserProfile.objects.create(
                user=user,
                company=company,
                role='admin'
            )

            messages.success(request, f"✓ Session créée avec succès : {company_name} ({company_code})")
            messages.info(request, f"Connexion : Username = {username} / Password = {password}")

            return redirect('list_companies')

        except Exception as e:
            messages.error(request, f"Erreur : {str(e)}")

    return render(request, 'create_company.html')


@login_required
@user_passes_test(is_superuser)
def list_companies_view(request):
    """Vue pour lister toutes les companies"""
    companies = Company.objects.all().order_by('name')

    companies_data = []
    for company in companies:
        companies_data.append({
            'company': company,
            'users_count': company.users.count(),
            'users': UserProfile.objects.filter(company=company).select_related('user')
        })

    context = {
        'companies_data': companies_data,
        'total_companies': companies.count()
    }

    return render(request, 'list_companies.html', context)


@login_required
@user_passes_test(is_superuser)
def delete_company_view(request, company_id):
    """Vue pour supprimer une company"""
    try:
        company = Company.objects.get(id=company_id)
        company_name = company.name
        company.delete()
        messages.success(request, f"✓ Session supprimée : {company_name}")
    except Company.DoesNotExist:
        messages.error(request, "Session introuvable")
    except Exception as e:
        messages.error(request, f"Erreur : {str(e)}")

    return redirect('list_companies')
