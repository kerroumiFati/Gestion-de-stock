from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from API.models import AuditLog


def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)

@staff_required
def audit_list(request):
    logs = AuditLog.objects.select_related('actor').all()[:500]
    return render(request, 'frontoffice/audit_list.html', {'logs': logs})
