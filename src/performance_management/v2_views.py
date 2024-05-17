import traceback
from performance_management.models import AppraisalSetName,AppraisalSetQuestions, AppraisalSendForm,NotificationDates,AppraisalFormSubmit

from directory.models import Employee, EmployeeWorkDetails,EmployeeReportingManager
from company_profile.models import Departments
from django.db.models import Q, F, Value, CharField, OuterRef, Subquery, Count, Func, JSONField
from django.db.models.functions import Concat
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models as db_models


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.custom_paginations import CustomPagePagination

from django.conf import settings
from core.utils import (
    timezone_now,
    error_response,
    success_response,
    search_filter_decode
)


class AppraisalSetNameRetriveAPIViewV2(APIView):
    """
    Set Name And Question Retrive
    By Company Id
    """
    model = AppraisalSetName
    pagination_class = CustomPagePagination

    def get(self, request, *args,**kwargs):
        company_id = kwargs.get('company_id')
        q_filter = db_models.Q(company_id = company_id, is_deleted = False)

        qs = AppraisalSetName.objects.filter(q_filter, setname_questions__is_deleted = False).select_related(
            'setname_questions',
            'author'
        ).annotate(
            no_of_questions=Count('setname_questions', filter=Q(q_filter) & Q(setname_questions__is_deleted=False), distinct=True),
            authorName=F('author__user__username'),
            setName=F('id'),
            creationDate=F('created_at'),
            questions=ArrayAgg(Func(
                    Value('id'), 'setname_questions__id',
                    Value('setName'), 'id',
                    Value('isActive'), 'setname_questions__is_active',
                    Value('creationDate'), 'setname_questions__creation_date',
                    Value('questions'), 'setname_questions__questions',
                    Value('isDeleted'), 'is_deleted',
                    function='jsonb_build_object',
                    output_field=JSONField()
                ),distinct=True),
            is_editable = db_models.Case(
                                db_models.When(setnumber_id__set_id = db_models.F('id'), then = False),
                                default = Value(True), output_field=db_models.BooleanField()),
        ).values(
            'id','company','name','author','authorName','set_number','no_of_questions',
            'is_active','creationDate','questions','is_deleted','is_editable'
        ).order_by('-id')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "successfully fetched data"),
            status=status.HTTP_200_OK
            )


class RetriveAllDepartmentsV2(APIView):
    """
    Retriving All Departments Names APIView
    By Company Id
    """
    model = Departments

    def get(self, request, *args, **kwargs):
        company_id = kwargs.get('company_id')
        q_filter = db_models.Q(company_id = company_id)
        get_all =  Departments.objects.filter(q_filter).values('name')
        return Response(
            success_response(get_all, "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class SendFormDepartmentListAPIViewV2(APIView):
    """
    Retriving Employee Name And Official Email APIView
    By Company Id And Department Id
    """
    model = AppraisalSendForm
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        month=timezone_now().date().month
        year=timezone_now().date().year
        param = request.query_params
        department_id = kwargs.get('department_id')
        q_filter = db_models.Q(department__id = department_id, employee__company__id = param.get('company_id'),employee_status = 'Active')
        q_filter &= ~db_models.Q(employee__id=request.user.id)
        form = AppraisalSendForm.objects.filter(employee__work_details__department = department_id, employee__company__id = param.get('company_id'),
                                                creation_date__month=month, creation_date__year=year).values_list('employee', flat=True)
        
        dept = EmployeeWorkDetails.objects.filter(q_filter).select_related('employee').exclude(employee_id__in = form).annotate(
            emp_id = F('employee__id'),
            employee_name = F('employee__user__username'),
            employee_official_email = F('employee__official_email')
        ).values(
                'emp_id','department__id','employee_name','employee_official_email'
            ).exclude(employee__roles__name__in  = ['CEO'])
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(dept, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class SendFormListAPIViewV2(APIView):
    """
    Send Form Retrive APIView
    By Company Id
    Send Form Retrive Of Send Mail's To Employees
    """
    model = AppraisalSendForm
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = kwargs.get('company_id')
        q_filter = db_models.Q(employee__company_id = company_id)
        if "search_filter" in params:
                q_filter &= (
                    db_models.Q(employee__user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
                )
        data = AppraisalSendForm.objects.filter(q_filter).select_related(
            'employee','employee__work_details','employee__work_details__department',
            'set_id','set_id__author'
            ).annotate(
                    employee_name = F('employee__user__username'),
                    question_set = F('set_id__set_number'),
                    set_number = F('set_id__set_number'),
                    set_name_id = F('set_id__id'),
                    set_name = F('set_id__name'),
                    author = F('set_id__author__user__username'),
                    department_name = F('employee__work_details__department__name')

            ).values(
                    'employee_name','question_set','set_number','set_name_id','set_name',
                    'author','department_name','creation_date','email_status'
            ).order_by('-id')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class AllKraFormListAPIViewV2(APIView):
    """
    All Kra Form List APIView
    By Company Id
    All Kra Form Of Send Form Model
    """
    model = AppraisalSendForm
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        params = request.query_params
        company_id = kwargs.get('company_id')
        q_filter = db_models.Q(employee__company_id = company_id,manager_acknowledgement = "PENDING")
        if 'select_candidate_status' in params:
            q_filter &= db_models.Q(candidate_status = params.get('select_candidate_status'))
        if "month" in params:
            q_filter &= db_models.Q(creation_date__month = params.get("month"))
        if "year" in params:
            q_filter &= db_models.Q(creation_date__year = params.get("year"))
        if "department" in params:
            q_filter &= db_models.Q(employee__work_details__department_id = params.get("department"))
        if "search_filter" in params:
            q_filter &= (
                db_models.Q(employee__user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
            )
        emp_id = self.request.user.employee_details.first().id
        if 'MANAGER' in list(Employee.objects.filter(id=emp_id).values_list('roles__name',flat=True)) or 'TEAM LEAD' in list(Employee.objects.filter(id=emp_id).values_list('roles__name',flat=True)):
            empls_list = EmployeeReportingManager.objects.filter(manager_id=emp_id, is_deleted=False).values_list('employee',flat=True)
            q_filter &= db_models.Q(employee_id__in = empls_list)
        obj = AppraisalSendForm.objects.filter(q_filter)
        if not obj.exists():
            return Response(
                error_response("Company Not Found KRA Details", 'Company Does Not Have All KRA Details!', 404),
                status=status.HTTP_404_NOT_FOUND
                )
        gett = obj.select_related('employee')
        # appraisal_form_submit_qs = AppraisalFormSubmit.objects.filter(employee__id__in=gett.values_list('employee_id', flat=True), sentform_date__month=month, sentform_date__year=year)
        # gett.filter(employee__id__in=appraisal_form_submit_qs.filter(candidate_status="SUBMITTED").values_list('employee_id', flat=True)).update(candidate_status="SUBMITTED")

        data = gett.annotate(
            employee_name=F('employee__user__username'),
            set_name_id=F('set_id_id'),
            set_name=F('set_id__name'),
            manageemnt_review=F('comment'),
            Creations_date=F('creation_date'),
            department = F('employee__work_details__department__name'),
            employee_user_id = F('employee__user_id')
        ).annotate(
            is_logged_in_user = db_models.Case(
            db_models.When(employee_user_id = request.user.id, then = True),
            default = Value(False), output_field=db_models.BooleanField())

        ).values('id', 'employee', 'employee_name', 'set_name_id', 'set_name', 'candidate_status', 'manager_acknowledgement',
                 'score', 'monthly_score_status','is_revoked', 'manageemnt_review', 'reason', 'department', 'Creations_date', 'is_logged_in_user',
                 'form_deadline_date'
                 ).order_by('-creation_date')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(data, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class CandidateSubmittionAPIViewV2(APIView):
    """
    Candidate Submitted or Not Submitted Filtering APIView
    Based On Company Id And Select Candidate Status
    """
    model = AppraisalSendForm
    pagination_class = CustomPagePagination

    def get(self, request):
        data = request.query_params
        q_filter = db_models.Q(candidate_status = data.get('select_candidate_status'), employee__company_id = data.get('company_id'))

        if not AppraisalSendForm.objects.filter(employee__company_id = data.get('company_id')).exists():
            return Response(
                error_response("Company Not Found Any Submission Of Employee", "Company Doesn't Found Any SUBMITTED Or NOT SUBMITTED Detail Of Employee", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not AppraisalSendForm.objects.filter(candidate_status = data.get('select_candidate_status')).exists():
            return Response(
                error_response("Selected Status Not Found", "Selected Candidate Status Not Exists!", 404),
                status=status.HTTP_404_NOT_FOUND
            )
        
        emp_id = self.request.user.id
        if 'MANAGER' in list(Employee.objects.filter(id=emp_id).values_list('roles__name',flat=True)) or 'TEAM LEAD' in list(Employee.objects.filter(id=emp_id).values_list('roles__name',flat=True)):
            empls_list = EmployeeReportingManager.objects.filter(manager_id = emp_id, is_deleted=False).values_list('employee',flat=True)
            q_filter &= db_models.Q(employee_id__in = empls_list)

        candidate_status = AppraisalSendForm.objects.filter(q_filter).select_related(
            'employee','work_details','employee__work_details__department'
            ).annotate(
                       set_number = F('set_id__set_number'),
                       employee_name = F('employee__user__username'),
                       department = F('employee__work_details__department__name'),
                       manageemnt_review = F('comment'),
                       set_name_id=F('set_id_id'),
                        set_name=F('set_id__name'),
                        Creations_date=F('creation_date'),
            ).values(
                'id','set_number','employee','employee_name','set_name_id','set_name',
                'department','Creations_date','is_revoked','candidate_status','manager_acknowledgement',
                'score','monthly_score_status','manageemnt_review','reason'
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(candidate_status, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class NotificationDateAPIViewV2(APIView):
    """
    Notification Retrive APIView
    By Company Id
    """
    model = NotificationDates

    def get(self, request, *args, **kwargs):
        company_id = kwargs.get('company_id')
        q_filter = db_models.Q(company_id = company_id)
        qs = NotificationDates.objects.filter(q_filter).values(
            'company','id','notification_start_date','notification_end_date',
            'reporting_manager_start_date','reporting_manager_end_date',
            'employees_kra_deadline_date'
        )
        return Response(
            success_response(qs, "Successfully Fetch The Data Of Notification", 200),
            status=status.HTTP_200_OK
            )


class SendFormEmployeeRetriveV2(APIView):
    """
    Retrive Send Form By Employee_id
    """
    model = AppraisalSendForm

    def get(self, request, *args, **kwargs):
        month = timezone_now().month
        year = timezone_now().year
        params = request.query_params
        employee_id = kwargs.get('employee_id')
        q_filter = db_models.Q(employee_id = employee_id, manager_acknowledgement = params.get('manager_acknowledgement'))
        send_form_qs = AppraisalSendForm.objects.filter(q_filter)
        if not send_form_qs.exists():
            return Response(
                error_response("Employee Not Found In SendForm", "Employee Does Not Have SendForm Details!", 404),
                status=status.HTTP_404_NOT_FOUND
                )
        form_submit_qs = AppraisalFormSubmit.objects.filter(employee__id__in = send_form_qs.values_list('employee', flat=True))
        send_form_qs.filter(employee__id__in = form_submit_qs.filter(candidate_status='SUBMITTED').values_list('employee')).update(candidate_status='SUBMITTED')
        data = send_form_qs.select_related(
                'employee',
                'set_id').annotate(
                        employee_action=F('candidate_status'),
                        appraisal_status = F('monthly_score_status'),
                        management_review = F('comment'),
                        set_number = F('set_id__set_number'),
                        set_name = F('set_id__id'),
                        company_name = F('employee__company__company_name')
                        ).values(
                            'id',
                            'company_name','employee','creation_date','employee_action','appraisal_status',
                            'score','manager_acknowledgement','management_review','comment','set_number','set_name','reason').order_by('-creation_date')
        return Response(
            success_response(data, "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class AppraisalRetriveFormSubmitAPIViewV2(APIView):
    """
    Retrive Details Of Submittion From
    Form Submit Model By Employee Id
    """
    model = AppraisalFormSubmit
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        month = timezone_now().month
        year = timezone_now().year
        employee_id = kwargs.get('employee_id')
        query_params = request.query_params
        q_filter = db_models.Q(employee_id=employee_id)
        form_send = AppraisalFormSubmit.objects.filter(q_filter, sentform_date__month=month, sentform_date__year=year)
        # query_params = {'submit_id': 1209}
        if 'submit_id' in query_params:
            form_send = AppraisalFormSubmit.objects.filter(
                employee_id=employee_id, set_name__setnumber_id__id=query_params['submit_id'])
            qs = form_send.select_related(
                'employee','question','employee__work_details','employee__work_details__department',
                'employee__company','set_name'
                ).annotate(
                        employee_name = F('employee__user__username'),
                        employee_number = F('employee__work_details__employee_number'),
                        department = F('employee__work_details__department__name'),
                        name_question = F('question__questions'),
                        company_name = F('employee__company__company_name'),
                        setName = F('set_name__name'),
                        setid = F('set_name__id'),
                ).annotate(
                    comment = Subquery(AppraisalSendForm.objects.filter(set_id = OuterRef('setid'),employee_id = OuterRef('employee_id')).values('comment')[:1]),
                    score = Subquery(AppraisalSendForm.objects.filter(set_id = OuterRef('setid'),employee_id = OuterRef('employee_id')).values('score')[:1])
                ).values(
                    'employee_name','employee_number','department','employee_id','name_question','question',
                    'answer','company_name','setName','setid','comment','score'
                )
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(qs, request)

            return Response(
                success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
                status=status.HTTP_200_OK
                )

        if not form_send.exists():
            return Response(
                error_response("Employee Question And Anwers Not Found", "Employee Does Not Have Any Question And Answer To Show", 404),
                status=status.HTTP_404_NOT_FOUND
                )
        qs = form_send.select_related(
            'employee','question','employee__work_details','employee__work_details__department',
            'employee__company','set_name'
            ).annotate(
                    employee_name = F('employee__user__username'),
                    employee_number = F('employee__work_details__employee_number'),
                    department = F('employee__work_details__department__name'),
                    name_question = F('question__questions'),
                    company_name = F('employee__company__company_name'),
                    setName = F('set_name__name'),
                    setid = F('set_name__id'),
            ).annotate(
                comment = Subquery(AppraisalSendForm.objects.filter(set_id = OuterRef('setid'),employee_id = OuterRef('employee_id'), creation_date__month=month,creation_date__year=year).values('comment')[:1]),
                score = Subquery(AppraisalSendForm.objects.filter(set_id = OuterRef('setid'),employee_id = OuterRef('employee_id'),creation_date__month=month,creation_date__year=year).values('score')[:1])
            ).values(
                'employee_name','employee_number','department','employee_id','name_question','question',
                'answer','company_name','setName','setid','comment','score'
            )
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class AppraisalRetriveQuestionsAPIViewV2(APIView):
    """
    While Candidate_Status == NOT SUBMITTED
    Retrive Questions By Employee_id
    """
    model = AppraisalSendForm
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        month = timezone_now().month
        year = timezone_now().year
        param = request.query_params
        employee_id = kwargs.get('employee_id')
        q_filter = db_models.Q(employee_id = employee_id, set_id__set_number = param.get('set_number'))
        obj = AppraisalSendForm.objects.filter(q_filter, # creation_date__month = month, creation_date__year = year, 
                                            set_id__setname_questions__is_deleted=False)
        if not obj.exists():
            return Response(
                error_response("Employee Not Found Questions Details", "Employee Does Not Have Any Question Details To Retrive", 404),
                status=status.HTTP_404_NOT_FOUND
                )
        
        qs = obj.select_related('set_id', 'set_id__setname_questions','set_id__setname_appraisal'
                    ).annotate(
                        question_id=F('set_id__setname_questions__id'),
                        question = F('set_id__setname_questions__questions'),
                        set_number = F('set_id__set_number'),
                        set_name = F('set_id__name'),
                        emp = F('employee')
                    ).annotate(
                        answer =Subquery(AppraisalFormSubmit.objects.filter(question_id = OuterRef('question_id'),employee__id__in = OuterRef('emp'),
                                                                            sentform_date__month=month,sentform_date__year=year).values('answer')[:1], is_deleted=False),
                    ).values(
                        'question_id','question','answer','employee','set_number','set_name')
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)
        return Response(
            success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200),
            status=status.HTTP_200_OK
            )


class AllArchiveAPIViewV2(APIView):

    model = AppraisalSendForm
    pagination_class = CustomPagePagination

    def get(self, request, *args, **kwargs):
        params = request.query_params
        try:
            q_filters = db_models.Q(is_deleted = False)
            if "id" in params:
                q_filters &= db_models.Q(id=params.get("id"))
            if "company" in params:
                q_filters &= db_models.Q(employee__company = params.get("company"))
            if "employee" in params:
                q_filters &= db_models.Q(employee = params.get("employee"))
            if "month" in params:
                q_filters &= db_models.Q(creation_date__month = params.get("month"))
            if "year" in params:
                q_filters &= db_models.Q(creation_date__year = params.get("year"))
            if "candidate_status" in params:
                q_filters &= db_models.Q(candidate_status = params.get("candidate_status"))
            if "manager_acknowledgement" in params:
                q_filters &= db_models.Q(manager_acknowledgement = params.get("manager_acknowledgement"))
            if "department" in params:
                q_filters &= db_models.Q(employee__work_details__department_id = params.get("department"))
            if "search_filter" in params:
                q_filters &= (
                    db_models.Q(employee__user__username__icontains=search_filter_decode(params.get("search_filter"))) |
                    db_models.Q(employee__work_details__employee_number__icontains=search_filter_decode(params.get("search_filter")))
                )
            paginator = self.pagination_class()

            emp_id = self.request.user.id
            if 'employee' not in params:
                if 'MANAGER' in list(Employee.objects.filter(id=emp_id).values_list('roles__name',flat=True)) or 'TEAM LEAD' in list(Employee.objects.filter(id=emp_id).values_list('roles__name',flat=True)):
                    empls_list = EmployeeReportingManager.objects.filter(manager_id = emp_id, is_deleted=False).values_list('employee',flat=True)
                    q_filters &= db_models.Q(employee_id__in = empls_list)
            data = AppraisalSendForm.objects.filter(q_filters).select_related(
                        'employee', 'employee__work_details', 'employee__work_details__department','employee__employee_manager'
                ).annotate(
                manager_name = ArrayAgg(Concat(
                                    F('employee__employee__manager__first_name'),
                                    Value(' '),
                                    F('employee__employee__manager__middle_name'),
                                    Value(' '),
                                    F('employee__employee__manager__last_name'),
                                    output_field=CharField()
                                    ), 
                                    filter=Q(employee__employee__isnull=False, employee__employee__manager_type__manager_type=10, employee__employee__is_deleted=False, employee__employee__manager__work_details__employee_status='Active'),
                                    distinct=True
                                    ),
                employee_name = Concat(
                                    F('employee__first_name'),
                                    Value(' '),
                                    F('employee__middle_name'),
                                    Value(' '),
                                    F('employee__last_name')
                                    ),
                author = Concat(
                                F('set_id__author__first_name'),
                                Value(' '),
                                F('set_id__author__middle_name'),
                                Value(' '),
                                F('set_id__author__last_name')
                                ),
                company_name = F("employee__company__company_name"),
                department = F('employee__work_details__department__name'),
                set_name = F('set_id__name')
            ).values(
                'id','employee_id','employee_name','department','set_name','set_id','company_name','creation_date',
                'candidate_status','Emp_suggestion', 'manager_acknowledgement', 'score', 'monthly_score_status',
                'email_status','is_revoked', 'comment','reason','manager_name','author'
            ).order_by("-creation_date")
            
            paginator = self.pagination_class() 
            page = paginator.paginate_queryset(data, request)
            
            return Response(
                success_response(paginator.get_paginated_response(page), "Successfully Fetched Data", 200), 
                status=status.HTTP_200_OK,
            )
        
        except Exception as e:
            return Response(
                error_response(f'{str(e)} Error: {traceback.format_exc()}', 400),
                status=status.HTTP_400_BAD_REQUEST,
            )