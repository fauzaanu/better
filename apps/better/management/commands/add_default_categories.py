from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.better.models import ScoreDay, TargetCategory


class Command(BaseCommand):
    help = 'Add default categories to today\'s ScoreDay'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Date in YYYY-MM-DD format (defaults to today)',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Overwrite existing categories with same names',
        )
        parser.add_argument(
            '--update-all',
            action='store_true',
            help='Update descriptions for all existing categories across all days',
        )
        parser.add_argument(
            '--delete-empty',
            action='store_true',
            help='Delete categories that have no targets',
        )

    def handle(self, *args, **options):
        # Default categories with descriptions that guide users to add correct targets
        default_categories = [
            {
                'name': 'Finance',
                'description': 'Targets that help you add future pleasure through money or remove future pain from financial stress. Examples: increase income, reduce expenses, build savings, pay off debt.'
            },
            {
                'name': 'Health', 
                'description': 'Targets that help you add health or remove sickness and discomfort. Examples: exercise, eat nutritious meals, get medical checkups, practice mental wellness.'
            },
            {
                'name': 'Energy',
                'description': 'Targets that help you save time or remove effort from your day. Examples: optimize routines, eliminate time-wasters, automate tasks, improve productivity systems.'
            },
            {
                'name': 'Opinion',
                'description': 'Targets that help you add status in society or protect your reputation. Examples: build professional image, expand network, develop valued skills, manage public perception.'
            },
            {
                'name': 'Connection',
                'description': 'Targets that help you add meaningful relationships and connection or remove loneliness. Examples: strengthen relationships, make new connections, show care for others, build meaningful bonds.'
            },
            {
                'name': 'Safety',
                'description': 'Targets that help you add security and protection or remove risk and danger. Examples: ensure physical safety, build financial security, create emotional stability, get insurance.'
            },
            {
                'name': 'Knowledge',
                'description': 'Targets that help you expand understanding and capabilities. Examples: learn new skills, gain valuable information, solve problems, improve decision-making abilities.'
            }
        ]

        # Determine the target date
        if options['date']:
            try:
                from datetime import datetime
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            target_date = timezone.now().date()

        # Get or create ScoreDay for the target date
        score_day, created = ScoreDay.objects.get_or_create(
            day=target_date,
            defaults={'score': None, 'max_score': None}
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created new ScoreDay for {target_date}')
            )
        else:
            self.stdout.write(f'Using existing ScoreDay for {target_date}')

        # Handle update-all option first
        if options['update_all']:
            self.update_all_categories(default_categories)
            return

        # Handle delete-empty option
        if options['delete_empty']:
            deleted_count = self.delete_empty_categories(score_day)
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {deleted_count} empty categories')
            )

        # Add default categories
        categories_added = 0
        categories_updated = 0
        categories_skipped = 0

        for category_data in default_categories:
            try:
                category, category_created = TargetCategory.objects.get_or_create(
                    day=score_day,
                    name=category_data['name'],
                    defaults={
                        'description': category_data['description'],
                        'score': None,
                        'max_score': None
                    }
                )

                if category_created:
                    categories_added += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Added category: {category_data["name"]}')
                    )
                elif options['overwrite']:
                    category.description = category_data['description']
                    category.save()
                    categories_updated += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Updated category: {category_data["name"]}')
                    )
                else:
                    categories_skipped += 1
                    self.stdout.write(
                        self.style.WARNING(f'- Skipped existing category: {category_data["name"]}')
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error adding category {category_data["name"]}: {str(e)}')
                )

        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Categories added: {categories_added}')
        self.stdout.write(f'Categories updated: {categories_updated}')
        self.stdout.write(f'Categories skipped: {categories_skipped}')
        
        if categories_added > 0 or categories_updated > 0:
            # Recalculate scores for the day
            score_day.calculate_scores()
            self.stdout.write(
                self.style.SUCCESS(f'Recalculated scores for {target_date}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'\nDefault categories setup complete for {target_date}!')
        )

    def update_all_categories(self, default_categories):
        """Update descriptions for all existing categories across all days"""
        category_descriptions = {cat['name']: cat['description'] for cat in default_categories}
        
        updated_count = 0
        for category_name, description in category_descriptions.items():
            categories = TargetCategory.objects.filter(
                name=category_name,
                is_deleted=False
            )
            
            for category in categories:
                category.description = description
                category.save()
                updated_count += 1
        
        self.stdout.write('\n' + '='*50)
        self.stdout.write(f'Updated descriptions for {updated_count} categories across all days')
        self.stdout.write(
            self.style.SUCCESS('All category descriptions have been updated!')
        )

    def delete_empty_categories(self, score_day):
        """Delete categories that have no targets"""
        empty_categories = score_day.categories.filter(
            is_deleted=False,
            targets__isnull=True
        ).distinct()
        
        deleted_count = 0
        for category in empty_categories:
            self.stdout.write(f'Deleting empty category: {category.name}')
            category.delete()
            deleted_count += 1
        
        return deleted_count