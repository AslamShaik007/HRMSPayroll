from rest_framework.permissions import BasePermission


class IsCentralOrAuthenticated(BasePermission):
    """
    Created-By: Padmaraju 
    Use-Case: Added Permission if request coming from central
    """
    
    def has_permission(self, request, view):
        print(request.user, "Hiii")
        return request.user.is_authenticated or request.headers.get('X-CENTRAL') == 'raju@123'
