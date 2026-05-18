import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User


class Set(models.Model):
    name = models.CharField(max_length=100)
    released = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to='sets/', blank=True, null=True)

    def __str__(self):
        return self.name


class Card(models.Model):
    class Side(models.TextChoices):
        LIGHT = 'L', 'Light Side'
        DARK = 'D', 'Dark Side'

    class CardType(models.TextChoices):
        # Light Side Characters
        JEDI_MASTER_CHARACTER = 'jedi_master_character', 'Jedi Master'
        JEDI_TEST = 'jedi_test', 'Jedi Test'
        REBEL_CHARACTER = 'rebel_character', 'Rebel'
        REPUBLIC_CHARACTER = 'republic_character', 'Republic'
        # Shared Characters
        ALIEN_CHARACTER = 'alien_character', 'Alien'
        DROID_CHARACTER = 'droid_character', 'Droid'
        # Dark Side Characters
        DARK_JEDI_MASTER_CHARACTER = 'dark_jedi_master_character', 'Dark Jedi Master'
        IMPERIAL_CHARACTER = 'imperial_character', 'Imperial'
        SITH_CHARACTER = 'sith_character', 'Sith'
        # Non-Character Types
        ADMIRALS_ORDER = 'admirals_order', "Admiral's Order"
        CREATURE = 'creature', 'Creature'
        DEFENSIVE_SHIELD = 'defensive_shield', 'Defensive Shield'
        DEVICE = 'device', 'Device'
        EFFECT = 'effect', 'Effect'
        EPIC_EVENT = 'epic_event', 'Epic Event'
        GAME_AID = 'game_aid', 'Game Aid'
        INTERRUPT = 'interrupt', 'Interrupt'
        LOCATION = 'location', 'Location'
        OBJECTIVE = 'objective', 'Objective'
        STARSHIP = 'starship', 'Starship'
        VEHICLE = 'vehicle', 'Vehicle'
        WEAPON = 'weapon', 'Weapon'

    class Rarity(models.TextChoices):
        C = 'C', 'C'
        C1 = 'C1', 'C1'
        C2 = 'C2', 'C2'
        U = 'U', 'U'
        U1 = 'U1', 'U1'
        U2 = 'U2', 'U2'
        R = 'R', 'R'
        R1 = 'R1', 'R1'
        R2 = 'R2', 'R2'
        UR = 'UR', 'UR'
        XR = 'XR', 'XR'
        F = 'F', 'F'
        PM = 'PM', 'PM'

    name = models.CharField(max_length=200)
    card_set = models.ForeignKey(Set, on_delete=models.PROTECT, related_name='cards')
    card_type = models.CharField(max_length=30, choices=CardType.choices)
    secondary_card_type = models.CharField(max_length=30, choices=CardType.choices, blank=True, null=True)
    side = models.CharField(max_length=1, choices=Side.choices)
    rarity = models.CharField(max_length=2, choices=Rarity.choices, blank=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.card_set})"


class OwnedCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cards')
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='owned_by')
    copies_bb = models.PositiveSmallIntegerField(default=0, verbose_name='Black Border (Limited)')
    copies_wb = models.PositiveSmallIntegerField(default=0, verbose_name='White Border (Unlimited)')

    class Meta:
        unique_together = ('user', 'card')

    @property
    def copies(self):
        return self.copies_bb + self.copies_wb

    def __str__(self):
        return f"{self.user} — {self.card} BB:{self.copies_bb} WB:{self.copies_wb}"

class Deck(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    name = models.CharField(max_length=200)
    is_public = models.BooleanField(default=False)
    cards = models.ManyToManyField(OwnedCard, through='DeckCard', related_name='decks')
    saved_by = models.ManyToManyField(User, related_name='saved_decks', blank=True)

    def clean(self):
        total = (
            self.deck_cards.aggregate(total=models.Sum('quantity'))['total'] or 0
        )
        if total > 60:
            raise ValidationError(f"Deck cannot exceed 60 cards (current: {total}).")

    def __str__(self):
        return f"{self.name} ({self.user})"


class DeckCard(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='deck_cards')
    owned_card = models.ForeignKey(OwnedCard, on_delete=models.CASCADE, related_name='deck_cards')
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ('deck', 'owned_card')

    def clean(self):
        if self.quantity > self.owned_card.copies:
            raise ValidationError(
                f"You only own {self.owned_card.copies} copy/copies of {self.owned_card.card}."
            )

    def __str__(self):
        return f"{self.deck} — {self.owned_card.card} x{self.quantity}"
