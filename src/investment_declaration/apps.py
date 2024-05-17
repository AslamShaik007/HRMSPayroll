from django.apps import AppConfig


class InvestmentDeclarationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "investment_declaration"
    def ready(self):
        import investment_declaration.signals  # noqa