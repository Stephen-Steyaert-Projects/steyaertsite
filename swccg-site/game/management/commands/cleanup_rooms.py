from datetime import timedelta

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand
from django.utils import timezone

from game.models import Room
from game.state_store import get_store

GRACE_PERIOD = timedelta(hours=24)


class Command(BaseCommand):
    help = (
        'Deletes abandoned Room rows: no live match state left in the store '
        '(expired or never started) and older than the grace period. '
        'Most rooms clean themselves up via the "leave"/"close_room" actions; '
        'this is a fallback for rooms nobody ever explicitly left.'
    )

    def handle(self, *args, **options):
        store = get_store()
        cutoff = timezone.now() - GRACE_PERIOD
        deleted = 0

        for room in Room.objects.filter(created_at__lt=cutoff):
            state = async_to_sync(store.get)(room.code)
            if state is None:
                room.delete()
                deleted += 1

        self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} abandoned room(s).'))
