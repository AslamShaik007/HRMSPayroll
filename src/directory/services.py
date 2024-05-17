from typing import Optional

from .models import Employee, EmployeeReportingManager, ManagerType, SessionYear
from core.utils import timezone_now
from payroll.models import EmployeeComplianceNumbers

def get_manager(
    employee: Employee, manager_type: int = ManagerType.PRIMARY
) -> Optional[Employee]:
    """
    > Given an employee, return the employee's primary manager

    :param employee: The employee whose manager you want to get
    :type employee: Employee
    :param manager_type: This is an integer value that represents the type of manager. The default value
    is 1, which is the primary manager
    :type manager_type: int
    :return: Employee object

    AJAY, 30.03.2023
    """

    if employee is None:
        return None

    qs = EmployeeReportingManager.objects.filter(
        employee=employee, manager_type__manager_type=manager_type, is_deleted=False
    )

    if qs.exists():
        reporting_manager = qs.first()
        return reporting_manager.manager

def init_session_year(self="", company=""):
    if not company:
        return
    current_year = timezone_now().date().year
    SessionYear.objects.get_or_create(
        session_year = current_year,
    )
    
def init_employeecompliance_numbers(employee):
    """
    this function create pf, uan, esi,.. in model EmployeeComplianceNumbers
    whenever Employee is created
    """
    EmployeeComplianceNumbers.objects.create(
        employee_id=employee.id
    )