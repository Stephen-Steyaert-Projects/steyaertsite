from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    path("movies/all/", views.all_movies, name="all"),
    path("movies/add/", views.add, name="add"),
    path("movies/add/mass/", views.add_mass_movies, name="add_mass"),
    path("movies/random/", views.random, name="random_movie_generator"),
    path("movies/random/results/<uuid:result_id>/", views.random_results, name="random_results"),
    path("movies/<str:rating>/", views.movies_by_rating, name="movies_by_rating"),
    path("search/<str:title>/", views.search_results, name="search"),
]
