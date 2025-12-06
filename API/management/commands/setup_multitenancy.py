"""
Script de configuration du système multi-tenancy

Ce script permet de :
1. Créer une entreprise par défaut
2. Assigner tous les utilisateurs existants à cette entreprise
3. Assigner toutes les données existantes à cette entreprise
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from API.models import (
    Company, UserProfile, Produit, Client, Fournisseur, Categorie,
    Achat, BonLivraison, Facture, Warehouse, InventorySession, Vente
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Configure le système multi-tenancy avec une entreprise par défaut'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-name',
            type=str,
            default='Entreprise Par Défaut',
            help='Nom de l\'entreprise par défaut à créer'
        )
        parser.add_argument(
            '--company-code',
            type=str,
            default='DEFAULT',
            help='Code de l\'entreprise par défaut'
        )

    def handle(self, *args, **options):
        company_name = options['company_name']
        company_code = options['company_code']

        self.stdout.write(self.style.SUCCESS('=== Configuration du Multi-Tenancy ===\n'))

        # Étape 1 : Créer l'entreprise par défaut
        self.stdout.write('1. Création de l\'entreprise par défaut...')
        company, created = Company.objects.get_or_create(
            code=company_code,
            defaults={
                'name': company_name,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'   ✓ Entreprise créée : {company.name} ({company.code})'))
        else:
            self.stdout.write(self.style.WARNING(f'   ! Entreprise existante : {company.name} ({company.code})'))

        # Étape 2 : Assigner tous les utilisateurs à cette entreprise
        self.stdout.write('\n2. Assignation des utilisateurs à l\'entreprise...')
        users = User.objects.all()
        created_profiles = 0
        for user in users:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'company': company,
                    'role': 'admin' if user.is_superuser else 'employee'
                }
            )
            if created:
                created_profiles += 1
        self.stdout.write(self.style.SUCCESS(f'   ✓ {created_profiles} profils créés sur {users.count()} utilisateurs'))

        # Étape 3 : Assigner toutes les données existantes à cette entreprise
        self.stdout.write('\n3. Assignation des données existantes à l\'entreprise...')

        # Fournisseurs
        count = Fournisseur.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} fournisseurs assignés')

        # Catégories
        count = Categorie.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} catégories assignées')

        # Produits
        count = Produit.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} produits assignés')

        # Clients
        count = Client.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} clients assignés')

        # Warehouses
        count = Warehouse.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} entrepôts assignés')

        # Achats
        count = Achat.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} achats assignés')

        # Bons de livraison
        count = BonLivraison.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} bons de livraison assignés')

        # Factures
        count = Facture.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} factures assignées')

        # Sessions d'inventaire
        count = InventorySession.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} sessions d\'inventaire assignées')

        # Ventes
        count = Vente.objects.filter(company__isnull=True).update(company=company)
        self.stdout.write(f'   ✓ {count} ventes assignées')

        self.stdout.write(self.style.SUCCESS('\n=== Configuration terminée avec succès ! ==='))
        self.stdout.write(self.style.SUCCESS(f'\nTous les utilisateurs et données sont maintenant assignés à : {company.name}'))
        self.stdout.write(self.style.WARNING('\nNote : Les données sont maintenant isolées par entreprise.'))
        self.stdout.write(self.style.WARNING('Chaque utilisateur ne verra que les données de son entreprise.'))
