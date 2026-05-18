from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Clear all Django caches'

    def handle(self, *args, **options):
        cache.clear()
        self.stdout.write(self.style.SUCCESS('All caches cleared!'))
