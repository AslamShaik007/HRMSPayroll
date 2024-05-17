from core.models import AbstractModelManager, AbstractModelQuerySet


class AttendanceRuleQueryset(AbstractModelQuerySet):
    """
    AttendanceRule Details QuerySet

    AJAY, 29.03.2023
    """

    ...


class AttendanceRuleManager(AbstractModelManager):
    """
    AttendanceRule Manager

    AJAY, 29.03.2023
    """

    ...


AttendanceRuleManager = AttendanceRuleManager.from_queryset(AttendanceRuleQueryset)
