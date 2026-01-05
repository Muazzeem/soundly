"""
Django management command to list all users.
Usage: python manage.py list_users
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'List all users in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Search for a specific email (partial match)',
            default=None
        )

    def handle(self, *args, **options):
        email_filter = options.get('email')
        
        if email_filter:
            users = User.objects.filter(email__icontains=email_filter)
            self.stdout.write(f'\nUsers matching "{email_filter}":\n')
        else:
            users = User.objects.all().order_by('email')
            self.stdout.write(f'\nAll users ({users.count()} total):\n')
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('No users found.'))
            return
        
        for user in users:
            status = "Active" if user.is_active else "Inactive"
            self.stdout.write(
                f"  • {user.email} - {user.display_name} ({status})"
            )
        
        self.stdout.write('')
