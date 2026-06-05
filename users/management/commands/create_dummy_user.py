from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create a dummy user for testing (username: dummy_test, password: dummy1234!)"

    def handle(self, *args, **options):
        User = get_user_model()
        username = "dummy_test"
        password = "dummy1234!"
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists."))
            return
        # Create user and give staff access (so can login to admin)
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = True
        user.save()
        self.stdout.write(self.style.SUCCESS(
            f"✅ Dummy user created – username: '{username}', password: '{password}'"
        ))
