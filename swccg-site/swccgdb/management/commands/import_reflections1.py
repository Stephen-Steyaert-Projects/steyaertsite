import re
import time
import urllib.request

from django.core.management.base import BaseCommand

from swccgdb.models import Card, Set


BASE_URL = "https://www.categoryonegames.com/catalog/star_wars_ccg-reflections_i/439?page={}&sort_by_price=0"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def scrape():
    cards = []
    for page in range(1, 6):
        req = urllib.request.Request(BASE_URL.format(page), headers=HEADERS)
        with urllib.request.urlopen(req) as r:
            html = r.read().decode("utf-8")

        # Extract (name, image_url) from each product block
        products = re.findall(
            r'<h4[^>]*itemprop="name"[^>]*title="([^"]+)".*?'
            r'<img src="([^"]+)"[^>]*alt="[^"]*"[^>]*itemprop="image"',
            html, re.DOTALL
        )
        for name, img_url in products:
            base_name = name.replace(" [Foil]", "").strip()
            # Use large image instead of medium
            img_url = img_url.replace("/medium/", "/large/")
            cards.append((base_name, img_url))

        if page < 5:
            time.sleep(1)

    # Deduplicate preserving order
    seen = set()
    unique = []
    for name, img in cards:
        if name not in seen:
            seen.add(name)
            unique.append((name, img))
    return unique


class Command(BaseCommand):
    help = "Add bullet (•) to Reflections I card names that are missing it"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        try:
            ref1 = Set.objects.get(name="Reflections I")
        except Set.DoesNotExist:
            self.stdout.write(self.style.ERROR('Set "Reflections I" not found in DB.'))
            return

        self.stdout.write("Scraping categoryonegames.com...")
        cards = scrape()
        self.stdout.write(f"Found {len(cards)} cards on site.\n")

        updated = 0
        already_bulleted = 0
        not_found = 0

        for name, img_url in cards:
            bulleted = f"•{name}"

            # Already has a bullet — nothing to do
            if Card.objects.filter(card_set=ref1, name=bulleted).exists():
                self.stdout.write(f"  SKIP  {bulleted} (already bulleted)")
                already_bulleted += 1
                continue

            # Find the non-bulleted version
            matches = Card.objects.filter(card_set=ref1, name=name)
            if not matches.exists():
                self.stdout.write(self.style.WARNING(f"  MISS  {name} — not found in Reflections I"))
                self.stdout.write(f"        img: {img_url}")
                not_found += 1
                continue

            for card in matches:
                self.stdout.write(self.style.SUCCESS(f"  {'[DRY] ' if dry_run else ''}UPDATE  {name} → {bulleted}"))
                self.stdout.write(f"        img: {img_url}")
                if not dry_run:
                    card.name = bulleted
                    card.save()
                updated += 1

        self.stdout.write(f"\nDone: {updated} updated, {already_bulleted} already bulleted, {not_found} not found.")
