"""Règles uniques de mise à jour du stock.

Deux compteurs existent :
  - ProductStock.quantity : stock d'un produit DANS UN DÉPÔT (la vraie source) ;
  - Produit.quantite      : total du produit = somme de ses ProductStock (TOUS les dépôts).

Toute écriture de stock passe par `appliquer_mouvement` (dépôt + journal + total), et tout
recalcul du total par `recalculer_quantite_produit` : une seule définition partout.
"""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone


class StockInsuffisant(ValidationError):
    """Stock du dépôt insuffisant pour une sortie."""


def message_erreur(exc):
    """Texte lisible d'une ValidationError Django (premier message)."""
    msgs = getattr(exc, 'messages', None)
    if msgs:
        return str(msgs[0])
    return str(exc)


def recalculer_quantite_produit(produit):
    """Produit.quantite = somme de ses stocks sur TOUS les dépôts. Retourne le total."""
    from .models import ProductStock
    total = ProductStock.objects.filter(produit_id=produit.pk).aggregate(total=Sum('quantity'))['total'] or 0
    produit.quantite = total
    produit.save(update_fields=['quantite'])
    return total


def quantite_entiere(valeur):
    """Convertit une quantité saisie en entier strictement positif, sinon ValidationError."""
    try:
        d = Decimal(str(valeur).strip().replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Quantité invalide")
    if d != d.to_integral_value():
        raise ValidationError("La quantité doit être un nombre entier")
    q = int(d)
    if q <= 0:
        raise ValidationError("La quantité doit être supérieure à 0")
    return q


def depot_par_defaut(company):
    """Dépôt par défaut configuré (Paramètres) pour l'entreprise, ou None. Ne crée rien."""
    from .models import SystemConfig
    try:
        w = SystemConfig.get_solo(company).default_warehouse
    except Exception:
        return None
    return w if (w is not None and w.is_active) else None


def stock_depot(produit, warehouse):
    """Stock actuel d'un produit dans un dépôt (0 si aucune ligne)."""
    from .models import ProductStock
    ps = ProductStock.objects.filter(produit_id=produit.pk, warehouse_id=warehouse.pk).first()
    return ps.quantity if ps else 0


def appliquer_mouvement(produit, warehouse, delta, source, note='', ref_id='', user=None, date=None):
    """Applique `delta` au stock de `produit` dans `warehouse` :
    vérifie le stock pour une sortie, met à jour ProductStock, journalise un StockMove
    et recalcule Produit.quantite. Tout ou rien. Retourne le StockMove (None si delta = 0).
    Lève StockInsuffisant (ValidationError) si le dépôt n'a pas assez de stock."""
    from .models import ProductStock, StockMove
    if warehouse is None:
        raise ValidationError("Choisissez un dépôt")
    delta = int(delta)
    if delta == 0:
        return None
    with transaction.atomic():
        ps, _ = ProductStock.objects.select_for_update().get_or_create(
            produit=produit, warehouse=warehouse, defaults={'quantity': 0})
        if ps.quantity + delta < 0:
            nom = getattr(produit, 'designation', '') or getattr(produit, 'reference', '')
            raise StockInsuffisant(
                f"Stock insuffisant dans {warehouse.name} : {ps.quantity} disponible(s) "
                f"pour {nom}, {-delta} demandé(s)")
        ps.quantity += delta
        ps.save(update_fields=['quantity'])
        move = StockMove.objects.create(
            produit=produit, warehouse=warehouse, delta=delta, source=source,
            ref_id=str(ref_id or '')[:50], note=str(note or '')[:200], date=date or timezone.now())
        recalculer_quantite_produit(produit)
    return move
