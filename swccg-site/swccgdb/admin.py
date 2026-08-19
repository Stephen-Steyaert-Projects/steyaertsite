from django.contrib import admin
from .models import Card, CardText, Set


@admin.register(Set)
class SetAdmin(admin.ModelAdmin):
    search_fields = ['name']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_filter = ['card_set', 'card_type', 'side']


@admin.register(CardText)
class CardTextAdmin(admin.ModelAdmin):
    search_fields = ['card__name']
    autocomplete_fields = ['card']
