from django.contrib import admin

from .models import Choices, ChoiceType


class ChoicesInline(admin.TabularInline):
    """
    Add inline for easy view.

    AJAY, 31.01.2023
    """

    model = Choices
    extra = 0
    raw_id_fields = ("choice_type", "parent")


@admin.register(ChoiceType)
class ChoiceTypeAdmin(admin.ModelAdmin):
    """
    Admin choice type.

    AJAY, 31.01.2023
    """

    list_display = ("name", "slug")
    list_filter = ("name",)
    search_fields = ("name", "slug")
    inlines = [
        ChoicesInline,
    ]


@admin.register(Choices)
class ChoicesAdmin(admin.ModelAdmin):
    """
    Admin choices.

    AJAY, 31.01.2023
    """

    list_display = ("key", "value", "choice_type", "is_active", "parent", "ordering")
    list_filter = ("choice_type__name", "choice_type")
    search_fields = ("key", "value", "choice_type__slug", "choice_type__name")

    raw_id_fields = ("parent",)
