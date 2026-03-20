from rest_framework.permissions import BasePermission


class IsGuest(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "guest"


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "owner"


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsOwnerOfProperty(BasePermission):
    """Verifies the requesting owner owns the property referenced in the request."""

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or request.user.role != "owner":
            return False
        # Works with Property instances directly or objects with a .property FK
        prop = obj if hasattr(obj, "owner_id") and not hasattr(obj, "property_id") else getattr(obj, "property", None)
        if prop is None:
            return False
        return prop.owner_id == request.user.id
