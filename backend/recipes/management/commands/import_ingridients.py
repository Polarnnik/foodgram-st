import csv
import os
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Import ingredients from CSV file'

    def handle(self, *args, **options):
        file_path = Path(settings.BASE_DIR)/'..' / 'data' / 'ingredients.csv'

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f'❌ File not found: {file_path}'))
            return

        created_count = 0
        duplicates = 0

        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) < 2:
                    continue

                name = row[0].strip()
                unit = row[1].strip()

                _, created = Ingredient.objects.get_or_create(
                    name=name,
                    measurement_unit=unit
                )

                if created:
                    created_count += 1
                else:
                    duplicates += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅ Successfully imported ingredients: '
            f'{created_count} added, {duplicates} duplicates skipped'
        ))
