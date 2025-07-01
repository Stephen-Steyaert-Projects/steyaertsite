from django import forms
from .models import Movie

RATINGS = [
    ("", "Rating..."),
    ("G", "G"),
    ("PG", "PG"),
    ("PG-13", "PG-13"),
    ("R", "R"),
    ("NR", "NR"),
    ("TV", "TV"),
]

DISKS = [
    ("", "Disk Type..."),
    ("4k", "4K Ultra HD"),
    ("Blu-Ray", "Blu-Ray"),
    ("DVD", "DVD"),
]


class AddMovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ["title", "rating", "disk"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Title", "class": "form-control"}
            ),
            "rating": forms.Select(attrs={"class": "form-select"}),
            "disk": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "title": "What is the new Movie's Title?",
            "rating": "What is the new Movie's Rating?",
            "disk": "What is the new Movie's Disk Type?",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rating"].choices = RATINGS
        self.fields["disk"].choices = DISKS

    def clean(self):
        cleaned_data = super().clean()
        rating = cleaned_data.get("rating")
        disk = cleaned_data.get("disk")

        if rating == "":
            self.add_error("rating", "Please choose a valid rating.")

        if disk == "":
            self.add_error("disk", "Please choose a valid disk type.")

        return cleaned_data


RATING_CHOICES = [
    ("G", "G"),
    ("PG", "PG"),
    ("PG-13", "PG-13"),
    ("R", "R"),
    ("NR", "NR"),
    ("TV", "TV"),
]

class RandomMovieForm(forms.Form):
    movies = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=1,
        label="How many movies?",
        widget=forms.NumberInput(attrs={"placeholder": "1-20"})
    )
    ratings = forms.MultipleChoiceField(
        choices=RATING_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Choose ratings",
    )

class CSVUploadForm(forms.Form):
    file = forms.FileField(label="Upload CSV File")