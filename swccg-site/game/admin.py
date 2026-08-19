from django.contrib import admin

from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['code', 'created_by', 'player_two', 'created_at']
    search_fields = ['code', 'created_by__username', 'player_two__username']
