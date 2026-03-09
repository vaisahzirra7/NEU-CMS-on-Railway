"""
Management command: create_superuser
=====================================
Place at: accounts/management/commands/create_superuser_env.py

Creates a superuser from environment variables on first deploy.
Safe to run multiple times — skips if user already exists.

Usage:
    python manage.py create_superuser_env
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decouple import config


class Command(BaseCommand):
    help = 'Create initial superuser from environment variables'

    def handle(self, *args, **options):
        User = get_user_model()

        email      = config('SUPERUSER_EMAIL',     default='')
        password   = config('SUPERUSER_PASSWORD',  default='')
        first_name = config('SUPERUSER_FIRSTNAME', default='Super')
        last_name  = config('SUPERUSER_LASTNAME',  default='Admin')

        if not email or not password:
            self.stderr.write(self.style.ERROR(
                'SUPERUSER_EMAIL and SUPERUSER_PASSWORD environment variables are required.'
            ))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(
                f'User {email} already exists — skipping.'
            ))
            return

        user = User.objects.create_superuser(
            email      = email,
            password   = password,
            first_name = first_name,
            last_name  = last_name,
        )
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])

        self.stdout.write(self.style.SUCCESS(
            f'Superuser {email} created successfully.'
        ))