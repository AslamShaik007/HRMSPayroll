from core.models import AbstractModelManager, AbstractModelQuerySet


class ChoicesQuerySet(AbstractModelQuerySet):
    """
    Choices queryset

    AJAY, 31.01.2023
    """

    def default(self, request, *args, **kwargs):
        """
        TODO: Default choices for choice type
        """
        return self.filter(*args, **kwargs)

    def active(self, **kwargs):
        """
        Active choices
        """
        return self.filter(is_active=True, **kwargs)


class ChoicesModelManager(AbstractModelManager):
    """
    Model Manager for Choices.

    AJAY, 31.01.2023
    """

    pass


ChoicesManager = ChoicesModelManager.from_queryset(ChoicesQuerySet)
