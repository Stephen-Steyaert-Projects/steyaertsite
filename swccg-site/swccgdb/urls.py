from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    path("cards/", views.all_cards, name="all_cards"),
    path("owned/", views.all_owned, name="all_owned"),
]