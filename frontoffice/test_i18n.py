"""
Test view to check if translations are working
"""
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.utils.translation import get_language, activate
from django.http import HttpResponse


def test_translation(request):
    """Test translation functionality"""

    # Get current language
    current_lang = get_language()

    # Test translations
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test Traduction</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .test-result {{ background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .success {{ background: #d4edda; color: #155724; }}
            .error {{ background: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <h1>Test de Traduction Django i18n</h1>

        <div class="test-result">
            <strong>Langue actuelle détectée:</strong> {current_lang}
        </div>

        <div class="test-result">
            <strong>Test de traduction "Commercial":</strong><br>
            FR: Commercial<br>
            Traduit: {_('Commercial')}<br>
            Status: {'<span class="success">✓ OK</span>' if _('Commercial') != 'Commercial' or current_lang == 'fr' else '<span class="error">✗ Pas traduit</span>'}
        </div>

        <div class="test-result">
            <strong>Test de traduction "Produits":</strong><br>
            FR: Produits<br>
            Traduit: {_('Produits')}<br>
            Status: {'<span class="success">✓ OK</span>' if _('Produits') != 'Produits' or current_lang == 'fr' else '<span class="error">✗ Pas traduit</span>'}
        </div>

        <div class="test-result">
            <strong>Test de traduction "Déconnexion":</strong><br>
            FR: Déconnexion<br>
            Traduit: {_('Déconnexion')}<br>
            Status: {'<span class="success">✓ OK</span>' if _('Déconnexion') != 'Déconnexion' or current_lang == 'fr' else '<span class="error">✗ Pas traduit</span>'}
        </div>

        <h2>Test manuel des langues</h2>
        <p><a href="?lang=fr">Français</a> | <a href="?lang=en">English</a> | <a href="?lang=ar">العربية</a></p>

        <h2>SystemConfig</h2>
        <div class="test-result">
    """

    try:
        from API.models import SystemConfig
        config = SystemConfig.get_solo()
        html += f"""
            <strong>Langue configurée:</strong> {config.language if config else 'None'}<br>
            <strong>Config existe:</strong> {'Oui' if config else 'Non'}
        """
    except Exception as e:
        html += f"""
            <span class="error">Erreur: {e}</span>
        """

    html += """
        </div>

        <h2>Import des fichiers .mo</h2>
        <div class="test-result">
    """

    # Test if .mo files are found
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ar_mo = os.path.join(base_dir, 'locale', 'ar', 'LC_MESSAGES', 'django.mo')
    en_mo = os.path.join(base_dir, 'locale', 'en', 'LC_MESSAGES', 'django.mo')

    html += f"""
            <strong>Fichier AR .mo:</strong> {'✓ Existe' if os.path.exists(ar_mo) else '✗ Manquant'} ({ar_mo})<br>
            <strong>Fichier EN .mo:</strong> {'✓ Existe' if os.path.exists(en_mo) else '✗ Manquant'} ({en_mo})
        </div>
    </body>
    </html>
    """

    # Handle manual language change
    lang = request.GET.get('lang')
    if lang in ['fr', 'en', 'ar']:
        activate(lang)
        request.session['django_language'] = lang
        return HttpResponse(html)

    return HttpResponse(html)
