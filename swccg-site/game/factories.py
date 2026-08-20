import factory
from django.contrib.auth.models import User

from swccgdb.models import Card, CardText, Set

from .models import GameDeck, GameDeckCard, Room


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'player{n}')


class SetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Set

    name = factory.Sequence(lambda n: f'Set {n}')


class CardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Card

    name = factory.Sequence(lambda n: f'Card {n}')
    card_set = factory.SubFactory(SetFactory)
    card_type = Card.CardType.EFFECT
    side = Card.Side.DARK


class CardTextFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CardText

    card = factory.SubFactory(CardFactory)
    stats = factory.LazyFunction(dict)


class GameDeckFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GameDeck

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f'Deck {n}')
    side = Card.Side.DARK


class GameDeckCardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GameDeckCard

    game_deck = factory.SubFactory(GameDeckFactory)
    card = factory.SubFactory(CardFactory)
    quantity = 1


class RoomFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Room

    created_by = factory.SubFactory(UserFactory)
    player_two = factory.SubFactory(UserFactory)


DARK_FILLER_TYPES = [
    Card.CardType.IMPERIAL_CHARACTER,
    Card.CardType.DARK_JEDI_MASTER_CHARACTER,
    Card.CardType.SITH_CHARACTER,
    Card.CardType.ALIEN_CHARACTER,
    Card.CardType.DROID_CHARACTER,
    Card.CardType.STARSHIP,
    Card.CardType.VEHICLE,
    Card.CardType.WEAPON,
    Card.CardType.DEVICE,
    Card.CardType.EFFECT,
    Card.CardType.INTERRUPT,
    Card.CardType.EPIC_EVENT,
]
LIGHT_FILLER_TYPES = [
    Card.CardType.REBEL_CHARACTER,
    Card.CardType.REPUBLIC_CHARACTER,
    Card.CardType.JEDI_MASTER_CHARACTER,
    Card.CardType.ALIEN_CHARACTER,
    Card.CardType.DROID_CHARACTER,
    Card.CardType.STARSHIP,
    Card.CardType.VEHICLE,
    Card.CardType.WEAPON,
    Card.CardType.DEVICE,
    Card.CardType.EFFECT,
    Card.CardType.INTERRUPT,
    Card.CardType.EPIC_EVENT,
]


def make_full_deck(user, side, location_count=1, filler_count=59):
    """Builds a valid 60-card GameDeck for `user`/`side`: some Location cards plus a
    realistic mix of character/starship/effect/interrupt filler — with varying quantities
    per card (3x, 2x, 1x), like a real deck that runs multiple copies of the same card."""
    deck = GameDeckFactory(user=user, side=side)
    for _ in range(location_count):
        card = CardFactory(side=side, card_type=Card.CardType.LOCATION)
        GameDeckCardFactory(game_deck=deck, card=card, quantity=1)

    filler_types = DARK_FILLER_TYPES if side == Card.Side.DARK else LIGHT_FILLER_TYPES
    quantity_pattern = [3, 2, 1]
    remaining = filler_count
    i = 0
    while remaining > 0:
        qty = min(quantity_pattern[i % len(quantity_pattern)], remaining)
        card_type = filler_types[i % len(filler_types)]
        card = CardFactory(side=side, card_type=card_type)
        GameDeckCardFactory(game_deck=deck, card=card, quantity=qty)
        remaining -= qty
        i += 1
    return deck
