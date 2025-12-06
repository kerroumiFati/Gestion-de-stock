"""
Script de test pour vérifier l'insertion des données ClientLivreurHebdo
"""
import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from API.distribution_models import ClientLivreurHebdo, LivreurDistribution
from API.models import Client

def test_client_livreur_hebdo():
    """Tester les données dans ClientLivreurHebdo"""
    print("\n" + "="*60)
    print("TEST: Vérification des données ClientLivreurHebdo")
    print("="*60 + "\n")

    # Compter le nombre total d'enregistrements
    total = ClientLivreurHebdo.objects.count()
    print(f"📊 Nombre total de configurations: {total}")

    # Compter par jour
    print("\n📅 Répartition par jour de la semaine:")
    jours_noms = {
        1: 'Lundi', 2: 'Mardi', 3: 'Mercredi',
        4: 'Jeudi', 5: 'Vendredi', 6: 'Samedi', 7: 'Dimanche'
    }
    for jour_num, jour_nom in jours_noms.items():
        count = ClientLivreurHebdo.objects.filter(jour_semaine=jour_num, is_active=True).count()
        print(f"   {jour_nom}: {count} configurations actives")

    # Compter par livreur
    print("\n👨‍💼 Configurations par livreur:")
    livreurs = LivreurDistribution.objects.all()
    for livreur in livreurs:
        count = ClientLivreurHebdo.objects.filter(livreur=livreur, is_active=True).count()
        if count > 0:
            clients_count = ClientLivreurHebdo.objects.filter(
                livreur=livreur, is_active=True
            ).values('client').distinct().count()
            print(f"   {livreur.nom}: {count} configs pour {clients_count} clients distincts")

    # Afficher les 10 dernières configurations créées
    print("\n🕐 Les 10 dernières configurations créées:")
    recent = ClientLivreurHebdo.objects.order_by('-created_at')[:10]
    for config in recent:
        jour_nom = jours_noms.get(config.jour_semaine, 'Inconnu')
        client_nom = f"{config.client.nom} {config.client.prenom}".strip() or config.client.email or f"Client #{config.client.id}"
        statut = "✅ Actif" if config.is_active else "❌ Inactif"
        ordre = f"Ordre: {config.ordre_passage}" if config.ordre_passage else "Sans ordre"
        print(f"   {statut} | {jour_nom} | {config.livreur.nom} → {client_nom} | {ordre}")
        print(f"      Créé le: {config.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Vérifier s'il y a des configurations inactives
    inactives = ClientLivreurHebdo.objects.filter(is_active=False).count()
    if inactives > 0:
        print(f"\n⚠️  Il y a {inactives} configurations inactives dans la base")

    # Vérifier les doublons potentiels
    print("\n🔍 Vérification des doublons (même client, même jour, plusieurs livreurs actifs):")
    clients = Client.objects.all()
    doublons_found = False
    for client in clients:
        for jour in range(1, 8):
            configs = ClientLivreurHebdo.objects.filter(
                client=client,
                jour_semaine=jour,
                is_active=True
            )
            if configs.count() > 1:
                doublons_found = True
                jour_nom = jours_noms.get(jour, 'Inconnu')
                client_nom = f"{client.nom} {client.prenom}".strip() or client.email or f"Client #{client.id}"
                print(f"   ⚠️  {client_nom} a {configs.count()} livreurs pour {jour_nom}:")
                for cfg in configs:
                    print(f"      - {cfg.livreur.nom}")

    if not doublons_found:
        print("   ✅ Aucun doublon détecté")

    print("\n" + "="*60)
    print("TEST TERMINÉ")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_client_livreur_hebdo()
