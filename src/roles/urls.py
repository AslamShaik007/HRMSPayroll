from django.urls import path

from .views import CustomPermissionsAPIView, EmployeeRoleAssign, MobileRolesDataFetch

urlpatterns = [
    path('permissions/', CustomPermissionsAPIView.as_view(), name='role_permissions'),
    path('assign/', EmployeeRoleAssign.as_view(), name='role_assign'),
    path('mobile/fetch/', MobileRolesDataFetch.as_view(), name='mobile_roles'),
]
