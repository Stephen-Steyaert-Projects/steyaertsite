import os
from io import BytesIO
from django.db import models
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from PIL import Image


class Set(models.Model):
    name = models.CharField(max_length=100)
    released = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to='sets/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.image and not self.image.name.endswith('.webp'):
            img = Image.open(self.image)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            output = BytesIO()
            img.save(output, format='WEBP', quality=85)
            output.seek(0)
            filename = self.name.lower().replace(' ', '_') + '.webp'
            self.image = ContentFile(output.read(), name=filename)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Card(models.Model):
    class Side(models.TextChoices):
        LIGHT = 'L', 'Light Side'
        DARK = 'D', 'Dark Side'

    class CardType(models.TextChoices):
        ADMIRALS_ORDER = 'admirals_order', "Admiral's Order"
        ALIEN_CHARACTER = 'alien_character', 'Alien'
        REBEL_CHARACTER = 'rebel_character', 'Rebel'
        DROID_CHARACTER = 'droid_character', 'Droid'
        IMPERIAL_CHARACTER = 'imperial_character', 'Imperial'
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
