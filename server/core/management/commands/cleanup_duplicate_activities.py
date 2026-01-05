"""
Django management command to clean up duplicate song exchange activities.
This removes duplicate activities for the same exchange, keeping only one per exchange.
"""
from django.core.management.base import BaseCommand
from core.models import Activity
from django.db.models import Count


class Command(BaseCommand):
    help = 'Remove duplicate song exchange activities, keeping only one per exchange'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Find all song exchange activities
        exchange_activities = Activity.objects.filter(
            activity_type='song_exchange'
        ).select_related('song_exchange')
        
        # Group by song_exchange and find duplicates
        exchange_counts = {}
        for activity in exchange_activities:
            if activity.song_exchange:
                exchange_id = str(activity.song_exchange.uid)
                if exchange_id not in exchange_counts:
                    exchange_counts[exchange_id] = []
                exchange_counts[exchange_id].append(activity)
        
        # Find exchanges with multiple activities
        duplicates = {k: v for k, v in exchange_counts.items() if len(v) > 1}
        
        if not duplicates:
            self.stdout.write(
                self.style.SUCCESS('No duplicate activities found.')
            )
            return
        
        self.stdout.write(
            self.style.WARNING(
                f'Found {len(duplicates)} exchanges with duplicate activities'
            )
        )
        
        total_to_delete = 0
        for exchange_id, activities in duplicates.items():
            # Keep the first (oldest) activity, delete the rest
            activities.sort(key=lambda x: x.created_at)
            to_keep = activities[0]
            to_delete = activities[1:]
            
            self.stdout.write(
                f'\nExchange {exchange_id}:'
            )
            self.stdout.write(
                f'  Keeping: Activity {to_keep.uid} (actor: {to_keep.actor.email}, created: {to_keep.created_at})'
            )
            for activity in to_delete:
                self.stdout.write(
                    f'  {"Would delete" if dry_run else "Deleting"}: Activity {activity.uid} (actor: {activity.actor.email}, created: {activity.created_at})'
                )
                if not dry_run:
                    activity.delete()
                total_to_delete += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\nDRY RUN: Would delete {total_to_delete} duplicate activities.'
                )
            )
            self.stdout.write('Run without --dry-run to actually delete them.')
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully deleted {total_to_delete} duplicate activities.'
                )
            )
