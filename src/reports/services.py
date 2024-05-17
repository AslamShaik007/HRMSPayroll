import os
import traceback
from typing import List

from django.conf import settings
from django.contrib.contenttypes.models import ContentType

import pandas as pd

from core.utils import generate_random_string
from directory.models import (
    Employee,
    EmployeeEmergencyContact,
    EmployeeReportingManager,
)
from reports.exporter import export_excel
from reports.models import Report
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models as db_models

class EmployeeExporter:
    def __init__(self, *args, **kwargs) -> None:
        self.standard_fields = {}
        self.filename = f"employee_report_{generate_random_string()}.xlsx"
        self.file = os.path.join(settings.MEDIA_ROOT, self.filename)
        self.fields = [
            "Employee ID",
            "Employee Name",
            "Department",
            "Designation",
            "Reporting Manager",
            "Secondary Managers",
            "Job Title",
            "DOJ",
            "Work Location",
            "Employee Status",
            "Employee Type",
            "Probation Period",
            "Grade",
            "Contact Number",
            "Official Email ID",
            "Personal Email ID",
            "Emergency Contact Name",
            "Emergency Contact Number",
            "CTC"
        ]

    def generate(self, fields: dict = None, ids: List[int] = None):
        """
        It takes a list of employee ids, fetches the employees, and then creates a report with the
        employee details

        :param fields: A dictionary of fields to be included in the report
        :type fields: dict
        :param ids: List of ids of the objects to be exported
        :type ids: List[int]

        AJAY, 01.02.2023
        """

        employees = Employee.objects.filter(id__in=ids)
        report = Report(
            name="Employee Report",
            status=Report.PENDING,
            # content_type=ContentType.objects.get_for_model(Employee),
        )
        employee_query = employees.annotate(
                    attendance_rules = db_models.F('assignedattendancerules__attendance_rule__name'),
                    workweek_rule=db_models.F('employeeworkrulerelation__work_rule__name'),
                    leave_rules = ArrayAgg(db_models.F('employeeleaverulerelation__leave_rule__name'), distinct=True)
                    ).values('attendance_rules','workweek_rule','leave_rules','work_details__employee_number')
        
        employee_df = pd.DataFrame(employee_query,columns=['attendance_rules','workweek_rule','leave_rules','work_details__employee_number'])
        employee_df = employee_df.rename(columns={'work_details__employee_number':'Employee ID'})
        
        rows = []
        for employee in employees:
            try:
                managers = (
                    EmployeeReportingManager.objects.filter(
                        employee=employee, is_deleted=False
                    )
                    .select_related("manager_type", "manager")
                    .order_by("-manager_type")
                )
                primary_manager = (
                    managers[0].manager.name if managers.count() >= 1 else " "
                )
                second_manager = (
                    managers[1].manager.name if managers.count() >= 2 else " "
                )
                emergency_contact = EmployeeEmergencyContact.objects.filter(
                    employee=employee, is_deleted=False
                ).first()

                ctc = ''
                
                try:
                    ctc = employee.salary_details.ctc if employee.salary_details.exists() else " "
                except Exception as e:
                    pass

                rows.append(
                    (
                        getattr(employee.work_details if employee.work_details else " ", "employee_number"),
                        employee.name,
                        getattr(employee.work_details.department if employee.work_details else " ", "name", "-"),
                        getattr(employee.work_details.designation if employee.work_details else " ", "name", "-"),
                        primary_manager,
                        second_manager,
                        getattr(employee.work_details if employee.work_details else " ", "job_title"),
                        str(employee.date_of_join),
                        getattr(employee.work_details if employee.work_details else " ", "work_location"),
                        getattr(employee.work_details if employee.work_details else " ", "employee_status"),
                        # getattr(
                        #     employee.work_details.employee_type if employee.work_details else " ",
                        #     "get_employee_type_display()",
                        #     "-",
                        # ),
                        employee.work_details.employee_type.slug if employee.work_details.employee_type else '',
                        getattr(employee.work_details if employee.work_details else " ", "probation_period"),
                        getattr(employee.work_details.employee_grade if employee.work_details else " ", "grade", "-"),
                        employee.phone or "",
                        employee.official_email or "",
                        employee.personal_email or "",
                        emergency_contact.name if emergency_contact else "",
                        emergency_contact.phone_number if emergency_contact else "",
                        # employee.salary_details.ctc if employee.salary_details else " ",
                        ctc
                    )
                )
            except Exception:
                report.notes = traceback.format_exc()
                report.status = Report.ERROR
            df = pd.DataFrame(rows, columns=self.fields)
            df = df.merge(employee_df, on='Employee ID', how='left')
            export_excel(df, file=self.file)
        #     report.file = self.filename
        #     report.status = Report.SUCCESS
        # report.save()
        return df
