from django.conf import settings

from rest_framework.permissions import BasePermission

from directory.models import Employee


def is_whitelist(path):
    """
    The function checks if a given path is in a predefined whitelist of paths.

    :param path: The `path` parameter is a string representing the URL path of a request
    :return: The function `is_whitelist(path)` returns a boolean value (`True` or `False`). It returns
    `True` if the `path` parameter matches any of the paths in the `WHITELIST_PATH` list, and `False`
    otherwise.

    AJAY, 25.05.2023
    """
    WHITELIST_PATH = [
        "favicon.ico",
        "api/user/login/",
        "cental/",
        settings.ADMIN_URL_PATH,
    ]

    if settings.WHITELIST_PATH:
        WHITELIST_PATH.extend(settings.WHITELIST_PATH)

    if any(s in path for s in WHITELIST_PATH):
        return True

    return False


def is_file(path):
    """
    The function checks if a given file path has a valid file format from a predefined list of formats.

    :param path: The `path` parameter is a string representing the file path to be checked
    :return: The function `is_file` takes a `path` argument and returns a boolean value indicating
    whether the file extension of the path matches any of the file formats listed in the `FILE_FORMAT`
    list. If the file extension matches any of the formats, the function returns `True`, otherwise it
    returns `False`.

    AJAY, 25.05.2023
    """
    FILE_FORMAT = [
        ".js"
        ".css"
        ".jpg"
        ".png"
        ".ico"
        ".eot"
        ".svg"
        ".ttf"
        ".woff"
        ".woff2"
        ".otf"
        ".less"
        ".xml"
        ".scss"
    ]

    return any(path[-len(file_format) :] == file_format for file_format in FILE_FORMAT)


def is_model_excluded(model):
    """
    Function to exclude certain model to pass in uuid

    AJAY, 25.05.2023
    """
    EXCLUDED_MODELS = ["worklocations", "choices"]

    if model in EXCLUDED_MODELS:
        return True

    return False


class ActionBasedPermission(BasePermission):
    def has_permission(self, request, view):
        
        if '54.210.248.129' in request.get_host() or 'db_setup' in request.path:
            return True
        user = request.user
        # company_id = Employee.objects.filter(user=user).first().company.id
        employee_qs = Employee.objects.filter(user=user, work_details__employee_status="Active")
        
        if not employee_qs.exists():
            return False

        if is_whitelist(request.path) or is_file(request.path):
            return False

        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        permission_granted = False
        # TODO change after demo
        if '/payroll/' in request.path:
            return True
        action = request.method
        permission = ""
        if action in ("POST",):
            permission = "add_"
        elif action in ("PUT", "PATCH"):
            permission = "change_"
        elif action in ("DELETE",):
            permission = "delete_"
        elif action in ("GET", "retrieve"):
            permission = "view_"
        else:
            permission = "add_"

        permission_basename = ""
        if (
            hasattr(view, "serializer_class")
            and hasattr(view.serializer_class, "Meta")
            and hasattr(view.serializer_class.Meta, "model")
        ):
            permission_basename = view.serializer_class.Meta.model.__name__.lower()
        elif hasattr(view, "queryset") and hasattr(view.queryset, "model"):
            permission_basename = view.queryset.model.__name__.lower()
        elif hasattr(view, "model"):
            permission_basename = view.model.__name__.lower()

        if hasattr(view, "permission_basename") and view.permission_basename:
            permission_basename = view.permission_basename

        if not permission_basename:
            return False

        if is_model_excluded(permission_basename):
            return True

        permission += permission_basename

        roles = (
            employee_qs.prefetch_related("roles")
            .first()
            .roles.all()
        )
        if roles.prefetch_related(
            'rolemodulemapping', 'rolemodulemapping__permissions'
        ).filter(rolemodulemapping__permissions__codename=permission).exists():
            permission_granted = True
        
        return permission_granted
