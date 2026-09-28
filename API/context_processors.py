from django.conf import settings


def upload_limits(request):
    """Expose aux templates les limites d'upload configurees dans settings.py, pour que
    les textes d'aide et la validation JS restent alignes avec la validation serveur."""
    return {
        'PRODUIT_IMAGE_MAX_SIZE_MB': settings.PRODUIT_IMAGE_MAX_SIZE_MB,
    }
