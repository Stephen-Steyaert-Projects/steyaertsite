from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    path("cards/", views.all_cards, name="all_cards"),
    path("owned/", views.owned_cards, name="owned_cards"),
    path("missing/", views.missing_cards, name="missing_cards"),
    path("cards/add/", views.add_card, name="add_card"),
    path("cards/<int:card_id>/edit/", views.edit_card, name="edit_card"),
    path("sets/add/", views.add_set, name="add_set"),
    path("cards/<int:card_id>/add-copy/<str:border>/", views.add_copy, name="add_copy"),
    path("cards/<int:card_id>/remove-copy/<str:border>/", views.remove_copy, name="remove_copy"),
    path("collection/save/", views.save_collection, name="save_collection"),
    path("collection/export/", views.export_collection_by_set, name="export_collection_by_set"),
    path("collection/import/", views.import_collection_by_set, name="import_collection_by_set"),
]