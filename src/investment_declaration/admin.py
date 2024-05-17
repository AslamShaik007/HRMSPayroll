from django.contrib import admin

from core.admin import AbstractModelAdmin
from investment_declaration import models


@admin.register(models.FormChoices)
class FormChoicesAdmin(AbstractModelAdmin):
    search_fields = ["formtype"]
    list_filter = ["formtype"]


@admin.register(models.SubFormChoices)
class SubFormChoicesAdmin(AbstractModelAdmin):
    search_fields = ["formtype"]
    list_filter = ["formtype"]


# class DeclarationFormsInline(admin.TabularInline):
#     """
#     Forms Inline

#     """

#     model = models.DeclarationForms
#     extra = 0
#     raw_id_fields = ("declaration",)


@admin.register(models.InvestmentDeclaration)
class InvestmentDeclarationAdmin(AbstractModelAdmin):
    search_fields = ("employee", "status")
    list_filter = ("employee", "status", "start_year", "end_year")

    # inlines = [DeclarationFormsInline]

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.DeclarationForms)
class DeclarationFormsAdmin(AbstractModelAdmin):
    search_fields = ("declaration",)
    list_filter = ("declaration", "parentform_type", "subform_type")

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)


@admin.register(models.Attachments)
class AttachmentsAdmin(AbstractModelAdmin):
    search_fields = ("declaration_form",)
    list_filter = ("declaration_form", "attachment",)

    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.get_list_display(include_all_fields=True)