from django.shortcuts import redirect
from django.contrib.auth.decorators import user_passes_test


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)

@staff_required
def audit_list(request):
    # L'ancienne page brute est remplacée par l'interface intégrée au tableau de bord
    return redirect('/admindash/#audit')
