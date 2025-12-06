from django import forms

from API.models import *


class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        # Keep prixU and quantite in the model, but hide them in the UI
        fields = ('reference', 'code_barre', 'designation', 'prixU', 'quantite', 'fournisseur')
        widgets = {
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'code_barre': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
                        'prixU': forms.HiddenInput(),
            'quantite': forms.HiddenInput(),
            'fournisseur': forms.Select(attrs={'class': 'form-control'})
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set defaults if not provided
        self.fields['prixU'].required = False
        self.fields['quantite'].required = False
        if not self.initial.get('prixU'):
            self.initial['prixU'] = 0
        if not self.initial.get('quantite'):
            self.initial['quantite'] = 0
class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ('libelle', 'telephone', 'email', 'adresse')
