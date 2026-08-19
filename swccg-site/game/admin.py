from django.contrib import admin

from .models import GameDeck, Room


@admin.register(GameDeck)
class GameDeckAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'side', 'created_at']
    search_fields = ['name', 'user__username']
    list_filter = ['side']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['code', 'created_by', 'player_two', 'created_at']
    search_fields = ['code', 'created_by__username', 'player_two__username']
