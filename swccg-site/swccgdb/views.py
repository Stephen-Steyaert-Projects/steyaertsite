from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField, Prefetch
from .models import Set, Card, OwnedCard

# Create your views here.
def index(request):
    return render(request, 'swccgdb/index.html')

def all_cards(request):
    card_order = Card.objects.annotate(
        side_order=Case(
            When(side='L', then=Value(0)),
            When(side='D', then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ),
        type_order=Case(
            When(card_type='character', then=Value(0)),
            When(card_type='device', then=Value(1)),
            When(card_type='effect', then=Value(2)),
            When(card_type='interrupt', then=Value(3)),
            When(card_type='location', then=Value(4)),
            When(card_type='starship', then=Value(5)),
            When(card_type='vehicle', then=Value(6)),
            When(card_type='weapon', then=Value(7)),
            default=Value(8),
            output_field=IntegerField(),
        ),
    ).order_by('side_order', 'type_order', 'name')

    sets = Set.objects.prefetch_related(
        Prefetch('cards', queryset=card_order)
    ).order_by('name')
    return render(request, 'swccgdb/all-cards.html', {'sets': sets})


@login_required
def home(request):
    return render(request, 'swccgdb/home.html')

@login_required
def all_owned(request):
    owned = (
        OwnedCard.objects
        .filter(user=request.user, copies__gt=0)
        .select_related('card', 'card__card_set')
        .annotate(
            side_order=Case(
                When(card__side='L', then=Value(0)),
                When(card__side='D', then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            type_order=Case(
                When(card__card_type='character', then=Value(0)),
                When(card__card_type='device', then=Value(1)),
                When(card__card_type='effect', then=Value(2)),
                When(card__card_type='interrupt', then=Value(3)),
                When(card__card_type='location', then=Value(4)),
                When(card__card_type='starship', then=Value(5)),
                When(card__card_type='vehicle', then=Value(6)),
                When(card__card_type='weapon', then=Value(7)),
                default=Value(8),
                output_field=IntegerField(),
            ),
        )
        .order_by('card__card_set__name', 'side_order', 'type_order', 'card__name')
    )

    sets = {}
    for owned_card in owned:
        set_name = owned_card.card.card_set.name
        sets.setdefault(set_name, []).append(owned_card)

    return render(request, 'swccgdb/all-owned.html', {'sets': sets})

