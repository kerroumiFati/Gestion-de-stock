#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Donnees de test (mock) pour verifier l'affichage du STOCK DEPOT
dans l'app mobile (ecran "Nouvelle commande").

Le champ `stock` de /API/distribution/produits/ est la somme des
ProductStock des entrepots actifs dont le code ne contient pas "van".
Si cette somme vaut 0 ou n'existe pas, l'API renvoie Produit.quantite.

Usage :
    python create_mock_stock_mobile.py
    python create_mock_stock_mobile.py --user livreur1
    python create_mock_stock_mobile.py --reset

Idempotent : relancer le script remet les quantites a jour.
"""
import argparse
import os
import sys
from decimal import Decimal

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_stock.settings')
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from API.models import (  # noqa: E402
    Categorie, Company, ProductStock, Produit, UserProfile, Warehouse,
)
from API.distribution_models import LivreurDistribution  # noqa: E402

User = get_user_model()

MOCK_PREFIX = 'MOCK-'
MOCK_PASSWORD = 'mock1234'

WAREHOUSES = [
    # code, nom, actif
    ('DEPOT-MOCK-A', 'Depot Mock A', True),
    ('DEPOT-MOCK-B', 'Depot Mock B', True),
    ('DEPOT-MOCK-INACTIF', 'Depot Mock Inactif', False),
    ('VAN-MOCK', 'Van Mock (exclu du stock depot)', True),
]

PRODUITS = [
    {
        'reference': 'MOCK-01',
        'code_barre': '9000000000001',
        'designation': 'Mock Eau 1.5L (stock normal)',
        'prixU': '40.00',
        'quantite': 0,
        'stocks': {'DEPOT-MOCK-A': 150},
        'attendu': '150 -> vert',
    },
    {
        'reference': 'MOCK-02',
        'code_barre': '9000000000002',
        'designation': 'Mock Coca 500ml (stock reparti A+B)',
        'prixU': '80.00',
        'quantite': 0,
        'stocks': {'DEPOT-MOCK-A': 20, 'DEPOT-MOCK-B': 5},
        'attendu': '25 -> vert',
    },
    {
        'reference': 'MOCK-03',
        'code_barre': '9000000000003',
        'designation': 'Mock Chips (stock faible = 3)',
        'prixU': '90.00',
        'quantite': 0,
        'stocks': {'DEPOT-MOCK-A': 3},
        'attendu': '3 -> orange, plafonne a 3',
    },
    {
        'reference': 'MOCK-04',
        'code_barre': '9000000000004',
        'designation': 'Mock Kit Kat (stock limite = 5)',
        'prixU': '65.00',
        'quantite': 0,
        'stocks': {'DEPOT-MOCK-A': 5},
        'attendu': '5 -> orange (seuil <= 5)',
    },
    {
        'reference': 'MOCK-05',
        'code_barre': '9000000000005',
        'designation': 'Mock Sprite (RUPTURE)',
        'prixU': '75.00',
        'quantite': 0,
        'stocks': {'DEPOT-MOCK-A': 0},
        'attendu': '0 -> rouge Rupture, grise, ajout refuse',
    },
    {
        'reference': 'MOCK-06',
        'code_barre': '9000000000006',
        'designation': 'Mock Oreo (stock uniquement dans le VAN)',
        'prixU': '120.00',
        'quantite': 0,
        'stocks': {'VAN-MOCK': 40},
        'attendu': '0 -> rupture (van exclu)',
    },
    {
        'reference': 'MOCK-07',
        'code_barre': '9000000000007',
        'designation': 'Mock Jus Orange (fallback quantite)',
        'prixU': '110.00',
        'quantite': 12,
        'stocks': {},
        'attendu': '12 -> vert (fallback Produit.quantite)',
    },
    {
        'reference': 'MOCK-08',
        'code_barre': '9000000000008',
        'designation': 'Mock Snickers (depot inactif + quantite=1)',
        'prixU': '70.00',
        'quantite': 1,
        'stocks': {'DEPOT-MOCK-INACTIF': 500},
        'attendu': '1 -> orange (depot inactif ignore), max 1',
    },
]


def line(char='-', n=70):
    print(char * n)


def pick_user(username):
    """Retourne (user, created) : utilisateur cible, cree si besoin."""
    if username:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': 'Livreur',
                'last_name': 'Mock',
                'is_active': True,
            },
        )
        if created:
            user.set_password(MOCK_PASSWORD)
            user.save()
        return user, created

    livreur = (
        LivreurDistribution.objects
        .filter(user__isnull=False)
        .select_related('user')
        .first()
    )
    if livreur:
        return livreur.user, False

    print('[ERREUR] Aucun livreur avec compte. Utilise --user <username>.')
    sys.exit(1)


def ensure_livreur(user, van):
    """Garantit un LivreurDistribution lie au user (login mobile)."""
    livreur = LivreurDistribution.objects.filter(user=user).first()
    if livreur:
        if not livreur.entrepot:
            livreur.entrepot = van
            livreur.save(update_fields=['entrepot'])
        return livreur, False

    matricule = ('LIV-' + user.username.upper())[:20]
    livreur = LivreurDistribution.objects.create(
        user=user,
        matricule=matricule,
        nom=(user.get_full_name() or user.username),
        telephone='0550000000',
        email=user.email or '',
        statut='actif',
        entrepot=van,
    )
    return livreur, True


def reset(company):
    line('=')
    print('  SUPPRESSION DES DONNEES MOCK')
    line('=')
    n, _ = Produit.objects.filter(
        company=company, reference__startswith=MOCK_PREFIX
    ).delete()
    print('  Produits supprimes : %s' % n)
    codes = [w[0] for w in WAREHOUSES]
    n, _ = Warehouse.objects.filter(
        company=company, code__in=codes
    ).delete()
    print('  Entrepots supprimes : %s' % n)
    n, _ = Categorie.objects.filter(
        company=company, nom='Mock Stock'
    ).delete()
    print('  Categories supprimees : %s' % n)
    print('[OK] Termine')


def create(user, company, user_created):
    line('=')
    print('  DONNEES MOCK - STOCK DEPOT POUR L APP MOBILE')
    line('=')
    print('  Utilisateur : %s' % user.username)
    print('  Entreprise  : %s' % (company or '(aucune)'))
    line()

    # 1. Entrepots
    wh = {}
    for code, name, active in WAREHOUSES:
        w, created = Warehouse.objects.get_or_create(
            company=company,
            code=code,
            defaults={'name': name, 'is_active': active},
        )
        if not created and (w.name != name or w.is_active != active):
            w.name, w.is_active = name, active
            w.save(update_fields=['name', 'is_active'])
        wh[code] = w
        tag = '[cree]  ' if created else '[existe]'
        print('  %s entrepot %-20s actif=%s' % (tag, code, active))

    # 2. Livreur lie a l utilisateur
    livreur, created = ensure_livreur(user, wh['VAN-MOCK'])
    tag = '[cree]  ' if created else '[existe]'
    print('  %s livreur %s (%s)' % (tag, livreur.matricule, livreur.nom))

    # 3. Categorie
    cat, created = Categorie.objects.get_or_create(
        company=company,
        nom='Mock Stock',
        defaults={'description': 'Produits de test stock depot'},
    )
    tag = '[cree]  ' if created else '[existe]'
    print('  %s categorie %s' % (tag, cat.nom))
    line()

    # 4. Produits + stocks
    for p in PRODUITS:
        prod, created = Produit.objects.get_or_create(
            company=company,
            reference=p['reference'],
            defaults={
                'code_barre': p['code_barre'],
                'designation': p['designation'],
                'categorie': cat,
                'prixU': Decimal(p['prixU']),
                'quantite': p['quantite'],
                'is_active': True,
            },
        )
        if not created:
            prod.designation = p['designation']
            prod.categorie = cat
            prod.prixU = Decimal(p['prixU'])
            prod.quantite = p['quantite']
            prod.is_active = True
            prod.save()

        # Remet a plat les stocks de ce produit dans les entrepots mock
        ProductStock.objects.filter(
            produit=prod, warehouse__in=wh.values()
        ).delete()
        for code, qty in p['stocks'].items():
            ProductStock.objects.create(
                produit=prod, warehouse=wh[code], quantity=qty
            )

        tag = '+' if created else '='
        print('  %s %s  %s' % (tag, prod.reference, prod.designation))
        print('      stocks=%s  quantite=%s' % (
            p['stocks'] or '{}', p['quantite']))
        print('      attendu mobile : %s' % p['attendu'])

    line('=')
    print('  COMMENT TESTER')
    line('=')
    print('  1. Backend : python manage.py runserver 0.0.0.0:8000')
    print('  2. App mobile : se connecter avec "%s"' % user.username)
    if user_created:
        print('     (compte cree, mot de passe : %s)' % MOCK_PASSWORD)
    print('  3. Parametres > Synchroniser (recharge le catalogue)')
    print('  4. Client > Nouvelle commande > Ajouter produit > "Mock"')
    print('  5. API : GET /API/distribution/produits/ -> champ "stock"')
    print()


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--user', help='username mobile a cibler (cree si absent)'
    )
    parser.add_argument(
        '--reset', action='store_true',
        help='supprime les donnees MOCK au lieu de les creer',
    )
    args = parser.parse_args()

    user, user_created = pick_user(args.user)
    if user_created:
        print('[OK] Utilisateur "%s" cree (mdp : %s)' % (
            user.username, MOCK_PASSWORD))
        company = Company.objects.filter(is_active=True).first()
        if company:
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'company': company, 'role': 'employee'},
            )
            user = User.objects.get(pk=user.pk)

    company = user.profile.company if hasattr(user, 'profile') else None
    if args.reset:
        reset(company)
    else:
        create(user, company, user_created)


if __name__ == '__main__':
    main()
