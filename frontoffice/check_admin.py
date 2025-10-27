"""
Temporary endpoint to check existing admin users
"""
from django.contrib.auth.models import User
from django.http import JsonResponse

def check_existing_admins(request):
    """
    List existing superusers (only usernames, no passwords)
    """
    superusers = User.objects.filter(is_superuser=True)

    if not superusers.exists():
        return JsonResponse({
            'message': 'No admin users found',
            'count': 0
        })

    admin_list = []
    for user in superusers:
        admin_list.append({
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat()
        })

    return JsonResponse({
        'message': f'{len(admin_list)} admin user(s) found',
        'count': len(admin_list),
        'admins': admin_list
    })
