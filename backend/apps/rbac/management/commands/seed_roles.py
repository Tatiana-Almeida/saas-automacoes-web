from apps.rbac.models import Permission, Role
from django.core.management.base import BaseCommand

DEFAULT_PERMS = [
    "manage_tenants",
    "view_audit_logs",
    "manage_users",
    "view_users",
    "send_whatsapp",
    "send_email",
    "send_sms",
    "execute_workflows",
    "ai_infer",
]

ROLE_PERMS = {
    "Admin": DEFAULT_PERMS,
    "Manager": ["manage_users", "view_users", "view_audit_logs", "execute_workflows"],
    "Operator": ["send_whatsapp", "send_email", "send_sms", "execute_workflows"],
    "Viewer": ["view_users", "view_audit_logs"],
}


class Command(BaseCommand):
    help = "Seed default roles and permissions"

    def handle(self, *args, **options):
        # Ensure permissions exist
        perm_objs = {}
        for code in DEFAULT_PERMS:
            perm, _ = Permission.objects.get_or_create(code=code)
            perm_objs[code] = perm
        # Create roles and assign
        for role_name, perm_codes in ROLE_PERMS.items():
            role, _ = Role.objects.get_or_create(name=role_name)
            role.permissions.set([perm_objs[c] for c in perm_codes])
        self.stdout.write(self.style.SUCCESS("Seeded roles and permissions"))
