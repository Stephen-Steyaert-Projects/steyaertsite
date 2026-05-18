from django.core.management.base import BaseCommand
from swccgdb.models import Set, Card


class Command(BaseCommand):
    help = 'Merge duplicate sets, keeping the ones with images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Find potential duplicates (similar names)
        all_sets = Set.objects.all().order_by('name')

        # Group sets by normalized name
        set_groups = {}
        for s in all_sets:
            # Normalize name for comparison (case-insensitive, ignore punctuation differences)
            normalized = s.name.lower().replace("'", "").replace("'", "").strip()
            if normalized not in set_groups:
                set_groups[normalized] = []
            set_groups[normalized].append(s)

        # Find duplicates
        for normalized_name, sets in set_groups.items():
            if len(sets) > 1:
                self.stdout.write(self.style.WARNING(f'\nDuplicate sets found for "{normalized_name}":'))

                # Find the set with an image (to keep)
                keeper = None
                duplicates = []

                for s in sets:
                    card_count = s.cards.count()
                    has_image = bool(s.image)
                    self.stdout.write(f'  ID {s.id}: "{s.name}" - {card_count} cards, image={has_image}')

                    if has_image and not keeper:
                        keeper = s
                    elif not has_image:
                        duplicates.append(s)

                # If no set has an image, keep the one with most cards
                if not keeper and sets:
                    keeper = max(sets, key=lambda s: s.cards.count())
                    duplicates = [s for s in sets if s != keeper]
                    self.stdout.write(self.style.WARNING(f'  No image found, keeping set with most cards: "{keeper.name}"'))

                if keeper and duplicates:
                    self.stdout.write(self.style.SUCCESS(f'  Keeping: "{keeper.name}" (ID {keeper.id})'))

                    # Merge duplicates into keeper
                    for dup in duplicates:
                        card_count = dup.cards.count()
                        if card_count > 0:
                            if dry_run:
                                self.stdout.write(f'  [DRY RUN] Would move {card_count} cards from "{dup.name}" to "{keeper.name}"')
                            else:
                                # Move cards to keeper
                                dup.cards.all().update(card_set=keeper)
                                self.stdout.write(self.style.SUCCESS(f'  Moved {card_count} cards from "{dup.name}" to "{keeper.name}"'))

                        if dry_run:
                            self.stdout.write(f'  [DRY RUN] Would delete set: "{dup.name}" (ID {dup.id})')
                        else:
                            dup.delete()
                            self.stdout.write(self.style.SUCCESS(f'  Deleted set: "{dup.name}" (ID {dup.id})'))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. Use without --dry-run to actually merge sets.'))
        else:
            self.stdout.write(self.style.SUCCESS('\nDone!'))
