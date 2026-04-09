from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField, Prefetch, Count, Q
from .models import Set, Card, OwnedCard

# Create your views here.
def index(request):
    return render(request, 'swccgdb/index.html')

def all_cards(request):
    card_order = Card.objects.annotate(
        side_order=_side_order(),
        type_order=_card_type_order(),
    ).order_by('side_order', 'type_order', 'name')

    sets = Set.objects.prefetch_related(
        Prefetch('cards', queryset=card_order)
    ).order_by('name')
    return render(request, 'swccgdb/all-cards.html', {'sets': sets})


@login_required
def home(request):
    sets = Set.objects.annotate(
        total=Count('cards'),
        owned=Count('cards', filter=Q(
            cards__owned_by__user=request.user,
            cards__owned_by__copies__gt=0,
        )),
    ).order_by('released', 'name')

    for s in sets:
        s.pct = round(s.owned / s.total * 100) if s.total else 0

    total_cards = sum(s.total for s in sets)
    total_owned = sum(s.owned for s in sets)

    return render(request, 'swccgdb/home.html', {
        'sets': sets,
        'total_cards': total_cards,
        'total_owned': total_owned,
    })

def _card_type_order(prefix=''):
    f = f'{prefix}card_type' if prefix else 'card_type'
    return Case(
        When(**{f: 'admirals_order'}, then=Value(0)),
        When(**{f: 'character'}, then=Value(1)),
        When(**{f: 'creature'}, then=Value(2)),
        When(**{f: 'device'}, then=Value(3)),
        When(**{f: 'effect'}, then=Value(4)),
        When(**{f: 'epic_event'}, then=Value(5)),
        When(**{f: 'interrupt'}, then=Value(6)),
        When(**{f: 'jedi_test'}, then=Value(7)),
        When(**{f: 'location'}, then=Value(8)),
        When(**{f: 'objective'}, then=Value(9)),
        When(**{f: 'starship'}, then=Value(10)),
        When(**{f: 'vehicle'}, then=Value(11)),
        When(**{f: 'weapon'}, then=Value(12)),
        default=Value(13),
        output_field=IntegerField(),
    )

def _side_order(prefix=''):
    f = f'{prefix}side' if prefix else 'side'
    return Case(
        When(**{f: 'L'}, then=Value(0)),
        When(**{f: 'D'}, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )

@login_required
def all_owned(request):
    owned_ids = OwnedCard.objects.filter(user=request.user, copies__gt=0).values_list('card_id', flat=True)

    owned = (
        OwnedCard.objects
        .filter(user=request.user, copies__gt=0)
        .select_related('card', 'card__card_set')
        .annotate(side_order=_side_order('card__'), type_order=_card_type_order('card__'))
        .order_by('card__card_set__name', 'side_order', 'type_order', 'card__name')
    )

    missing = (
        Card.objects
        .exclude(id__in=owned_ids)
        .select_related('card_set')
        .annotate(side_order=_side_order(), type_order=_card_type_order())
        .order_by('card_set__name', 'side_order', 'type_order', 'name')
    )

    owned_sets = {}
    for oc in owned:
        owned_sets.setdefault(oc.card.card_set.name, []).append(oc)

    missing_sets = {}
    for card in missing:
        missing_sets.setdefault(card.card_set.name, []).append(card)

    return render(request, 'swccgdb/all-owned.html', {
        'owned_sets': owned_sets,
        'missing_sets': missing_sets,
    })

