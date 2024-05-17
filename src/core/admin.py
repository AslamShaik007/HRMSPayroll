import json

from django.contrib import admin
from django.utils.safestring import mark_safe

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import JsonLexer


# from django.apps import apps

# from django.contrib import admin

# admin model registrations
# models = apps.get_models()
# for model in models:
#     try:
#         admin.site.register(model)
#     except admin.sites.AlreadyRegistered:
#         ...


def prettify_json_field(data, dump_kwargs={}, formatter_kwargs={}):
    """
    Prettify the Data of a JSON Field and format it with pygments

    AJAY, 28.01.2023
    """
    # Convert the data to sorted, indented JSON
    dump_kwargs.setdefault("sort_keys", True)
    dump_kwargs.setdefault("indent", 4)
    response = json.dumps(data, **dump_kwargs)

    # Get the Pygments formatter
    formatter_kwargs.setdefault("style", "colorful")
    formatter_kwargs.setdefault("nowrap", False)
    formatter = HtmlFormatter(**formatter_kwargs)

    # Highlight the data
    response = highlight(response, JsonLexer(), formatter)

    # Get the stylesheet
    style = f"<style>{formatter.get_style_defs()}</style><br>"

    # Safe the output
    return mark_safe(style + response)


class AbstractModelAdmin(admin.ModelAdmin):
    """
    To be used in conjunction with Models using the AbstractModel from
    core.models

    AJAY, 02.01.2023
    """

    def get_list_display(self, request=None, include_all_fields=False):
        """
        Append additional fields to the self.list_display.

        AJAY, 02.01.2023
        """
        list_display = self.list_display

        if "id" not in list_display:
            list_display += ("id",)
        if "is_deleted" not in list_display:
            list_display += ("is_deleted",)
        if "created_at" not in list_display:
            list_display += ("created_at",)
        if "created_by" not in list_display:
            list_display += ("created_by",)
        if "updated_at" not in list_display:
            list_display += ("updated_at",)
        if "updated_by" not in list_display:
            list_display += ("updated_by",)

        if include_all_fields:
            return [field.name for field in self.model._meta.fields]

        return list_display

    def get_list_filter(self, request=None):
        """
        Append additional fields to the self.list_filter.

        AJAY, 02.01.2023
        """
        list_filter = self.list_filter
        if "is_deleted" not in list_filter:
            list_filter += ("is_deleted",)
        return list_filter
