from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    path("movies/all/", views.all_movies, name="all"),
    path("movies/g/", views.g_movies, name="g_movies"),
    path("movies/pg/", views.pg_movies, name="pg_movies"),
    path("movies/pg-13/", views.pg13_movies, name="pg-13_movies"),
    path("movies/r/", views.r_movies, name="r_movies"),
    path("movies/nr/", views.nr_movies, name="nr_movies"),
    path("movies/tv/", views.tv_movies, name="tv_shows"),
    path("movies/add/", views.add, name="add"),
    path("movies/random/", views.random, name="random_movie_generator"),
    path("movies/random/results/", views.random_results, name="random_results"),
    path("search/<str:title>/", views.search_results, name="search"),
    path("movies/add/mass/", views.add_mass_movies, name="add_mass"),
]
