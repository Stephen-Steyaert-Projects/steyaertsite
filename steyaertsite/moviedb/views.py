from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import AddMovieForm, RandomMovieForm
from random import sample, shuffle
from .models import Movie


def index(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, "moviedb/index.html")


@login_required(login_url="/auth/login")
def home(request):
    return render(request, "moviedb/home.html")


@login_required(login_url="/auth/login")
def all_movies(request):
    g_movies = Movie.objects.all().filter(rating="G").order_by("title")

    pg_movies = Movie.objects.all().filter(rating="PG").order_by("title")

    pg13_movies = Movie.objects.all().filter(rating="PG-13").order_by("title")

    r_movies = Movie.objects.all().filter(rating="R").order_by("title")

    nr_movies = Movie.objects.all().filter(rating="NR").order_by("title")

    tv_movies = Movie.objects.all().filter(rating="TV").order_by("title")

    ctx = {
        "g_movies": g_movies if g_movies else [],
        "pg_movies": pg_movies if pg_movies else [],
        "pg13_movies": pg13_movies if pg_movies else [],
        "r_movies": r_movies if r_movies else [],
        "nr_movies": nr_movies if nr_movies else [],
        "tv_movies": tv_movies if tv_movies else [],
    }

    return render(request, "moviedb/all_movies.html", ctx)


@login_required(login_url="/auth/login")
def g_movies(request):
    g_movies = Movie.objects.all().filter(rating="G").order_by("title")

    ctx = {"g_movies": g_movies}
    return render(request, "moviedb/g_movies.html", ctx)


@login_required(login_url="/auth/login")
def pg_movies(request):
    pg_movies = Movie.objects.all().filter(rating="PG").order_by("title")

    ctx = {"pg_movies": pg_movies}
    return render(request, "moviedb/pg_movies.html", ctx)


@login_required(login_url="/auth/login")
def pg13_movies(request):
    pg13_movies = Movie.objects.all().filter(rating="PG-13").order_by("title")

    ctx = {"pg13_movies": pg13_movies}
    return render(request, "moviedb/pg13_movies.html", ctx)


@login_required(login_url="/auth/login")
def r_movies(request):
    r_movies = Movie.objects.all().filter(rating="R").order_by("title")

    ctx = {"r_movies": r_movies}
    return render(request, "moviedb/r_movies.html", ctx)


@login_required(login_url="/auth/login")
def nr_movies(request):
    nr_movies = Movie.objects.all().filter(rating="NR").order_by("title")

    ctx = {"nr_movies": nr_movies}
    return render(request, "moviedb/nr_movies.html", ctx)


@login_required(login_url="/auth/login")
def tv_movies(request):
    tv_movies = Movie.objects.all().filter(rating="TV").order_by("title")

    ctx = {"tv_movies": tv_movies}
    return render(request, "moviedb/tv_shows.html", ctx)


@login_required(login_url="/auth/login")
def add(request):
    if request.method == "POST":
        form = AddMovieForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("home")
    else:
        form = AddMovieForm()

    return render(request, "moviedb/add.html", {"form": form})


@login_required(login_url="/auth/login")
def search_results(request, title: str):
    _title = title.strip()
    if not _title or _title.lower() == "title":
        ctx = {"titles": ["Invalid Search"], "t": _title}
    else:
        results = [m for m in Movie.objects.all() if _title.lower() in m.title.lower()]
        if results:
            ctx = {"titles": results, "t": _title}
        else:
            ctx = {
                "titles": [f'There are no titles that match the query "{_title}"'],
                "t": title,
            }
    return render(request, "moviedb/search_results.html", ctx)


@login_required(login_url="/auth/login")
def random(request):
    form = RandomMovieForm()
    return render(request, "moviedb/random.html", {"form": form})

@login_required(login_url="/auth/login")
def random_results(request):
    if request.method == "GET":
        form = RandomMovieForm(request.GET)
        if form.is_valid():
            num_movies = form.cleaned_data["movies"]
            selected_ratings = form.cleaned_data["ratings"]

            movies = Movie.objects.filter(rating__in=selected_ratings).order_by("title")
            movie_list = [[movie.title, movie.rating] for movie in movies]

            shuffle(movie_list)

            if len(movie_list) < num_movies:
                num_movies = 1

            generated = sample(movie_list, num_movies)

            return render(request, "moviedb/random_results.html", {"generated": generated})

    return redirect("random_movie_generator")  # or your 'random' route name

