from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="game_index"),
    path("create/", views.create_room, name="game_create_room"),
    path("join/", views.join_room, name="game_join_room"),
    path("decks/", views.deck_list, name="game_deck_list"),
    path("decks/new/", views.deck_new, name="game_deck_new"),
    path("decks/<uuid:deck_id>/edit/", views.deck_edit, name="game_deck_edit"),
    path("decks/<uuid:deck_id>/delete/", views.deck_delete, name="game_deck_delete"),
    path("decks/<uuid:deck_id>/add-card/", views.deck_add_card, name="game_deck_add_card"),
    path("decks/<uuid:deck_id>/remove-card/", views.deck_remove_card, name="game_deck_remove_card"),
    path("decks/<uuid:deck_id>/update-card/", views.deck_update_card, name="game_deck_update_card"),
    path("<str:code>/", views.room, name="game_room"),
]
