"""
Modification d'une commande client depuis l'application mobile (prevendeur ou livreur),
par exemple quand le client change d'avis sur un produit ou une quantite.

Regles appliquees cote serveur (l'application applique les memes, mais le serveur fait foi) :
- la commande doit etre encore ouverte : ni livree, ni annulee ;
- elle ne doit pas etre entierement payee, et le nouveau total ne peut pas descendre sous
  le montant deja encaisse ;
- au moins une ligne, quantites strictement positives, un produit par ligne, produits
  actifs et de la meme entreprise ;
- le prix d'une ligne existante est conserve ; un produit ajoute prend le prix envoye par
  l'application (prix selon le type de client) ou, a defaut, le prix du produit ;
- tout est applique en une transaction et trace dans `notes_preparation`.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

STATUTS_MODIFIABLES = ('pending', 'confirmed', 'preparing', 'ready')


class ModificationRefusee(Exception):
    """Modification refusee par une regle metier. `code` = statut HTTP a renvoyer."""

    def __init__(self, message, code=400, champ=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.champ = champ


def _decimal(valeur, libelle):
    try:
        d = Decimal(str(valeur).strip().replace(',', '.'))
    except (InvalidOperation, AttributeError, ValueError):
        raise ModificationRefusee(f"{libelle} invalide : « {valeur} ».")
    if not d.is_finite():
        raise ModificationRefusee(f"{libelle} invalide : « {valeur} ».")
    return d


def _fmt(q):
    q = Decimal(q)
    return str(q.quantize(Decimal('1'))) if q == q.to_integral_value() else str(q.normalize())


def verifier_commande_modifiable(commande):
    if commande.statut not in STATUTS_MODIFIABLES:
        raise ModificationRefusee(
            f"La commande {commande.reference} est {commande.get_statut_display().lower()} : "
            "elle ne peut plus être modifiée.", code=409)
    if commande.est_paye:
        raise ModificationRefusee(
            f"La commande {commande.reference} est entièrement payée : elle ne peut plus être modifiée.", code=409)


def _normaliser_lignes(commande, lignes):
    """Valide les lignes recues et retourne [(produit, quantite, prix|None, tva|None)]."""
    from .models import Produit

    if not isinstance(lignes, list) or not lignes:
        raise ModificationRefusee("La commande doit contenir au moins un produit.", champ='lignes')
    if len(lignes) > 500:
        raise ModificationRefusee("Trop de lignes dans la commande.", champ='lignes')

    resultat, vus = [], set()
    for position, brut in enumerate(lignes, start=1):
        if not isinstance(brut, dict):
            raise ModificationRefusee(f"Ligne {position} invalide.", champ='lignes')
        pid = brut.get('produit', brut.get('produit_id'))
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            raise ModificationRefusee(f"Ligne {position} : produit non précisé.", champ='lignes')
        if pid in vus:
            raise ModificationRefusee(f"Ligne {position} : le produit apparaît plusieurs fois dans la commande.",
                                      champ='lignes')
        vus.add(pid)

        produit = Produit.objects.filter(pk=pid).first()
        if produit is None:
            raise ModificationRefusee(f"Ligne {position} : produit #{pid} introuvable.", champ='lignes')
        deja_dans_commande = commande.lignes.filter(produit_id=pid).exists()
        if not produit.is_active and not deja_dans_commande:
            raise ModificationRefusee(f"« {produit.designation} » n'est plus commercialisé.", champ='lignes')
        if (commande.company_id and produit.company_id and produit.company_id != commande.company_id):
            raise ModificationRefusee(f"« {produit.designation} » n'appartient pas à cette entreprise.",
                                      code=403, champ='lignes')

        quantite = _decimal(brut.get('quantite'), f"Quantité de « {produit.designation} »")
        if quantite <= 0:
            raise ModificationRefusee(
                f"La quantité de « {produit.designation} » doit être supérieure à zéro. "
                "Pour retirer un produit, supprimez sa ligne.", champ='lignes')
        if quantite > Decimal('99999999'):
            raise ModificationRefusee(f"Quantité de « {produit.designation} » trop grande.", champ='lignes')
        quantite = quantite.quantize(Decimal('0.01'))

        prix = brut.get('prix_unitaire_ht', brut.get('prix_unitaire'))
        prix = _decimal(prix, f"Prix de « {produit.designation} »") if prix not in (None, '') else None
        if prix is not None and prix < 0:
            raise ModificationRefusee(f"Prix de « {produit.designation} » négatif.", champ='lignes')
        tva = brut.get('taux_tva')
        tva = _decimal(tva, f"TVA de « {produit.designation} »") if tva not in (None, '') else None
        if tva is not None and not (0 <= tva <= 100):
            raise ModificationRefusee(f"TVA de « {produit.designation} » invalide.", champ='lignes')

        resultat.append((produit, quantite, prix, tva))
    return resultat


def modifier_lignes_commande(commande, lignes, user, notes=None):
    """
    Remplace le contenu de la commande par `lignes` (ajouts, retraits, quantites).
    Retourne (commande, modifications) ou leve ModificationRefusee.
    """
    from .distribution_models import CommandeClient, LigneCommandeClient

    with transaction.atomic():
        commande = CommandeClient.objects.select_for_update().get(pk=commande.pk)
        verifier_commande_modifiable(commande)
        nouvelles = _normaliser_lignes(commande, lignes)

        existantes = {l.produit_id: l for l in commande.lignes.select_related('produit')}
        tva_defaut = next((l.taux_tva for l in existantes.values()), Decimal('0'))
        modifications = []
        conserves = set()

        for produit, quantite, prix, tva in nouvelles:
            ligne = existantes.get(produit.id)
            if ligne is not None:
                conserves.add(produit.id)
                if ligne.quantite != quantite:
                    modifications.append(f"{produit.designation} {_fmt(ligne.quantite)}→{_fmt(quantite)}")
                    ligne.quantite = quantite
                    ligne.save()   # recalcule HT / TVA / TTC, le prix de la ligne est conserve
            else:
                LigneCommandeClient.objects.create(
                    commande=commande, produit=produit, quantite=quantite,
                    prix_unitaire_ht=prix if prix is not None else (produit.prixU or Decimal('0')),
                    taux_tva=tva if tva is not None else tva_defaut,
                )
                modifications.append(f"+{produit.designation} x{_fmt(quantite)}")

        for pid, ligne in existantes.items():
            if pid not in conserves:
                modifications.append(f"-{ligne.produit.designation}")
                ligne.delete()

        commande.calculer_totaux()
        commande.refresh_from_db()
        if commande.montant_paye and commande.montant_total_ttc < commande.montant_paye:
            raise ModificationRefusee(
                f"Le nouveau total ({commande.montant_total_ttc} DA) est inférieur au montant déjà "
                f"encaissé ({commande.montant_paye} DA).")   # la transaction annule tout

        champs = ['synced_at', 'updated_at']
        if notes is not None and (notes or '') != (commande.notes or ''):
            commande.notes = notes
            champs.append('notes')
            modifications.append('notes modifiées')
        if modifications:
            auteur = user.get_full_name() or user.username
            trace = (f"[{timezone.localtime().strftime('%d/%m/%Y %H:%M')}] Modifiée par {auteur} : "
                     + ', '.join(modifications))
            commande.notes_preparation = ((commande.notes_preparation or '').rstrip() + '\n' + trace).strip()
            champs.append('notes_preparation')
        commande.synced_at = timezone.now()
        commande.save(update_fields=champs)
    return commande, modifications
