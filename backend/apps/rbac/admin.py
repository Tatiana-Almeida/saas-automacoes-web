from django.contrib import admin

from .models import Permission, Role, UserPermission, UserRole


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "description")
    search_fields = ("code", "description")


class RolePermissionInline(admin.TabularInline):
    model = Role.permissions.through
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [RolePermissionInline]
    exclude = ("permissions",)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "tenant")
    list_filter = ("tenant", "role")
    search_fields = ("user__username", "role__name")


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ("user", "permission", "tenant")
    list_filter = ("tenant", "permission")
    search_fields = ("user__username", "permission__code")
