from django.contrib import admin
from .models import Card, Set


@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['card_set', 'card_type', 'side']
