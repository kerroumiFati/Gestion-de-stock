from django.shortcuts import render, redirect
from django.templatetags.static import static


# Aperçu de l'application sur la page de téléchargement : vraies captures du guide (static/guide/captures/).
APP_SCREENS = [
    ('guide/captures/W_mobile_accueil.png', 'Accueil',
     "Les ventes et le chiffre d'affaires du jour, puis un accès direct aux tournées, clients, stock du van, crédits et commandes à livrer.",
     "Écran Accueil : ventes du jour et actions rapides"),
    ('guide/captures/W_mobile_clients.png', 'Clients à visiter',
     "Les clients de la tournée du jour, avec l'itinéraire et les boutons Vente et Cmd.",
     "Écran Clients à visiter de la tournée"),
    ('guide/captures/B0_tournee_commandes.png', 'Détails de la tournée',
     "Pour chaque client, les ventes et les commandes de la journée avec leurs montants.",
     "Détails de la tournée : ventes et commandes d'un client"),
    ('guide/captures/M2_vente_choix_produit.png', 'Nouvelle vente',
     "Choisissez le mode de paiement, puis les produits dans le stock de votre van.",
     "Nouvelle vente : mode de paiement et produits du van"),
    ('guide/captures/M4_commande_choix_produit.png', 'Nouvelle commande',
     "Prenez une commande à livrer plus tard, avec le stock disponible au dépôt.",
     "Nouvelle commande : produits avec le stock du dépôt"),
    ('guide/captures/M6_livreur_commandes_a_livrer.png', 'Commandes à livrer',
     "Les commandes préparées pour vous : paiement, bon imprimable, appel, itinéraire et livraison.",
     "Commandes à livrer avec les boutons d'action"),
]


def app_download_page(request):
    apk_url = request.build_absolute_uri(static('app/app.apk'))
    screens = [{'src': static(path), 'title': title, 'text': text, 'alt': alt}
               for path, title, text, alt in APP_SCREENS]
    context = {'apk_url': apk_url, 'screens': screens}
    return render(request, 'frontoffice/app_download.html', context)


def app_download_redirect(request):
    return redirect(static('app/app.apk'))


def guide_nouveautes(request):
    """Guide des nouveautés : site statique dans static/guide/ (captures dans static/guide/captures/)."""
    return redirect(static('guide/index.html'))
