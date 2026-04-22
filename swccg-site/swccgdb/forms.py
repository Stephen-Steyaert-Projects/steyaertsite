from django import forms
from .models import Card, Set


class SetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = name != 'image'

    released = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'form-control bg-dark text-light border-secondary',
            'type': 'date',
            'min': '1995-01-01',
            'max': '2001-12-12',
            'value': '1995-12-01',
            'placeholder': 'Released',
        })
    )

    def clean_name(self):
        name = self.cleaned_data['name']
        lowercase_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor',
                           'at', 'by', 'in', 'of', 'on', 'to', 'up', 'with', 'from'}
        words = name.strip().split()
        def _fmt(word, i):
            if word.isupper() and len(word) > 1:
                return word  # preserve roman numerals like II, III, IV
            if i == 0 or word.lower() not in lowercase_words:
                return word.capitalize()
            return word.lower()

        name = ' '.join(_fmt(word, i) for i, word in enumerate(words))
        if Set.objects.filter(name__iexact=name).exclude(pk=self.instance.pk if self.instance.pk else None).exists():
            raise forms.ValidationError(f'A set named "{name}" already exists.')
        return name

    class Meta:
        model = Set
        fields = ['name', 'released', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control bg-dark text-light border-secondary', 'placeholder': 'Name'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control bg-dark text-light border-secondary', 'accept': 'image/png,image/jpeg,image/webp,image/gif'}),
        }


class CardForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.required = name != 'rarity'

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        card_set = cleaned_data.get('card_set')
        side = cleaned_data.get('side')
        if name and card_set:
            normalized = name.lstrip('•').strip()
            if Card.objects.filter(
                card_set=card_set,
                side=side
            ).exclude(
                pk=self.instance.pk if self.instance.pk else None
            ).filter(
                name__iregex=rf'^•*{normalized}$'
            ).exists():
                raise forms.ValidationError(f'A card named "{name}" already exists in this set.')
        return cleaned_data

    class Meta:
        model = Card
        fields = ['name', 'card_set', 'card_type', 'side', 'rarity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control bg-dark text-light border-secondary', 'placeholder': 'Name'}),
            'card_set': forms.Select(attrs={'class': 'form-select bg-dark text-light border-secondary', 'placeholder': 'Set'}),
            'card_type': forms.Select(attrs={'class': 'form-select bg-dark text-light border-secondary', 'placeholder': 'Type'}),
            'side': forms.Select(attrs={'class': 'form-select bg-dark text-light border-secondary', 'placeholder': 'Side'}),
            'rarity': forms.Select(attrs={'class': 'form-select bg-dark text-light border-secondary', 'placeholder': 'Rarity'}),
        }
