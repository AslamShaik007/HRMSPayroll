import os
import datetime
import pandas as pd
import traceback

from django.conf import settings
from django.db import transaction
from django.db.models import F, FloatField, Q, Sum, Value
from django.db.models.functions import Coalesce, Concat
from django.db.models import Sum
from django.db import models as db_models

from rest_framework import permissions, serializers, status
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from uritemplate import partial

from core.views import (
    AbstractListAPIView,
    AbstractListCreateAPIView,
    AbstractRetrieveUpdateAPIView,
)
from core.utils import timezone_now, success_response, error_response, excel_converter, get_paycycle_dates
from directory.models import Employee, EmployeeWorkDetails, SessionYear
from leave.models import (
    EmployeeLeaveRuleRelation,
    EmployeeWorkRuleRelation,
    LeaveRules,
    LeavesHistory,
    WorkRuleChoices,
    WorkRules,
)
from leave.serializers import (
    EmpLeaveRuleRelationDetailSerializer,
    EmployeeGetWorkRuleRelationDetailSerializer,
    EmployeeLeaveRuleRelationSerializer,
    EmployeeWorkRuleBulkSerializer,
    EmployeeWorkRuleRelationDetailSerializer,
    EmployeeWorkRuleRelationSerializer,
    GetEmployeeLeaveRuleRelationDetailSerializer,
    LeaveRulesDetailSerializer,
    LeaveRulesSerializer,
    LeavesHistoryDetailSerializer,
    LeavesHistorySerializer,
    WorkRuleChoicesDetailSerializer,
    WorkRuleChoicesSerializer,
    WorkRulesDetailSerializer,
    WorkRulesSerializer,
)
from attendance.models import AttendanceRuleSettings
from HRMSProject.multitenant_setup import MultitenantSetup
class WorkRulesCreateView(AbstractListCreateAPIView):
    """
    View to create Company Work Rule
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkRulesSerializer
    queryset = WorkRules.objects.all()


class WorkRulesUpdateView(RetrieveUpdateAPIView):
    """
    View to Update Company Work Rule
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkRulesSerializer
    detail_serializer_class = WorkRulesDetailSerializer
    lookup_field = "id"
    queryset = WorkRules.objects.all()


class WorkRulesRetrieveView(ListAPIView):
    """
    View to retrieve compnay work rule
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkRulesDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = WorkRules.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class WorkRuleChoicesCreateView(AbstractListCreateAPIView):
    serializer_class = WorkRuleChoicesSerializer
    detail_serializer_class = WorkRuleChoicesDetailSerializer
    queryset = WorkRuleChoices.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class WorkRuleChoicesUpdateView(RetrieveUpdateAPIView):
    serializer_class = WorkRuleChoicesSerializer
    detail_serializer_class = WorkRuleChoicesDetailSerializer
    lookup_field = "id"
    queryset = WorkRuleChoices.objects.all()


class WorkRuleChoicesRetrieveView(ListAPIView):
    serializer_class = WorkRuleChoicesDetailSerializer
    lookup_field = "work_rule"
    lookup_url_kwarg = "work_rule_id"
    queryset = WorkRuleChoices.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class EmployeeWorkRuleRelationCreateView(AbstractListCreateAPIView):
    serializer_class = EmployeeWorkRuleRelationSerializer
    queryset = EmployeeWorkRuleRelation.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class EmployeeWorkRuleBulkAPIView(APIView):
    """
    View to Assign Employee Work rule
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeWorkRuleBulkSerializer
    detailed_serializer_class = EmployeeWorkRuleRelationDetailSerializer
    lookup_field = "company"
    model = EmployeeWorkRuleRelation

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.kwargs[self.lookup_field], is_deleted=False
        )

    def _perform_create(self, request, *args, **kwargs):
        """
        performs update or save
        :param request: The request object

        AJAY, 01.03.2023
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        if kwargs.pop("partial", False):
            serializer.update(None, validated_data=serializer.validated_data)
        else:
            serializer.save()

    def _retrieve(self, *args, **kwargs):
        """
        > The function retrieves all the objects in the database and returns them in a serialized format
        :return: The serializer.data is being returned.

        AJAY, 01.03.2023
        """

        serializer = self.detailed_serializer_class(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """
        AJAY, 01.03.2023
        """
        self._perform_create(request)
        return self._retrieve()

    def get(self, request, *args, **kwargs):
        """
        Retrieve Company's employee work rules

        AJAY, 01.03.2023
        """
        return self._retrieve()

    def patch(self, request, *args, **kwargs):
        """
        Override default patch method

        AJAY, 01.03.2023
        """
        self._perform_create(request, partial=partial)
        return self._retrieve()


class EmployeeWorkRuleRelationRetrieveView(AbstractListAPIView):
    """
    View to retrive employee workrule relations
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeWorkRuleRelationDetailSerializer
    lookup_field = "company_id"

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.kwargs[self.lookup_field], is_deleted=False
        )
        # qs = Employee.objects.filter(
        #     company=self.kwargs[self.lookup_field], is_deleted=False
        # )
        # if not qs.exists():
        #     qs = Employee.objects.filter(
        #         id=self.kwargs[self.lookup_field], is_deleted=False
        #     )
        # return qs


class EmpGetEmployeeWorkRuleRelationRetrieveView(AbstractListAPIView):
    """
    View to Retrive Employee Work_rule relation

    SURESH, 08.03.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    # serializer_class = EmployeeGetWorkRuleRelationSerializer
    serializer_class = EmployeeGetWorkRuleRelationDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeWorkRuleRelation.objects.all()

    def filter_queryset(self, queryset):
        today = timezone_now()
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
            "effective_date__lte" : today,
        }
        return queryset.filter(**filter_queryset)


class EmployeeWorkRuleRelationUpdateView(UpdateAPIView):
    serializer_class = EmployeeWorkRuleRelationSerializer
    lookup_field = "id"
    queryset = EmployeeWorkRuleRelation.objects.all()


class LeaveRulesCreateView(AbstractListCreateAPIView):
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeaveRulesSerializer
    detailed_serializer_class = LeaveRulesDetailSerializer
    queryset = LeaveRules.objects.all()


class LeaveRulesUpdateView(RetrieveUpdateAPIView):
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeaveRulesSerializer
    detailed_serializer_class = LeaveRulesDetailSerializer
    lookup_field = "id"
    queryset = LeaveRules.objects.all()
    
    def patch(self, request, *args, **kwargs):
        data = request.data
        if 'is_deleted' in data:
            obj = self.queryset.get(id=self.kwargs.get('id'))
            if obj.name in ["Loss Of Pay", "Comp Off", "Additional Leaves"]:
                return Response(
                    {"error": f"{obj.name} Cant be deleted"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        qs = self.queryset.filter(
            is_deleted=False, company_id=data.get('company'),
            name=data.get("name")
        ).exclude(id=self.kwargs.get('id'))
        if qs.exists():
            return Response(
                {"error": "Name With Leave rule already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().patch(request, *args, **kwargs)


class LeaveRulesRetrieveView(ListAPIView):
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeaveRulesDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = LeaveRules.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)

class LeaveRuleDeletion(APIView):
    model = LeavesHistory
    
    def get(self, request):
        params = request.query_params
        emp_id = params.get('emp_id')
        rule_id = params.get('rule_id')
        if not (rule_id or emp_id):
            return Response(
                {
                    "message": "Employee ID and Rule ID both were required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        data = self.model.objects.filter(employee_id=emp_id, leave_rule_id=rule_id, status=10)
        response = {
                'is_approved_leaves_present': data.exists(),
                'message': "Employee Dont have any approved leaves, You can delete.",
                
            }
        if data.exists():
            response['message'] = "Already leaves were approved in for this employee in this rule, Please deduct those leaves from other Rules."
            total_leaves_taken = data.aggregate(total_leaves_to_deduct=Sum('no_of_leaves_applied'))['total_leaves_to_deduct']
            lop_rule_ids = list(LeaveRules.objects.filter(name='Loss Of Pay', is_deleted=False).order_by('id').distinct('id').values_list('id', flat=True))
            lop_rule_ids.append(rule_id)
            assigned_rule_data = EmployeeLeaveRuleRelation.objects.exclude(
                    leave_rule_id__in=lop_rule_ids
                ).filter(employee_id=emp_id, remaining_leaves__gte=total_leaves_taken, is_deleted=False, leave_rule__is_deleted=False).select_related('leave_rule').values('leave_rule_id', 'leave_rule__name', 'remaining_leaves')
            if not assigned_rule_data.exists():
                response['message'] = f"{response['message']} \n Employee Used all leaves in other rules."
            response['existing_rules'] = assigned_rule_data
        return Response(
            response,
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        data = request.data
        approved_leave_data = LeavesHistory.objects.filter(
            employee_id=data.get('emp_id'), leave_rule_id=data.get('deleting_rule_id'), status=10
        )
        update_relation_qs = EmployeeLeaveRuleRelation.objects.filter(employee_id=data.get('emp_id'), leave_rule_id=data.get('assigning_rule_id'))
        if not update_relation_qs.exists():
            return Response(
                {
                    "message": "Employee Dont Have leave rule relation."
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        update_relation_obj = update_relation_qs.first()
        no_of_leaves = approved_leave_data.aggregate(total_leaves_to_deduct=Sum('no_of_leaves_applied'))['total_leaves_to_deduct']
        if no_of_leaves is None:
            no_of_leaves = 0.0
        # print(update_relation_obj.remaining_leaves, no_of_leaves)
        update_relation_obj.remaining_leaves = float(update_relation_obj.remaining_leaves) - float(no_of_leaves)
        if update_relation_obj.remaining_leaves < 0:
            return Response(
                {
                    "message": "Leaves were excceding the limt, please assign other leave rule"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        approved_leave_data.update(leave_rule_id=data.get('assigning_rule_id'))
        update_relation_obj.save()
        EmployeeLeaveRuleRelation.objects.get(employee_id=data.get('emp_id'), leave_rule_id=data.get('deleting_rule_id')).delete()
        return Response(
            {
                'message': 'Leave Rule deleted successfully'
            },
            status=status.HTTP_200_OK
        )

class EmployeeLeaveRulesCreationView(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployeeLeaveRuleRelationSerializer
    detailed_serializer_class = EmpLeaveRuleRelationDetailSerializer
    lookup_field = "company"
    model = EmployeeLeaveRuleRelation

    def get_queryset(self):
        return Employee.objects.filter(
            company=self.kwargs[self.lookup_field], is_deleted=False,
            work_details__employee_status='Active'
        )

    def _perform_create(self, request, *args, **kwargs):
        """
        performs update or save
        :param request: The request object

        AJAY, 25.02.2023
        """
        context = {"logged_in_user" : self.request.user.username,
                   "domain": f"{self.request.scheme}://{self.request.get_host()}/"}
        serializer = self.serializer_class(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        if kwargs.pop("partial", False):
            serializer.update(None, validated_data=serializer.validated_data)
        else:
            serializer.save()

    def _retrieve(self, *args, **kwargs):
        """
        > The function retrieves all the objects in the database and returns them in a serialized format
        :return: The serializer.data is being returned.

        AJAY, 25.02.2023
        """

        serializer = self.detailed_serializer_class(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def post(self, request, *args, **kwargs):
        """
        AJAY, 22.02.2023
        """
        self._perform_create(request)
        return self._retrieve()

    def get(self, request, *args, **kwargs):
        """
        Retrieve Company's employee leave rules

        AJAY, 22.02.2023
        """
        return self._retrieve()

    def patch(self, request, *args, **kwargs):
        """
        Override default patch method

        AJAY, 25.02.2023
        """
        self._perform_create(request, partial=partial)
        return self._retrieve()


class GetEmpLeavesView(AbstractListAPIView):
    serializer_class = GetEmployeeLeaveRuleRelationDetailSerializer
    filterset_fields = {
        "id": ["exact"],
        "employee": ["exact"],
        "leave_rule": ["in", "exact"],
    }
    queryset = EmployeeLeaveRuleRelation.objects.filter()


class LeavesHistoryCreateView(AbstractListCreateAPIView):
    """
    View to create Employee Leaves History

    SURESH, 23.02.2023
    AJAY, 03.03.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeavesHistorySerializer
    detailed_serializer_class = LeavesHistoryDetailSerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['domain'] = f"{self.request.scheme}://{self.request.get_host()}/"
        return context
    
    def get_queryset(self):
        return LeavesHistory.objects.filter(
            employee__id=self.request.data["employee"], is_deleted=False
        )


class LeavesHistoryUpdateView(AbstractRetrieveUpdateAPIView):
    """
    View to Update Employee Leaves History

    AJAY, 03.03.2023
    """

    serializer_class = LeavesHistorySerializer
    lookup_field = "id"
    queryset = LeavesHistory.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['domain'] = f"{self.request.scheme}://{self.request.get_host()}/"
        context['user_name'] = self.request.user.username
        return context
    
    def patch(self, request, *args, **kwargs):
        MultitenantSetup().create_to_connection(request)
        request.data["approver"] = request.user.email
        MultitenantSetup().go_to_old_connection(request)
        return super().patch(request, *args, **kwargs)
    
    
    
class ApproveLeaveMultitenant(AbstractListCreateAPIView):
    """
    View to Update Employee Leaves History

    AJAY, 03.03.2023
    """

    serializer_class = LeavesHistorySerializer
    lookup_field = "id"
    queryset = LeavesHistory.objects.all()
    
    def create(self, request, *args, **kwargs):
        instance_id  = request.query_params.get("history_id")
        if not instance_id:
            return Response(
                {
                    "status_code" :  400,
                    "message" : "history_id is required"
                },
                status=400
            )
        headers = request.headers
        if headers.get('X-CURRENT-COMPANY') == headers.get('X-SELECTED-COMPANY'):
            request.data["approver"] = request.user.email
        else:
            request.data["approver"] = request.data.get('approver')
        manager = Employee.objects.get(
            user__email = request.user.email
        )
        context = {
            "is_approved_by_tenant_manager" :  True,
            "multitenant_manager_id" : manager.id,
            "multitenant_manager_name" : manager.user.username,
            "multitenant_manager_email" : request.data.get('approver') 
        }
        MultitenantSetup().create_to_connection(request)
        from django.shortcuts import get_object_or_404 
        instance = get_object_or_404(LeavesHistory,**{"pk":instance_id})
        serializer = self.get_serializer(instance, data=request.data, partial=True, context = context)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            **context
        )
        data = serializer.data
        MultitenantSetup().go_to_old_connection(request)
        return Response(data)


class LeavesBulkApprovalView(AbstractListCreateAPIView):
    """
    Leave approval view

    AJAY, 12.04.2023
    """
    model = LeavesHistory
    serializer_class = LeavesHistorySerializer
    detail_serializer_class = LeavesHistoryDetailSerializer

    # @transaction.atomic()
    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            data["approver"] = request.user.email
            emps = data.pop("employee", [])
            leave_ids = data.pop("leave_ids", [])

            error = None

            if not leave_ids:
                error = {
                    "data": {
                        "errors": "please select atleast one employee",
                        "status": status.HTTP_200_OK,
                    }
                }
            histories = []
            # sid = transaction.savepoint()
            # print(1)
            for emp in leave_ids:
                history_qs = LeavesHistory.objects.filter(id=emp)
                for history in history_qs:
                    
                    if not history:
                        continue
                    serializer = self.serializer_class(instance=history)
                    serializer.validate(data.copy())
                    
                    if history.is_backdated == True:
                        histories.append(history.employee.user.username)
                    else:
                        history.status = data.get("status", LeavesHistory.PENDING)
                        # history.reason = data.get("reason", "")

                        serializer.update(instance=history, validated_data=data.copy())
                        # histories.append(history)
                        # The above code is printing the number 2.
                        # print(2)
                    # print(3, emp )
                # transaction.savepoint_commit(sid)
            if histories:
                return Response({
                            "status": status.HTTP_400_BAD_REQUEST,
                            "data": f"Bulk Leaves Approved, Following {histories} Employees have the Backdated Leaves, Hence not approved. Please Check"
                        })
            else:
                return Response({
                            "status": status.HTTP_200_OK,
                            "data": f"Bulk Leaves Approved Succefully"
                        })
                
            # return Response(
            #     data=self.detail_serializer_class(histories, many=True).data,
            #     status=status.HTTP_200_OK,
            # )
        except serializers.ValidationError as e:
            error = e.detail
        except Exception as e:
            # print("fsdg", e)
            # transaction.savepoint_rollback(sid)
            
            error = {
                "data": {
                    "errors": e,
                    "status": status.HTTP_400_BAD_REQUEST,
                }
            }

        if error:
            return Response(
                error,
                status=status.HTTP_400_BAD_REQUEST,
            )


class LeavesHistoryRetrieveView(AbstractListAPIView):
    """
    View to Retrive Employee Leaves History

    SURESH, 23.02.2023
    AJAY, 03.03.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeavesHistoryDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = LeavesHistory.objects.all().order_by("-id")

    def filter_queryset(self, queryset):
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_queryset)


class CompanyLeavesHistoryRetrieveView(AbstractListAPIView):
    """
    View to Retrive Employee Leaves History

    SURESH, 23.02.2023
    AJAY, 03.03.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = LeavesHistoryDetailSerializer
    lookup_field = "employee__company"
    lookup_url_kwarg = "company_id"
    queryset = LeavesHistory.objects.all().order_by("-id")

    def filter_queryset(self, queryset):
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        if 'department_id' in self.request.query_params:
            filter_queryset['employee__work_details__department_id__in'] = self.request.query_params['department_id'].split(',')
        if 'start_date' in self.request.query_params and 'end_date' in self.request.query_params:
            filter_queryset['start_date__gte'] = self.request.query_params['start_date']
            filter_queryset['end_date__lte'] = self.request.query_params['end_date']
        if 'status' in self.request.query_params:
            if self.request.query_params['status'] in ['10','20','30','40']:
                filter_queryset['status'] = self.request.query_params['status'] 
        return queryset.filter(**filter_queryset)


class EmployeeLeaveRuleRelationRetrieveView(AbstractListAPIView):
    """
    View to Retrive Employee Leaves History

    SURESH, 07.03.2023
    """

    serializer_class = GetEmployeeLeaveRuleRelationDetailSerializer
    lookup_field = "employee"
    lookup_url_kwarg = "employee_id"
    queryset = EmployeeLeaveRuleRelation.objects.all()

    def filter_queryset(self, queryset):
        filter_queryset = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
            "effective_date__lte": timezone_now().date()
        }
        return queryset.filter(**filter_queryset)


class MonthlyLeavesView(APIView):
    """
    View to extract applied emps monthly leaves data
    """

    http_method_names = ["post"]
    model = LeavesHistory

    def post(self, request, *args, **kwargs):
        #: month-year name emp-code dept designation totalleaves LOPleaves
        data = request.data
        result = {}
        try:
            objs = LeavesHistory.objects.filter(
                start_date__month=data.get("month", 0),
                start_date__year=data.get("year", 0),
                status=LeavesHistory.APPROVED,
                employee__company=data.get("company", 0),
            )
            result["data"] = list(
                objs.values("employee")
                .annotate(
                    name=Concat(
                        "employee__first_name",
                        Value(" "),
                        "employee__middle_name",
                        Value(" "),
                        "employee__last_name",
                        Value(" "),
                    ),
                    emp_code=Coalesce(
                        F("employee__work_details__employee_number"), Value("-")
                    ),
                    dept=Coalesce(
                        F("employee__work_details__department__name"), Value("-")
                    ),
                    designation=Coalesce(
                        F("employee__work_details__designation__name"), Value("-")
                    ),
                    total_leaves=Coalesce(
                        Sum("no_of_leaves_applied"), 0, output_field=FloatField()
                    ),
                    LOP_leaves=Coalesce(
                        Sum(
                            "no_of_leaves_applied",
                            filter=Q(leave_rule__name__iexact="Loss Of Pay"),
                        ),
                        0,
                        output_field=FloatField(),
                    ),
                )
                .order_by("employee")
            )
            result["status"] = status.HTTP_200_OK
        except Exception as e:
            result = {"error": str(e), "status": status.HTTP_400_BAD_REQUEST}

        return Response(
            data=result, status=result.get("status", status.HTTP_400_BAD_REQUEST)
        )

class EmployeeLeaveBalance(APIView):
    model = EmployeeLeaveRuleRelation
    
    def get_dates(self,current_year,current_month,psc_from_date,psc_to_date):
        next_month = current_month + 1
        if current_month == 1:
            previous_month = 12
            previous_year = current_year - 1
        else:
            previous_month = current_month - 1
            previous_year = current_year
        pay_cycle_from_date = datetime.datetime(previous_year, previous_month, psc_from_date).date()
        pay_cycle_to_date = datetime.datetime(current_year, current_month, psc_to_date).date()
        return [str(pay_cycle_from_date),str(pay_cycle_to_date)]
    
    def get(self, request, *args, **kwargs):
        if 'leave_rule_id' not in request.query_params:
            return Response(
                    error_response('Leave Rule is mandatory', 'Leave Rule is mandatory', 400),
                    status=status.HTTP_400_BAD_REQUEST
                )
        current_year = timezone_now().date().year
        leave_rule_id = request.query_params.get('leave_rule_id')
        company_id = request.user.employee_details.first().company_id
        employee_id = request.query_params.get('employee_id')  
          
        query_filter = db_models.Q(id=employee_id, company_id=company_id, 
                                   employeeleaverulerelation__leave_rule_id=leave_rule_id,
                                   employeeleaverulerelation__session_year__session_year=current_year
                                   )
        
        month_mapping = {
                            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
                        }
        
        att_sett_data = AttendanceRuleSettings.objects.filter(company_id = company_id)
        psc_from_date =  att_sett_data.first().attendance_input_cycle_from
        psc_to_date   =  att_sett_data.first().attendance_input_cycle_to

        my_df = pd.DataFrame(list(month_mapping.items()), columns=['month', 'month_name'])
        my_df['att_dates_range'] = my_df.apply(lambda obj: self.get_dates(current_year,obj['month'],psc_from_date,psc_to_date) ,axis=1)
        
        my_df['leaves_data'] = my_df.apply(lambda obj:
                        list(Employee.objects.filter(query_filter
                            ).annotate(
                                credited_leaves = db_models.Case(         
                                                            db_models.When(db_models.Q(
                                                                db_models.Q(employeeleaverulerelation__leave_rule__allow_backdated_leaves = True) &
                                                                ~db_models.Q(employeeleaverulerelation__employee__date_of_join__year = current_year)
                                                            ),
                                                                then='employeeleaverulerelation__earned_leaves'
                                                            ),
                                                            db_models.When(
                                                                employeeleaverulerelation__leave_rule__allow_backdated_leaves = True,
                                                                employeeleaverulerelation__employee__date_of_join__year = current_year,
                                                                employeeleaverulerelation__employee__date_of_join__month__lte = int(obj['month']),
                                                                then='employeeleaverulerelation__earned_leaves'
                                                            ),
                                                            db_models.When(
                                                                employeeleaverulerelation__leave_rule__allow_backdated_leaves = False,
                                                                employeeleaverulerelation__effective_date__month__lte=obj['month'],
                                                                employeeleaverulerelation__effective_date__year = current_year,
                                                                then='employeeleaverulerelation__earned_leaves'
                                                            ),
                                                            db_models.When(
                                                                employeeleaverulerelation__leave_rule__allow_backdated_leaves = False,
                                                                employeeleaverulerelation__effective_date__year__lt = current_year,
                                                                then='employeeleaverulerelation__earned_leaves'
                                                            ),
                                                            default=0,
                                                            output_field=db_models.DecimalField(),
                                                        ),
                                # applied_leaves = Sum('leaveshistory__no_of_leaves_applied', filter=db_models.Q(
                                #                         leaveshistory__status__in=[10],leaveshistory__leave_rule_id=leave_rule_id, 
                                #                         leaveshistory__is_penalty=False, leaveshistory__start_date__year = current_year,
                                #                         leaveshistory__start_date__range = obj['att_dates_range'])),
                                applied_leaves = db_models.Case(         
                                                            db_models.When(
                                                                employeeleaverulerelation__leave_rule__name__icontains = 'Comp Off',
                                                                then=Sum('leaveshistory__no_of_leaves_applied', filter=db_models.Q(
                                                                        leaveshistory__status__in=[10, 40, 20],leaveshistory__leave_rule_id=leave_rule_id, 
                                                                        leaveshistory__is_penalty=False, leaveshistory__start_date__year = current_year,
                                                                        leaveshistory__start_date__range = obj['att_dates_range']))
                                                                            ),
                                                            default=Sum('leaveshistory__no_of_leaves_applied', filter=db_models.Q(
                                                                        leaveshistory__status__in=[10,20],leaveshistory__leave_rule_id=leave_rule_id, 
                                                                        leaveshistory__is_penalty=False, leaveshistory__start_date__year = current_year,
                                                                        leaveshistory__start_date__range = obj['att_dates_range'])),
                                                            output_field=db_models.DecimalField(),
                                                        ),
                                penalty_deduction = Sum('leaveshistory__no_of_leaves_applied', filter=db_models.Q(
                                                        leaveshistory__status__in=[10, 20],leaveshistory__leave_rule_id=leave_rule_id, 
                                                        leaveshistory__is_penalty=True, leaveshistory__start_date__year = current_year,
                                                        leaveshistory__start_date__range = obj['att_dates_range'])),
                            ).annotate(
                                closing_balance = db_models.F('credited_leaves') - db_models.F('applied_leaves')
                            ).values('credited_leaves','applied_leaves','penalty_deduction','closing_balance')), axis=1)
        
        data = my_df.to_dict('records')
        for item in data:
            item['credited_leaves'] = item['leaves_data'][0].get('credited_leaves') if item['leaves_data'] else 0
            item['applied_leaves'] =item['leaves_data'][0].get('applied_leaves',0) if item['leaves_data'] else 0
            item['penalty_deduction'] =item['leaves_data'][0].get('penalty_deduction',0) if item['leaves_data'] else 0
            item['closing_balance'] =item['leaves_data'][0].get('closing_balance',0) if item['leaves_data'] else 0
            
        final_df = pd.DataFrame(data,columns=['credited_leaves','applied_leaves','penalty_deduction','closing_balance',
                                              'month','month_name','att_dates_range','leaves_data'])    
        df_removed = final_df.drop(['att_dates_range', 'leaves_data'], axis=1)
        df_removed.fillna(0,inplace=True)
        for i in range(1, len(df_removed)):
            if df_removed.at[i - 1, 'closing_balance'] != 0:
                df_removed.at[i, 'credited_leaves'] = df_removed.at[i - 1, 'closing_balance']
                df_removed.at[i, 'closing_balance'] = df_removed.at[i - 1, 'closing_balance'] - df_removed.at[i, 'applied_leaves'] - df_removed.at[i, 'penalty_deduction']
            elif df_removed.at[i - 1, 'closing_balance'] == 0 and df_removed.at[i - 1, 'applied_leaves'] != 0:
                df_removed.at[i, 'credited_leaves'] = 0
            elif df_removed.at[i - 1, 'closing_balance'] == 0 and df_removed.at[i - 1, 'applied_leaves'] == 0 and df_removed.at[i - 1, 'credited_leaves'] == 0:
                df_removed.at[i, 'credited_leaves'] = 0
        today = timezone_now().date() 
        a,b,c = get_paycycle_dates(today,psc_from_date,psc_to_date)
        psc_month = b.month
        psc_year = b.year
        if current_year == psc_year :
            for i in range(len(df_removed)):
                if df_removed.at[i, 'month'] > psc_month and df_removed.at[i, 'applied_leaves'] == 0:
                    df_removed.at[i, 'credited_leaves'] = 0
                    df_removed.at[i, 'closing_balance'] = 0
                if df_removed.at[i, 'closing_balance'] == 0:
                    df_removed.at[i, 'closing_balance'] = df_removed.at[i, 'credited_leaves']
            
               
        return Response(
            success_response(
                df_removed.to_dict('records'), "Successfully fetched Leave Rule Data", 200
            ),
            status=status.HTTP_200_OK
        )

class EmployeeLeaveBalanceImport(APIView):
    model = EmployeeLeaveRuleRelation
    
    def check_leave(self,used_so_far,earned_leaves):
        status = False
        try:
            status = int(earned_leaves) < int(used_so_far)
        except Exception as e:
            status = True
        return status 
    
    def check_leave_message(self,used_so_far,earned_leaves,message,l_type):
        msg = message
        try:
            msg = msg +','+f"Please provide correct {l_type} count" if int(earned_leaves) < int(used_so_far) else message
        except Exception as e:
            msg = msg +','+f"Please provide correct {l_type} count"
        return msg
    
    def check_gender(self,emp_id,status,mat=None,pat=None):
        st = status
        try:
            if emp_id:
                    employee_gender = Employee.objects.filter(id=emp_id).first().gender
                    if not employee_gender:
                        st=True
                    if mat and mat > 0  and employee_gender in ["MALE","TRANSGENDER"]:
                        st = True
                    if pat and pat > 0  and employee_gender in ["FEMALE","TRANSGENDER"]:
                        st = True
        except Exception as e:
            st = True
        return st
    
    def check_gender_message(self,emp_id,msg,mat=None,pat=None):
        message = msg
        try:
            if emp_id:
                    employee_gender = Employee.objects.filter(id=emp_id).first().gender
                    if not employee_gender:
                        message += ', Please Assign gender'
                    if mat and mat > 0  and employee_gender in ["MALE","TRANSGENDER"]:
                        message += ', He cant assign Maternity Leave'
                    if pat and pat > 0  and employee_gender in ["FEMALE","TRANSGENDER"]:
                        message += ', She cant assign Paternity Leave'
        except Exception as e:
            pass
            # message += ', Leaves count must not be Charaters'
        return message

    def leave_data(self,emp_id, leave_id, l_type):
        rec_dic = self.false_status_df.loc[self.false_status_df['emp_id'] == emp_id].to_dict('records')[0]
        # return f"{leave_id} - ({rec_dic[l_type + ' Applied']}/{rec_dic[l_type + ' Accrued']})"
        return f"{leave_id},{rec_dic[l_type + ' Applied']},{rec_dic[l_type + ' Accrued']}"

    def post(self, request, *args, **kwargs):
        try:
            company_id = request.user.employee_details.first().company.id
            file = self.request.FILES["leaves_data_file"]
            df = pd.read_excel(file,converters={'Session Year':str, 'Employee ID':str})
            df.fillna(0, inplace=True)
            if len(df) == 0:
                    return Response(
                        error_response('', 'File is empty', 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            required_columns = ['Employee ID','Employee Name','Session Year']
            company_leave_data = list(LeaveRules.objects.filter(company_id=company_id,is_deleted=False).values('id', 'name'))
            leave_names = [i['name'] for i in company_leave_data]
            
            for name in leave_names:
                required_columns.extend((name+' Applied', name+' Accrued')) 
            # if any(column not in df.columns for column in required_columns):
            if not all(column in df.columns for column in required_columns):
                return Response(
                        error_response('', 'please provide a correct file', 400),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            df['status'] = False
            df['message'] = ''
            
            # df.columns = df.columns.str.replace(' ', '_')
            df.status[df.loc[df['Employee ID'] == ""].index] = True
            df.message[df.loc[df["Employee ID"] == ""].index] = df.message[df.loc[df["Employee ID"] == ""].index] + "Employee ID is mandatory"
            
            df.status[df.loc[df['Session Year'] == ""].index] = True
            df.message[df.loc[df["Session Year"] == ""].index] = df.message[df.loc[df["Session Year"] == ""].index] +','+ "Session Year is mandatory"
            
            df['emp_id'] = df.apply(lambda obj:
                EmployeeWorkDetails.objects.filter(employee__company_id=company_id, employee_number = str(obj['Employee ID']).strip()).first().employee_id 
                if obj['Employee ID'] and EmployeeWorkDetails.objects.filter(employee__company_id=company_id,employee_number = str(obj['Employee ID']).strip()).exists() else '',axis=1)
            
            df.status[df.loc[df['emp_id'] == ""].index] = True
            df.message[df.loc[df["emp_id"] == ""].index] = df.message[df.loc[df["emp_id"] == ""].index] +','+ "Please provide correct Employee Id"
            
            # df['status'] = df.apply(lambda obj:(True if obj['Maternity Leave Accrued'] or obj['Paternity Leave Accrued'] else obj['status']) if not obj['status'] else obj['status'], axis=1)
            # df['message'] = df.apply(lambda obj:(obj['message']+', Please Assign gender' if obj['Maternity Leave Accrued'] or obj['Paternity Leave Accrued'] else obj['message']) if not obj['message'] else obj['message'], axis=1)
            
            df['session_year_id'] = df.apply(lambda obj:
                SessionYear.objects.filter(session_year = str(obj['Session Year']).strip()).first().id 
                if SessionYear.objects.filter(session_year = str(obj['Session Year']).strip()).exists() else '',axis=1)
            
            df.status[df.loc[df['session_year_id'] == ""].index] = True
            df.message[df.loc[df["session_year_id"] == ""].index] = df.message[df.loc[df["session_year_id"] == ""].index] +','+ "Please provide correct Session Year"
            if 'Maternity Leave Accrued' in df.columns:
                df['status'] = df.apply(lambda obj :self.check_gender(obj['emp_id'],obj['status'],mat=obj['Maternity Leave Accrued']) 
                                        if obj['Maternity Leave Applied'] else obj['status'],axis=1)

                df['message'] = df.apply(lambda obj :self.check_gender_message(obj['emp_id'],obj['message'],mat=obj['Maternity Leave Accrued']) 
                                        if obj['Maternity Leave Applied'] else obj['message'],axis=1)
            if 'Paternity Leave Accrued' in df.columns: 
                df['status'] = df.apply(lambda obj :self.check_gender(obj['emp_id'], obj['status'], pat=obj['Paternity Leave Accrued']) 
                                        if obj['Paternity Leave Applied'] else obj['status'],axis=1)

                df['message'] = df.apply(lambda obj :self.check_gender_message(obj['emp_id'], obj['message'], pat=obj['Paternity Leave Applied']) 
                                        if obj['Paternity Leave Applied'] else obj['message'],axis=1)

            for leave_type in leave_names:
                applied_col = f'{leave_type} Applied'
                accrued_col = f'{leave_type} Accrued'
                if (applied_col and accrued_col) in df.columns:
                    df['status'] = df.apply(lambda obj : self.check_leave(obj[applied_col],obj[accrued_col]) if not obj['status'] else obj['status'],axis=1)
                    df['message'] = df.apply(lambda obj : self.check_leave_message(obj[applied_col],obj[accrued_col],obj['message'],leave_type),axis=1)
                  
            true_status_df = df[df['status'] == True]
            self.false_status_df = df[df['status'] == False]
            
            if len(self.false_status_df) == 0:
                df_removed = true_status_df.drop(['session_year_id', 'emp_id'], axis=1)
                file_name = "failed records.xlsx"
                return excel_converter(df_removed,file_name)
            
            for dd in company_leave_data:
                self.false_status_df[dd['name']] = self.false_status_df.apply(lambda obj: self.leave_data(obj['emp_id'], dd['id'], dd['name']), axis=1)
                  
            self.false_status_df.apply(lambda obj: list(
                                                (EmployeeLeaveRuleRelation.objects.filter(
                                                                employee__company_id=company_id,employee_id = obj['emp_id'],
                                                                leave_rule_id = int(obj[leave_name].split(',')[0]),
                                                                session_year_id = obj['session_year_id']
                                                            ).update(
                                                                    remaining_leaves = float(obj[leave_name].split(',')[2]) - float(obj[leave_name].split(',')[1]),
                                                                    earned_leaves = float(obj[leave_name].split(',')[2]),
                                                                    used_so_far = float(obj[leave_name].split(',')[1]))
                                                if EmployeeLeaveRuleRelation.objects.filter(
                                                                                            employee__company_id=company_id,
                                                                                            employee_id = obj['emp_id'],
                                                                                            leave_rule_id = int(obj[leave_name].split(',')[0]),
                                                                                            session_year_id = obj['session_year_id']
                                                                                            ).exists()  
                                                else EmployeeLeaveRuleRelation.objects.create(employee_id = obj['emp_id'],
                                                                                                leave_rule_id = int(obj[leave_name].split(',')[0]),
                                                                                                session_year_id = obj['session_year_id'],
                                                                                                remaining_leaves = float(obj[leave_name].split(',')[2]) - float(obj[leave_name].split(',')[1]),
                                                                                                earned_leaves = float(obj[leave_name].split(',')[2]),
                                                                                                used_so_far = float(obj[leave_name].split(',')[1])))
                                                if float(obj[leave_name].split(',')[2]) > 0 else ''
                                                for leave_name in leave_names) ,axis=1)
               
            if len(true_status_df) != 0:
                df_removed = true_status_df.drop(['session_year_id', 'emp_id'], axis=1)
                file_name = "failed records.xlsx"
                return excel_converter(df_removed,file_name)

            return Response(
                status=status.HTTP_201_CREATED,
                data={
                    "status": status.HTTP_201_CREATED,
                    "message": "Leave Balance data created successfully",
                    "data": [],
                },
            )
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
            

class EmployeeLeaveBalanceImportFile(APIView):
    model = LeaveRules
    
    def get(self, request, *args, **kwargs):
        try:
            new_columns = ['Session Year']
            company_id = request.user.employee_details.first().company_id
            emp_ids = request.query_params.get('employee_ids').split(',')
            empls = Employee.objects.filter(id__in=emp_ids, company_id=company_id).values('work_details__employee_number','user__username')
            leave_names = LeaveRules.objects.filter(company_id=company_id, is_deleted=False).values_list('name',flat=True)
            
            for name in leave_names:
                new_columns.extend((name+' Applied', name+' Accrued'))

            emp_df = pd.DataFrame(empls,columns=['work_details__employee_number','user__username'])  
            emp_df = emp_df.rename(columns={'work_details__employee_number':'Employee ID', 'user__username':'Employee Name'}) 
            df = pd.DataFrame(columns=new_columns)
            emp_df.reset_index(drop=True, inplace=True)
            df.reset_index(drop=True, inplace=True)
            result = pd.concat([emp_df, df], axis=1)
            result['Session Year'] = timezone_now().date().year
            file_name = "import_file_leave_balance.xlsx"
            return excel_converter(result,file_name)
        except Exception as e:
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing Went wrong", 400),
                status=status.HTTP_400_BAD_REQUEST
            )
            

        
        
