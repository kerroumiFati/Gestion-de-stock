import json
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from .models import AuditLog

def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def log_event(request, action, target=None, metadata=None):
    try:
        target_model = ''
        target_id = ''
        target_repr = ''
        if target is not None:
            ct = ContentType.objects.get_for_model(target.__class__)
            target_model = f"{ct.app_label}.{ct.model}"
            target_id = getattr(target, 'pk', '')
            target_repr = str(target)
        AuditLog.objects.create(
            actor=request.user if request and hasattr(request, 'user') else None,
            action=action,
            target_model=target_model,
            target_id=str(target_id),
            target_repr=target_repr,
            metadata=json.dumps(metadata or {}),
            ip_address=_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT','') if request else '',
            created_at=now(),
        )
    except Exception:
        # Ensure audit never breaks business flow
        pass
