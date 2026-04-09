from django.db import models
from django.contrib.auth.models import User


class Set(models.Model):
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.name


class Card(models.Model):
    class Side(models.TextChoices):
        LIGHT = 'L', 'Light Side'
        DARK = 'D', 'Dark Side'

    class CardType(models.TextChoices):
        ADMIRALS_ORDER = 'admirals_order', "Admiral's Order"
        CHARACTER = 'character', 'Character'
        CREATURE = 'creature', 'Creature'
        DEVICE = 'device', 'Device'
        EFFECT = 'effect', 'Effect'
        EPIC_EVENT = 'epic_event', 'Epic Event'
        INTERRUPT = 'interrupt', 'Interrupt'
        JEDI_TEST = 'jedi_test', 'Jedi Test'
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
    card_type = models.CharField(max_length=20, choices=CardType.choices)
    side = models.CharField(max_length=1, choices=Side.choices)
    rarity = models.CharField(max_length=2, choices=Rarity.choices, blank=True)
    image = models.ImageField(upload_to='cards/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.card_set})"


class OwnedCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_cards')
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='owned_by')
    copies = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'card')

    def __str__(self):
        return f"{self.user} — {self.card} x{self.copies}"
