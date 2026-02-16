from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsClientOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.client == request.user


class IsAssignedBiker(BasePermission):
    def has_object_permission(self, request, view, obj):
        return hasattr(request.user, "biker_profile") and \
               obj.assignment.biker.user == request.user
