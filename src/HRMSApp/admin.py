from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.admin import AbstractModelAdmin, prettify_json_field

from .models import (
    AssignedModules,
    Attachment,
    CompanyDetails,
    Country,
    FutureModule,
    Modules,
    PhoneOTP,
    Registration,
    Roles,
    States,
    User,
)


@admin.register(User)
class UserAdmin(UserAdmin):
    """
    User view for django admin.

    AJAY, 2.1.2023
    """

    ...


@admin.register(Registration)
# class CompanyRegistrationsAdmin(UserAdmin):
class RegistrationAdmin(AbstractModelAdmin):
    """
    Registration view for django admin.

    AJAY, 26.12.2022
    """

    list_display = (
        "name",
        "email",
        "terms_and_conditions",
        "phone",
        "company",
        "company_size",
    )
    search_fields = (
        "name",
        "email",
        "company",
    )


@admin.register(CompanyDetails)
class CompanyDetailsAdmin(AbstractModelAdmin):
    """
    Company Details DJANGO Admin View

    AJAY, 26.12.2022
    """

    list_display = ("company_name", "brand_name", "domain_name", "created_at")
    search_fields = ("company_name",)
    list_filter = ("company_name",)


@admin.register(PhoneOTP)
class PhoneOTPAdmin(AbstractModelAdmin):
    """
    PhoneOTP Admin View

    AJAY, 26.12.2022
    """

    list_display = ("username", "phone", "email", "count", "validated")
    search_fields = ("username", "phone", "email")
    list_filter = ("phone", "email")


@admin.register(Roles)
class RoleAdmin(AbstractModelAdmin):
    """
    Role Admin View

    AJAY, 02.01.2023
    """

    list_display = ("name", "code", "slug", "is_active", "is_deleted", "description")
    search_fields = ("name", "code", "slug")
    list_filter = ("is_active", "permissions")
    filter_horizontal = ("permissions",)


@admin.register(Modules)
class ModuleAdmin(AbstractModelAdmin):
    """
    Modules Admin View

    AJAY, 02.01.2023
    """

    list_display = ("module_name",)
    search_fields = ("module_name",)
    list_filter = ("module_name",)


@admin.register(Country)
class CountryAdmin(AbstractModelAdmin):
    """
    Country Admin View

    AJAY, 02.01.2023
    """

    list_display = ("name", "calling_code")
    search_fields = ("name",)
    list_filter = ("name",)


@admin.register(States)
class StateAdmin(AbstractModelAdmin):
    """
    States Admin View

    AJAY, 02.01.2023
    """

    list_display = ("state_name", "country")
    search_fields = ("state_name", "country")
    list_filter = ("country__name",)


@admin.register(AssignedModules)
class AssignedModulesAdmin(AbstractModelAdmin):
    """
    Assigned Modules Admin View

    AJAY, 02.01.2023
    """

    list_display = ("registered_user", "module")
    search_fields = ("registered_user", "module")
    list_filter = ("registered_user", "module")


# @admin.register(FutureModule)
# class FutureModuleAdmin(AbstractModelAdmin):
#     """
#     Future Module Admin View

#     AJAY, 28.01.2023
#     """

#     def payload_pretty(self, instance):
#         return prettify_json_field(instance.payload)

#     # list_display = [field.name for field in FutureModule._meta.fields]
#     list_display = ["id", "effective_date", "status", "content_type", "logs"]
#     fields = [
#         "effective_date",
#         "status",
#         "content_type",
#         "logs",
#         "payload_pretty",
#         "serializer",
#     ]
#     list_filter = ("status",)
#     search_fields = ("effective_date",)
#     readonly_fields = ("payload_pretty",)


#####################
# Attachment Stuff
#####################


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    """
    Django admin display for Attachment.

    AJAY, 04.05.2023
    """

    search_fields = ("id", "object_id")
    list_display = (
        "id",
        # "content_type",
        "object_id",
        "title",
        "document",
        "created_at",
        # "content_object",
    )
    # list_filter = ("content_type",)
