from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Room


@login_required
def index(request):
    return render(request, "game/index.html")


@login_required
def room(request, code):
    room = get_object_or_404(Room, code=code.upper())
    if not room.has_player(request.user):
        raise Http404
    return render(request, "game/room.html", {"room": room})


@login_required
@require_POST
def create_room(request):
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

    if room.is_full and not room.has_player(request.user):
        messages.error(request, "That room is already full.")
        return redirect("game_index")

    if room.player_two_id is None and room.created_by_id != request.user.id:
        room.player_two = request.user
        room.save(update_fields=["player_two"])

    return redirect("game_room", code=room.code)
