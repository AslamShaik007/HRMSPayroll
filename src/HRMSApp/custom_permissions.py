import jwt
from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework.permissions import BasePermission


class IsHrAdminPermission(BasePermission):
    """
    Created-By: Padmaraju 
    Use-Case: Add Permission For One View Which is to show all other Permissions 
                It shows only to HR-Admin
    """
    
    def has_permission(self, request, view):
        return 'ADMIN' in request.user.employee_details.first().roles.values_list('name', flat=True) or 'CEO' in request.user.employee_details.first().roles.values_list('name', flat=True)
    

class ATSAddEmployeePermission(BasePermission):
    def has_permission(self, request, view):
        token = request.META.get("HTTP_AUTHORIZATION", " ").split(" ")[1]
        ats_key = request.headers.get('X-ATS-TOKEN',None)
        if token:
            token_data = jwt.decode(
                token, key=settings.SECRET_KEY, algorithms=["HS256"], verify=False
            )
            user = get_user_model().objects.get(id=token_data.get("user_pk", None))
            if user:
                return True
            return False
        elif ats_key == "ATS@123":
            return True
        return False