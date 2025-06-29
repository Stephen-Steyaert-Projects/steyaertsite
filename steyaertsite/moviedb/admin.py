from django.contrib import admin
from .models import Movie


class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'rating', 'disk')
    search_fields = ('title',)
    list_filter = ('rating',)

admin.site.register(Movie, MovieAdmin)
