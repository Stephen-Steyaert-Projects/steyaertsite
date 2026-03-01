from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from .forms import AddMovieForm, RandomMovieForm
from random import sample, shuffle
from .models import Movie
from django.contrib import messages
import csv
import io
from openpyxl import load_workbook


def index(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "moviedb/index.html")


@login_required(login_url="/auth/login")
def home(request):
    return render(request, "moviedb/home.html")


@login_required(login_url="/auth/login")
def all_movies(request):
    g_movies = (
        Movie.objects.all()
        .filter(rating="G")
        .order_by("title")
        .values("title")
        .distinct()
    )

    pg_movies = (
        Movie.objects.all()
        .filter(rating="PG")
        .order_by("title")
        .values("title")
        .distinct()
    )

    pg13_movies = (
        Movie.objects.all()
        .filter(rating="PG-13")
        .order_by("title")
        .values("title")
        .distinct()
    )

    r_movies = (
        Movie.objects.all()
        .filter(rating="R")
        .order_by("title")
        .values("title")
        .distinct()
    )

    nr_movies = (
        Movie.objects.all()
        .filter(rating="NR")
        .order_by("title")
        .values("title")
        .distinct()
    )

    tv_movies = (
        Movie.objects.all()
        .filter(rating="TV")
        .order_by("title")
        .values("title")
        .distinct()
    )

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
    g_movies = g_movies = (
        Movie.objects.filter(rating="G").order_by("title").values("title").distinct()
    )

    ctx = {"g_movies": g_movies}
    return render(request, "moviedb/g_movies.html", ctx)


@login_required(login_url="/auth/login")
def pg_movies(request):
    pg_movies = (
        Movie.objects.all()
        .filter(rating="PG")
        .order_by("title")
        .values("title")
        .distinct()
    )

    ctx = {"pg_movies": pg_movies}
    return render(request, "moviedb/pg_movies.html", ctx)


@login_required(login_url="/auth/login")
def pg13_movies(request):
    pg13_movies = (
        Movie.objects.all()
        .filter(rating="PG-13")
        .order_by("title")
        .values("title")
        .distinct()
    )

    ctx = {"pg13_movies": pg13_movies}
    return render(request, "moviedb/pg13_movies.html", ctx)


@login_required(login_url="/auth/login")
def r_movies(request):
    r_movies = (
        Movie.objects.all()
        .filter(rating="R")
        .order_by("title")
        .values("title")
        .distinct()
    )

    ctx = {"r_movies": r_movies}
    return render(request, "moviedb/r_movies.html", ctx)


@login_required(login_url="/auth/login")
def nr_movies(request):
    nr_movies = (
        Movie.objects.all()
        .filter(rating="NR")
        .order_by("title")
        .values("title")
        .distinct()
    )

    ctx = {"nr_movies": nr_movies}
    return render(request, "moviedb/nr_movies.html", ctx)


@login_required(login_url="/auth/login")
def tv_movies(request):
    tv_movies = (
        Movie.objects.all()
        .filter(rating="TV")
        .order_by("title")
        .values("title")
        .distinct()
    )

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
                "titles": [],
                "t": _title,
            }
    return render(request, "moviedb/search_results.html", ctx)


@login_required(login_url="/auth/login")
def random(request):
    form = RandomMovieForm()
    return render(request, "moviedb/random.html", {"form": form})


@login_required(login_url="/auth/login")
def random_results(request):
    if request.method == "POST":
        form = RandomMovieForm(request.POST)
        if form.is_valid():
            num_movies = form.cleaned_data["movies"]
            selected_ratings = form.cleaned_data["ratings"]

            movies = (
                Movie.objects.filter(rating__in=selected_ratings)
                .order_by("title")
                .values("title", "rating")
                .distinct()
            )

            movie_list = [{"title": m["title"], "rating": m["rating"]} for m in movies]
            shuffle(movie_list)

            if len(movie_list) < num_movies:
                num_movies = len(movie_list)

            generated = sample(movie_list, num_movies)

            # Store in session
            request.session["random_results"] = generated

            # Redirect so that reloads won't resubmit the form
            return redirect("random_results")

    # If GET: show results only if they exist in session
    generated = request.session.pop("random_results", None)

    if generated:
        return render(request, "moviedb/random_results.html", {"generated": generated})

    # No results → back to generator
    return redirect("random_movie_generator")




def is_admin(user):
    return user.is_staff


@login_required(login_url="/auth/login")
@user_passes_test(is_admin)
def add_mass_movies(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        uploaded_file = request.FILES["csv_file"]
        file_name = uploaded_file.name.lower()

        if not (file_name.endswith(".csv") or file_name.endswith(".xlsx")):
            messages.error(request, "Please upload a valid .csv or .xlsx file.")
            return redirect("add_mass_movies")

        try:
            valid_ratings = {
                choice[0].upper() for choice in Movie._meta.get_field("rating").choices
            }
            valid_disks = {
                choice[0].lower() for choice in Movie._meta.get_field("disk").choices
            }

            rows = []
            if file_name.endswith(".csv"):
                raw_data = uploaded_file.read()
                # Try UTF-8 with BOM first (Excel on Windows), then UTF-8, then fallback to latin-1
                try:
                    decoded_file = raw_data.decode("utf-8-sig")
                except UnicodeDecodeError:
                    try:
                        decoded_file = raw_data.decode("utf-8")
                    except UnicodeDecodeError:
                        decoded_file = raw_data.decode("latin-1")
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                next(reader)  # Skip header row
                rows = list(reader)
            elif file_name.endswith(".xlsx"):
                workbook = load_workbook(uploaded_file)
                # Always use the first sheet
                sheet = workbook.worksheets[0]
                rows = list(sheet.iter_rows(min_row=2, values_only=True))

            count = 0
            for row in rows:
                if not row:
                    continue

                # Handle both formats: 3-column (title,rating,disk) or 5-column (title,rated,4k,blu-ray,dvd)
                if len(row) == 5:
                    # Excel format: Title, Rated, 4k, Blu-Ray, DVD
                    title = str(row[0]).strip() if row[0] else ""
                    rating = str(row[1]).strip() if row[1] else ""

                    # Check which disk format has an X
                    disk = None
                    if row[2] and str(row[2]).strip().upper() == "X":
                        disk = "4k"
                    elif row[3] and str(row[3]).strip().upper() == "X":
                        disk = "blu-ray"
                    elif row[4] and str(row[4]).strip().upper() == "X":
                        disk = "dvd"

                    if not disk:
                        messages.warning(request, f"Skipping row with no disk format marked: {title}")
                        continue

                elif len(row) == 3:
                    # CSV format: title, rating, disk
                    title, rating, disk = [str(item).strip() if item else "" for item in row]
                    disk = disk.lower()
                else:
                    messages.warning(request, f"Skipping invalid row (expected 3 or 5 columns): {row}")
                    continue

                if not title or not rating:
                    messages.warning(request, f"Skipping row with empty values: {row}")
                    continue

                rating = rating.upper()

                if Movie.objects.filter(title=title, rating=rating, disk=disk).exists():
                    messages.info(
                        request, f"Skipping duplicate movie: {title} ({rating}, {disk})"
                    )
                    continue

                if rating not in valid_ratings:
                    messages.warning(
                        request, f"Invalid rating '{rating}' in row: {row}"
                    )
                    continue

                if disk not in valid_disks:
                    messages.warning(
                        request, f"Invalid disk type '{disk}' in row: {row}"
                    )
                    continue

                Movie.objects.create(title=title, rating=rating, disk=disk)
                count += 1

            messages.success(request, f"Successfully added {count} movies.")
        except Exception as e:
            messages.error(request, f"Error processing file: {e}")

        return redirect("add_mass")

    return render(request, "moviedb/mass_add.html")
