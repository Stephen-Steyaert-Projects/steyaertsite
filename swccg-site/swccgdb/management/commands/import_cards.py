import html
import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from swccgdb.models import Card, Set


class Command(BaseCommand):
    help = 'Import cards from starwarsccg.org card list pages'

    SETS = [
        'Premiere',
        'A New Hope',
        'Hoth',
        'Dagobah',
        'Cloud City',
        "Jabba's Palace",
        'Special Edition',
        'Endor',
        'Death Star II',
        'Reflections II',
        'Tatooine',
        'Coruscant',
        'Reflections III',
        'Theed',
        'Premium',
    ]

    TYPE_MAPPING = {
        # Light Side Characters
        ('CHARACTER', 'Jedi Master'): 'jedi_master_character',
        ('CHARACTER', 'Rebel'): 'rebel_character',
        ('CHARACTER', 'Republic'): 'republic_character',
        # Shared Characters
        ('CHARACTER', 'Alien'): 'alien_character',
        ('CHARACTER', 'Droid'): 'droid_character',
        # Dark Side Characters
        ('CHARACTER', 'Dark Jedi Master'): 'dark_jedi_master_character',
        ('CHARACTER', 'Imperial'): 'imperial_character',
        ('CHARACTER', 'Sith'): 'sith_character',
        # Non-Character Types
        ("ADMIRAL'S ORDER", None): 'admirals_order',
        ('CREATURE', None): 'creature',
        ('DEFENSIVE SHIELD', None): 'defensive_shield',
        ('DEVICE', None): 'device',
        ('EFFECT', None): 'effect',
        ('EPIC EVENT', None): 'epic_event',
        ('OBJECTIVE', 'Game Aid'): 'game_aid',
        ('INTERRUPT', None): 'interrupt',
        ('JEDI TEST', 'Jedi Test'): 'jedi_test',
        ('LOCATION', None): 'location',
        ('OBJECTIVE', None): 'objective',
        ('PODRACER', 'Podracer'): 'podracer',
        ('STARSHIP', None): 'starship',
        ('VEHICLE', None): 'vehicle',
        ('WEAPON', None): 'weapon',
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--set',
            type=str,
            help='Specific set name to import (e.g., "A New Hope")',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Import all sets',
        )

    def handle(self, *args, **options):
        if options['all']:
            for set_name in self.SETS:
                self.import_set(set_name)
        elif options['set']:
            self.import_set(options['set'])
        else:
            self.stdout.write(self.style.ERROR('Please specify --set "Set Name" or --all'))

    def set_name_to_url(self, set_name):
        """Convert set name to URL format"""
        url_name = set_name.replace(' ', '').replace("'", '')
        # Replace III before II to avoid partial replacement
        url_name = url_name.replace('III', '3').replace('II', '2')
        return f'https://res.starwarsccg.org/cardlists/{url_name}Type.html'

    def parse_card_type(self, section_type, img_alt):
        """Map HTML card type to Django model choice"""
        # Handle dual types like "Alien/Rebel"
        if img_alt and '/' in img_alt:
            types = img_alt.split('/')
            primary_type = self.TYPE_MAPPING.get((section_type, types[0].strip()), None)
            secondary_type = self.TYPE_MAPPING.get((section_type, types[1].strip()), None)
            return primary_type, secondary_type

        # Single type
        card_type = self.TYPE_MAPPING.get((section_type, img_alt), None)
        if not card_type:
            card_type = self.TYPE_MAPPING.get((section_type, None), None)

        return card_type, None

    def normalize_set_name(self, name):
        """Normalize set name for comparison"""
        normalized = name.lower()
        normalized = normalized.replace("'", "").replace("'", "")
        normalized = normalized.replace("-", " ").replace("  ", " ")
        normalized = normalized.replace("twoplayer", "two player")
        normalized = normalized.strip()
        return normalized

    def find_or_create_set(self, set_name):
        """Find existing set or create new one using normalized name matching"""
        normalized_target = self.normalize_set_name(set_name)

        # Check all existing sets for a match
        for existing_set in Set.objects.all():
            if self.normalize_set_name(existing_set.name) == normalized_target:
                return existing_set, False

        # No match found, create new set
        new_set = Set.objects.create(name=set_name)
        return new_set, True

    def extract_set_from_url(self, url):
        """Extract set name from card URL (for Premium cards)"""
        # URL format: https://res.starwarsccg.org/cards/EnhancedPremiere-Light/large/...
        match = re.search(r'/cards/([^/]+)-(Light|Dark)/', url)
        if match:
            set_slug = match.group(1)
            # Convert from slug to readable name
            # EnhancedPremiere -> Enhanced Premiere
            # JediPack -> Jedi Pack
            readable = re.sub(r'([a-z])([A-Z])', r'\1 \2', set_slug)
            return readable
        return None

    def import_set(self, set_name):
        self.stdout.write(f'Importing set: {set_name}')

        # Fetch the HTML
        url = self.set_name_to_url(set_name)
        self.stdout.write(f'Fetching: {url}')

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Failed to fetch {url}: {e}'))
            return

        soup = BeautifulSoup(response.content, 'html.parser')

        # Parse both Light and Dark sides
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for side_name, side_code in [('Light', 'L'), ('Dark', 'D')]:
            cards_data = self.parse_cards(soup, side_name, set_name)

            for card_data in cards_data:
                # For Premium set, extract actual set from URL
                actual_set_name = card_data.pop('_extracted_set_name', set_name)

                # Find or create the set using normalized matching
                card_set, created = self.find_or_create_set(actual_set_name)
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created new set: {actual_set_name}'))

                card_data['card_set'] = card_set
                card_data['side'] = side_code

                # Check if card already exists
                existing = Card.objects.filter(
                    name=card_data['name'],
                    card_set=card_set,
                    side=side_code
                ).first()

                if existing:
                    # Update existing card
                    for key, value in card_data.items():
                        setattr(existing, key, value)
                    existing.save()
                    updated_count += 1
                else:
                    # Create new card
                    try:
                        Card.objects.create(**card_data)
                        created_count += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Skipped card {card_data["name"]}: {e}'))
                        skipped_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Completed {set_name}: {created_count} created, {updated_count} updated, {skipped_count} skipped'
        ))

    def parse_cards(self, soup, side_name, set_name):
        """Parse cards from HTML for a specific side"""
        cards = []
        current_section = None

        # Find all table rows
        rows = soup.find_all('tr')

        for row in rows:
            # Check if this is a section header (CHARACTER, DEVICE, etc.)
            type_cell = row.find('td', class_='type')
            if type_cell:
                current_section = type_cell.get_text(strip=True).upper()
                continue

            # Check if this row contains a card
            card_link = row.find('a', href=lambda x: x and f'-{side_name}/' in x if x else False)
            if not card_link:
                continue

            # Extract card data
            img = row.find('img')
            img_alt = img.get('alt') if img else None
            img_title = img.get('title') if img else None

            # For Premium set: infer section from image alt/title
            if not current_section and img_alt:
                # Map card type icons to section names
                if img_alt in ['Starship', 'Vehicle', 'Weapon', 'Device', 'Effect',
                              'Interrupt', 'Objective', 'Game Aid', "Admiral's Order",
                              'Defensive Shield', 'Epic Event', 'Creature', 'Podracer']:
                    current_section = img_alt.upper().replace("'", "'")
                elif img_alt in ['Rebel', 'Imperial', 'Alien', 'Droid', 'Jedi Master',
                                'Dark Jedi Master', 'Republic', 'Sith', 'Jedi Test']:
                    current_section = 'CHARACTER'
                elif img_alt in ['Site', 'System', 'Sector']:
                    current_section = 'LOCATION'

            if not current_section:
                continue

            # Get card name (decode HTML entities like &#8226;)
            card_name = html.unescape(card_link.get_text(strip=True))

            # Get rarity
            rarity_cell = row.find_all('td', class_='center')
            rarity = rarity_cell[-1].get_text(strip=True) if rarity_cell else ''

            # Parse card type
            card_type, secondary_card_type = self.parse_card_type(current_section, img_alt)

            if not card_type:
                self.stdout.write(self.style.WARNING(
                    f'Unknown type mapping: section={current_section}, img_alt={img_alt} for {card_name}'
                ))
                continue

            card_data = {
                'name': card_name,
                'card_type': card_type,
                'secondary_card_type': secondary_card_type,
                'rarity': rarity if rarity else '',
            }

            # For Premium set, extract actual set name from URL
            if set_name == 'Premium':
                card_url = card_link.get('href', '')
                extracted_set = self.extract_set_from_url(card_url)
                if extracted_set:
                    card_data['_extracted_set_name'] = extracted_set

            cards.append(card_data)

        return cards
