from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Seed default RBAC groups and permissions (admin, manager, viewer).'

    def handle(self, *args, **options):
        admin, _ = Group.objects.get_or_create(name='admin')
        manager, _ = Group.objects.get_or_create(name='manager')
        viewer, _ = Group.objects.get_or_create(name='viewer')

        # Admin gets all permissions
        admin.permissions.set(Permission.objects.all())
        admin.save()

        # Manager/viewer can be tailored later; keep minimal for now
        manager.permissions.clear()
        viewer.permissions.clear()

        self.stdout.write(self.style.SUCCESS('RBAC groups seeded: admin, manager, viewer'))
