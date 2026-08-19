from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from swccgdb.models import Card

from .models import GameDeck, GameDeckCard, Room


def _valid_decks(user, side=None):
    qs = GameDeck.objects.filter(user=user).annotate(count=Sum('deck_cards__quantity'))
    if side:
        qs = qs.filter(side=side)
    return qs.filter(count=60).order_by('name')


def _has_both_valid_decks(user):
    return _valid_decks(user, Card.Side.LIGHT).exists() and _valid_decks(user, Card.Side.DARK).exists()


@login_required
def index(request):
    return render(request, "game/index.html", {"ready_to_play": _has_both_valid_decks(request.user)})


@login_required
@require_POST
def create_room(request):
    if not _has_both_valid_decks(request.user):
        messages.error(request, "You need a complete 60-card deck for both Light and Dark Side before you can play.")
        return redirect("game_index")
    room = Room.objects.create(created_by=request.user)
    return redirect("game_room", code=room.code)


@login_required
@require_POST
def join_room(request):
    code = request.POST.get("code", "").strip().upper()
    room = Room.objects.filter(code=code).first()

    if room is None:
        messages.error(request, f'No room found with code "{code}".')
        return redirect("game_index")

    if room.has_player(request.user):
        return redirect("game_room", code=room.code)

    if room.is_full:
        messages.error(request, "That room is already full.")
        return redirect("game_index")

    if not _has_both_valid_decks(request.user):
        messages.error(request, "You need a complete 60-card deck for both Light and Dark Side before you can play.")
        return redirect("game_index")

    room.player_two = request.user
    room.save(update_fields=["player_two"])
    return redirect("game_room", code=room.code)


@login_required
def room(request, code):
    room = get_object_or_404(Room, code=code.upper())
    if not room.has_player(request.user):
        raise Http404
    return render(request, "game/room.html", {
        "room": room,
        "light_decks": list(_valid_decks(request.user, Card.Side.LIGHT).values("id", "name")),
        "dark_decks": list(_valid_decks(request.user, Card.Side.DARK).values("id", "name")),
    })


@login_required
def deck_list(request):
    decks = GameDeck.objects.filter(user=request.user).annotate(count=Sum('deck_cards__quantity')).order_by('name')
    return render(request, "game/decks/list.html", {"decks": decks})


@login_required
def deck_new(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        side = request.POST.get("side")
        if name and side in Card.Side.values:
            deck = GameDeck.objects.create(user=request.user, name=name, side=side)
            return redirect("game_deck_edit", deck_id=deck.id)
        messages.error(request, "A name and side are required.")
    return render(request, "game/decks/new.html")


@login_required
def deck_edit(request, deck_id):
    deck = get_object_or_404(GameDeck, id=deck_id, user=request.user)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        if name:
            deck.name = name
            deck.save()
        return redirect("game_deck_edit", deck_id=deck.id)

    deck_cards = deck.deck_cards.select_related("card__card_set").order_by("card__name")
    in_deck_ids = set(deck_cards.values_list("card_id", flat=True))
    available = (
        Card.objects.filter(side=deck.side)
        .select_related("card_set")
        .order_by("name")
    )
    total = deck_cards.aggregate(t=Sum("quantity"))["t"] or 0
    return render(request, "game/decks/edit.html", {
        "deck": deck,
        "deck_cards": deck_cards,
        "available": available,
        "in_deck_ids": in_deck_ids,
        "total": total,
    })


@login_required
def deck_delete(request, deck_id):
    deck = get_object_or_404(GameDeck, id=deck_id, user=request.user)
    if request.method == "POST":
        deck.delete()
    return redirect("game_deck_list")


@login_required
def deck_add_card(request, deck_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    deck = get_object_or_404(GameDeck, id=deck_id, user=request.user)
    card = get_object_or_404(Card, id=request.POST.get("card_id"), side=deck.side)

    if GameDeckCard.objects.filter(game_deck=deck, card=card).exists():
        return JsonResponse({"error": "Card already in deck"}, status=400)

    current_total = deck.deck_cards.aggregate(t=Sum("quantity"))["t"] or 0
    if current_total >= 60:
        return JsonResponse({"error": "Deck is already at 60 cards"}, status=400)

    GameDeckCard.objects.create(game_deck=deck, card=card, quantity=1)
    return JsonResponse({"success": True, "total": current_total + 1})


@login_required
def deck_remove_card(request, deck_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    deck = get_object_or_404(GameDeck, id=deck_id, user=request.user)
    GameDeckCard.objects.filter(game_deck=deck, card_id=request.POST.get("card_id")).delete()
    total = deck.deck_cards.aggregate(t=Sum("quantity"))["t"] or 0
    return JsonResponse({"success": True, "total": total})


@login_required
def deck_update_card(request, deck_id):
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)
    deck = get_object_or_404(GameDeck, id=deck_id, user=request.user)
    try:
        quantity = int(request.POST.get("quantity", 1))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Invalid quantity"}, status=400)
    if quantity < 1:
        return JsonResponse({"error": "Quantity must be at least 1"}, status=400)

    deck_card = get_object_or_404(GameDeckCard, game_deck=deck, card_id=request.POST.get("card_id"))
    other_total = deck.deck_cards.exclude(id=deck_card.id).aggregate(t=Sum("quantity"))["t"] or 0
    if other_total + quantity > 60:
        return JsonResponse({"error": "Deck cannot exceed 60 cards"}, status=400)

    deck_card.quantity = quantity
    deck_card.save()
    return JsonResponse({"success": True, "total": other_total + quantity, "quantity": quantity})
