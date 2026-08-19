from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="game_index"),
    path("create/", views.create_room, name="game_create_room"),
    path("join/", views.join_room, name="game_join_room"),
    path("<str:code>/", views.room, name="game_room"),
]
