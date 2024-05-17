from core.models import AbstractModelManager, AbstractModelQuerySet


class EmployeeQueryset(AbstractModelQuerySet):
    """
    Employee Details QuerySet

    AJAY, 07.01.2023
    """

    ...


class EmployeeManager(AbstractModelManager):
    """
    Employee Manager

    AJAY, 07.01.2023
    """

    ...


EmployeeManager = EmployeeManager.from_queryset(EmployeeQueryset)


class EmployeeWorkDetailsQueryset(AbstractModelQuerySet):
    """
    Employee Work Details QuerySet

    AJAY, 10.01.2023
    """

    ...


class EmployeeWorkDetailsManager(AbstractModelManager):
    """
    Employee Work Details Manager

    AJAY, 07.01.2023
    """

    ...


EmployeeWorkDetailsManager = EmployeeWorkDetailsManager.from_queryset(
    EmployeeWorkDetailsQueryset
)


class EmployeeSalaryetailsQueryset(AbstractModelQuerySet):
    """
    Employee Salary Details QuerySet

    AJAY, 10.01.2023
    """

    ...


class EmployeeSalaryDetailsManager(AbstractModelManager):
    """
    Employee Salary Details Manager

    AJAY, 07.01.2023
    """

    ...


EmployeeSalaryDetailsManager = EmployeeSalaryDetailsManager.from_queryset(
    EmployeeSalaryetailsQueryset
)


class EmployeeWorkHistoryQueryset(AbstractModelQuerySet):
    """
    Employee Work History Details QuerySet

    AJAY, 10.01.2023
    """

    ...


class EmployeeWorkHistoryManager(AbstractModelManager):
    """
    Employee Work History Manager

    AJAY, 07.01.2023
    """

    ...


EmployeeWorkHistoryManager = EmployeeWorkHistoryManager.from_queryset(
    EmployeeWorkHistoryQueryset
)
