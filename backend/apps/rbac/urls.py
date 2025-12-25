from django.urls import path
from .views import (
    UserRoleAssignView,
    UserRoleListView,
    UserPermissionAssignView,
    UserPermissionRevokeView,
    UserPermissionListView,
    BulkRbacApplyView,
    RoleListCreateView,
    RoleDetailView,
    PermissionListCreateView,
    PermissionDetailView,
)

urlpatterns = [
    path(
        "rbac/users/<int:user_id>/roles",
        UserRoleListView.as_view(),
        name="rbac-user-roles",
    ),
    path(
        "rbac/users/<int:user_id>/roles/assign",
        UserRoleAssignView.as_view(),
        name="rbac-user-roles-assign",
    ),
    path(
        "rbac/users/<int:user_id>/permissions",
        UserPermissionListView.as_view(),
        name="rbac-user-perms",
    ),
    path(
        "rbac/users/<int:user_id>/permissions/assign",
        UserPermissionAssignView.as_view(),
        name="rbac-user-perms-assign",
    ),
    path(
        "rbac/users/<int:user_id>/permissions/revoke",
        UserPermissionRevokeView.as_view(),
        name="rbac-user-perms-revoke",
    ),
    path("rbac/bulk/apply", BulkRbacApplyView.as_view(), name="rbac-bulk-apply"),
    # Admin endpoints
    path("rbac/roles", RoleListCreateView.as_view(), name="rbac-roles"),
    path("rbac/roles/<int:role_id>", RoleDetailView.as_view(), name="rbac-role-detail"),
    path(
        "rbac/permissions", PermissionListCreateView.as_view(), name="rbac-permissions"
    ),
    path(
        "rbac/permissions/<int:perm_id>",
        PermissionDetailView.as_view(),
        name="rbac-permission-detail",
    ),
]
