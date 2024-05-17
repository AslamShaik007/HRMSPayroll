from rest_framework.views import APIView
import traceback

from leave.models import LeavesHistory, EmployeeLeaveRuleRelation
from directory.models import EmployeeReportingManager

from HRMSApp.custom_permissions import IsHrAdminPermission
from django.db import models as db_models
from rest_framework.response import Response
from rest_framework import status
from core.utils import success_response, error_response, timezone_now
from attendance.models import AttendanceRuleSettings
from datetime import datetime
from core.utils import get_paycycle_dates
class AdminLeaveRequestsCountAPIViewV2(APIView):

    model = LeavesHistory
    
    def get_manager_employees(self,man_id):
        emp_id = man_id
        my_list = []
        tag = True
        while tag:
            query = EmployeeReportingManager.objects.filter(manager_id__in=emp_id,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False)
            if not query.exists():
                break
            my_list.extend(list(query.values_list('employee_id',flat=True)))
            emp_id = list(query.values_list('employee_id',flat=True))
        return my_list
    
    def get(self, request, *args, **kwargs):

        try:
            user_info = request.user.employee_details.first()
            company_id = user_info.company_id
            employee_id = user_info.id
            role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
            paycycle = AttendanceRuleSettings.objects.filter(company_id=company_id).first()
            psc_from_date =  paycycle.attendance_input_cycle_from
            psc_to_date   =  paycycle.attendance_input_cycle_to
            current_date = timezone_now()
            pay_cycle_from_date,pay_cycle_to_date,current_payout_date=get_paycycle_dates(current_date,psc_from_date,psc_to_date)
            q_filters = db_models.Q(status = 20,start_date__gte=pay_cycle_from_date,end_date__lte=pay_cycle_to_date,is_deleted = False)
            if role == "ADMIN":   
                q_filters &= db_models.Q(employee__company_id = company_id)
            if role == "MANAGER":
                # emps_list = EmployeeReportingManager.objects.filter(manager_id = employee_id).values_list('employee',flat=True)
                q_filters &= db_models.Q(employee_id__in = self.get_manager_employees([employee_id]))
            qs = self.model.objects.filter(q_filters).count()
            data = {'leave_requests_count':qs}
            return Response(
                    success_response(
                        data, "Successfully fetched Leave Records", 200
                    ),
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error AT: {traceback.format_exc()}', "Got error while logging records fetch", 400),
                status=status.HTTP_404_NOT_FOUND
            )