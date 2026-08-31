import re

import requests
from django.core.management.base import BaseCommand

from swccgdb.models import Card, CardText

LIGHT_URL = 'https://raw.githubusercontent.com/swccgpc/swccg-card-json/main/Light.json'
DARK_URL = 'https://raw.githubusercontent.com/swccgpc/swccg-card-json/main/Dark.json'
SETS_URL = 'https://raw.githubusercontent.com/swccgpc/swccg-card-json/main/sets.json'

SIDE_URLS = [('Light', LIGHT_URL, 'L'), ('Dark', DARK_URL, 'D')]

# These `front` fields become dedicated CardText columns; everything else goes into `stats`.
CORE_FIELDS = {'gametext', 'lore', 'imageUrl', 'deploy', 'destiny', 'power', 'ability', 'armor', 'forfeit', 'title', 'type'}


def strip_uniqueness(title):
    """Remove the leading uniqueness marker(s) (•, ••, •••) from a card title."""
    return re.sub(r'^•+', '', title or '').strip()


def normalize_set_name(name):
    """Normalize set name for comparison (mirrors import_cards.Command.normalize_set_name)."""
    normalized = (name or '').lower()
    normalized = normalized.replace('’', '').replace("'", '')
    normalized = normalized.replace('-', ' ').replace('  ', ' ')
    normalized = normalized.replace('twoplayer', 'two player')
    return normalized.strip()


class Command(BaseCommand):
    help = 'Import card game text/stats from swccg-card-json into CardText, matched against existing Card rows.'

    def add_arguments(self, parser):
        parser.add_argument('--write', action='store_true', help='Actually write to the DB (default is dry-run).')
        parser.add_argument('--limit-unmatched', type=int, default=25, help='Max unmatched examples to print.')

    def handle(self, *args, **options):
        dry_run = not options['write']
        unmatched_limit = options['limit_unmatched']

        self.stdout.write('Fetching sets.json...')
        sets_json = self.fetch_json(SETS_URL)
        id_to_set_name = {s['id']: s['name'] for s in sets_json}

        total_matched = 0
        total_written = 0
        total_unmatched = []

        for side_label, url, side_code in SIDE_URLS:
            self.stdout.write(f'Fetching {side_label}.json...')
            cards_json = self.fetch_json(url)['cards']
            index = self.build_index(cards_json, id_to_set_name)

            db_cards = Card.objects.filter(side=side_code).select_related('card_set')
            for card in db_cards:
                entry = self.find_entry(card, index)
                if entry is None:
                    total_unmatched.append((card.id, card.name, card.card_set.name))
                    continue

                front = entry.get('front', {})
                defaults = dict(
                    game_text=front.get('gametext') or '',
                    lore=front.get('lore') or '',
                    image_url=front.get('imageUrl') or '',
                    deploy_cost=front.get('deploy') or '',
                    destiny=front.get('destiny') or '',
                    power=front.get('power') or '',
                    ability=front.get('ability') or '',
                    armor=front.get('armor') or '',
                    forfeit=front.get('forfeit') or '',
                    stats={k: v for k, v in front.items() if k not in CORE_FIELDS and v not in (None, '', [])},
                )

                if dry_run:
                    self.stdout.write(f'MATCH  {card.name!r} ({card.card_set.name}) -> {len(defaults["game_text"])} chars gametext')
                else:
                    CardText.objects.update_or_create(card=card, defaults=defaults)
                    total_written += 1
                total_matched += 1

        self.stdout.write(self.style.SUCCESS(
            f'Matched {total_matched}, unmatched {len(total_unmatched)}, written {total_written}'
        ))
        if total_unmatched:
            self.stdout.write('Unmatched examples:')
            for row in total_unmatched[:unmatched_limit]:
                self.stdout.write(f'  {row}')
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — pass --write to actually save.'))

    def fetch_json(self, url):
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()

    def build_index(self, cards_json, id_to_set_name):
        """
        Build a lookup keyed by (stripped_title, normalized_set_name) -> card record.
        Indexes every printing's set, not just the primary one, so reprints still match.
        """
        index = {}
        for entry in cards_json:
            front = entry.get('front', {})
            title = strip_uniqueness(front.get('title', ''))

            set_ids = {entry.get('set')}
            for printing in entry.get('printings') or []:
                if printing.get('set'):
                    set_ids.add(printing['set'])

            for set_id in set_ids:
                set_name = id_to_set_name.get(set_id)
                if not set_name:
                    continue
                index[(title, normalize_set_name(set_name))] = entry
        return index

    def find_entry(self, card, index):
        stripped_name = strip_uniqueness(card.name)
        set_key = normalize_set_name(card.card_set.name)

        entry = index.get((stripped_name, set_key))
        if entry is not None:
            return entry

        # Fallback: unambiguous title-only match, to surface set-name mismatches during dry run.
        candidates = [e for (title, _set), e in index.items() if title == stripped_name]
        if len(candidates) == 1:
            return candidates[0]
        return None
