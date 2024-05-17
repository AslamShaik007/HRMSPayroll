import datetime
import logging

from performance_management.models import AppraisalSetName,AppraisalSetQuestions, AppraisalSendForm,NotificationDates,AppraisalFormSubmit
from performance_management.serializers import (
        AppraisalSetNameSerializer,
        AppraisalSetNameDetailSerializer,
        AppraisalSendFormSerializer,
        NotificationDateSerializer,
        AppraisalFormSubmitSerializer,
        # AppraisalFormSubmitDetailSerializer,
        # AllKraFormListSerializer,
        RetriveAllDepartmentsSerializer,
    )

from directory.models import Employee, EmployeeWorkDetails,EmployeeReportingManager
from company_profile.models import Departments
from django.db.models import Q, F, Value, CharField, OuterRef, Subquery
from django.db.models.functions import Concat


from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateAPIView,
    ListCreateAPIView,
    UpdateAPIView,
)
from django.core.mail import send_mail
from django.core.mail import send_mass_mail
# from core.smtp import send_email
from HRMSApp.utils import Util
from HRMSApp.models import User
from django.conf import settings
from core.utils import (
    b64_to_image,
    email_render_to_string,
    get_formatted_time,
    get_ip_address,
    strptime,
    timezone_now,
    error_response,
    success_response
)
from core.whatsapp import WhatsappMessage
from alerts.utils import check_alert_notification

logger = logging.getLogger(__name__)

#Create And Retrive APIView of set and questions
class AppraisalSetNameCreateAPIView(APIView):
    """
    View to get or create EmployeeAppraisalSetName

    Aslam, 10.05.2023
    """
    model = AppraisalSetName

    def post(self, request):
        serializer = AppraisalSetNameSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            # return Response(serializer.errors,status = status.HTTP_400_BAD_REQUEST)
            Error  = ''
            for index, error in enumerate(serializer.errors):
                Error  += str(serializer.errors.get(error)).split("[ErrorDetail(string='")[1].split("', code=")[0]
            response = error_response('something went wrong',Error, 400)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


# class AppraisalSetNameCreateAPIView(ListCreateAPIView):
#     serializer_class = AppraisalSetNameSerializer
#     queryset = AppraisalSetName.objects.all()



# Retrive Set Name API View
class AppraisalSetNameRetriveAPIView(ListAPIView):
    """
    View to retrieve EmployeeAppraisalSetName and Questions
    Aslam, 10.05.2023
    """

    serializer_class = AppraisalSetNameSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = AppraisalSetName.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)



#Retrive and Update APIView OF Set Name And Questions
class AppraisalSetNameUpdateView(APIView):
    """
    Appraisal Set Name And Questions Retrive And Update
    APIView

    Aslam 23-05-2023
    """
    model = AppraisalSetName
    
    def get(self, request, pk):
        obj_data = AppraisalSetName.objects.get(pk=pk)
        serializer = AppraisalSetNameSerializer(obj_data)
        return Response(serializer.data)


    def put(self, request, pk):
        data = request.data
        obj_get = AppraisalSetName.objects.get(pk=pk)
        month_year = timezone_now().date()
        present_month = month_year.strftime('%m')
        present_year = month_year.strftime('%Y')
            
        if obj_get.name != data['name']:
            if AppraisalSetName.objects.filter(name = data['name'], created_at__month = present_month, created_at__year = present_year).exists():
                return Response(error_response({}, "The Name Already Taken For The Month, Try Different Set Name", 400))
            
        serializer = AppraisalSetNameSerializer(obj_get, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(success_response(serializer.data, "Successfully Updated Data", 200))
        else:
            return Response(error_response(serializer.errors, "Somethink Wents Work, Please try Again Later", 400))



class RetriveAllDepartments(APIView):
    """
    Retriving All Departments Names APIView

    Aslam 23-05-2023
    """
    model = Departments

    def get(self, request, pk):
        query_params = {
            'company__id': pk
        }
        get_all =  Departments.objects.filter(**query_params).values('name')
        return Response({
            "data": get_all
        })



class SendFormDepartmentListAPIView(APIView):
    """
    Retriving Employee Name And Official Email APIView

    Aslam 18-05-2023
    """
    model = AppraisalSendForm

    def get(self, request, pk):
        month=timezone_now().date().month
        year=timezone_now().date().year
        param = request.query_params
        company = param.get('company_id')
        query_params = {
            'department__id': pk
        }
        query_params['employee__company__id'] = company
        form = AppraisalSendForm.objects.filter(employee__work_details__department = pk, employee__company__id = company,
                                                creation_date__month=month, creation_date__year=year).values_list('employee', flat=True)
        
        dept = EmployeeWorkDetails.objects.filter(**query_params).select_related('employee').exclude(employee_id__in = form).annotate(
            emp_id = F('employee__id'),
            employee_name = F('employee__first_name'),
            employee_official_email = F('employee__official_email')
        ).values(
                'emp_id',
                'department__id',
                'employee_name',
                'employee_official_email'
            )
        return Response({"data": dept})



#Send Form Email To Employee Official Email
class SendFormEmailAPIVew(APIView):
    """
    Send E-mail To Employee's Official E-mail Address

    To Get The Monthly Kra Form Link
    
    Aslam 12-05-2023
    """
    
    model = AppraisalSetName

    def post(self, request):
        data = request.data
        month = timezone_now().month
        year = timezone_now().year
        company = data.get('company')
        emp_id = data.get('employee')
        set_num = data.get('set_number')
        set_id = AppraisalSetName.objects.filter(set_number=set_num).order_by('-id').first()
        setnumber_id = set_id.id
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        company_name = request.user.employee_details.first().company.company_name

        if AppraisalSendForm.objects.filter(employee__id__in=emp_id, set_id__set_number=set_num, creation_date__month=month, creation_date__year=year).exists():
            return Response(error_response('Already Send Questionnaire To Given Employee On Present Month'), status=status.HTTP_400_BAD_REQUEST)
        
        if NotificationDates.objects.filter(company__id = request.user.employee_details.first().company.id, employees_kra_deadline_date__lt = timezone_now().date()):
            return Response(error_response({}, "Please Update Your Notification Deadline Date Before Send The Form"))
        
        not_date = NotificationDates.objects.filter(company__id = request.user.employee_details.first().company.id).first()
        emps = Employee.objects.filter(company__id=company, id__in=emp_id, is_deleted=False, work_details__employee_status='Active').annotate(emp_full_name = Concat(('first_name'),Value(' '),('middle_name'),Value(' '),('last_name'))).values("id","emp_full_name","official_email","work_details__employee_number","phone")
        send_form_objs = []
        for emp in emps:
            emp_name = emp['emp_full_name']
            emp_email = emp['official_email']
            emp_id = emp['id']
            emp_number = emp['work_details__employee_number']
            emp_ph_number = emp['phone']
            tag = emp_number if emp_number else "-"

            body = f" Hello {emp_name.title()} [{tag}], \n\nPlease refer the link for more information:--- {domain}employeekra \n\nFill The Form And Submit.\n\nThanks & Regards,\n{company_name.title()}"

            data = {
                "subject": "Monthly Check In Assessment Completion",
                "body": body,
                "to_email": emp_email
            }
            if check_alert_notification("Performance Review",'Send Form', email=True):
                Util.send_email(data)
            send_form_objs.append(AppraisalSendForm(
                                employee_id=emp_id, set_id=set_id, 
                                email_status="Sent", form_deadline_date=not_date.employees_kra_deadline_date))
            
            # employee Whatsapp notifications
            try:
                month_map = { 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
                month_abbreviation = month_map.get(timezone_now().month)
                employee_data = {
                        'phone_number': emp_ph_number,
                        'subject': "Monthly Check In Assessment Completion",
                        'body_text1' :"Please Fill The KRA Form And Submit",
                        'body_text2' :f"For the month of {month_abbreviation} {timezone_now().year}" ,
                        'url': f"{domain}employeekra",
                        "company_name": company_name
                        }
                if check_alert_notification("Performance Review",'Send Form', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {emp_name} in KRA checkin: {e}") 

        AppraisalSendForm.objects.bulk_create(send_form_objs)

        # Send the batch of email messages
        
        try:
            return Response(success_response({}, "mail send", 200), status=status.HTTP_200_OK)
        except Exception as e:
            return Response(error_response(e, 'err', 400), status=status.HTTP_400_BAD_REQUEST)



#Send Form List Of Send Emails To Employee's
class SendFormListAPIView(APIView):
    """
    Send Form Retrive APIView
    
    Aslam 17-05-02023
    """
    model = AppraisalSendForm
    
    def get(self, request, pk):
        param = request.query_params
        query_params = {
            'employee__company_id': pk
        }
        data = AppraisalSendForm.objects.filter(**query_params).select_related(
            'employee',
            'employee__work_details',
            'employee__work_details__department',
            'set_id',
            'set_id__author'

            ).annotate(
                    employee_name = F('employee__first_name'),
                    question_set = F('set_id__set_number'),
                    set_number = F('set_id__set_number'),
                    set_name_id = F('set_id__id'),
                    set_name = F('set_id__name'),
                    author = F('set_id__author__first_name'),
                    department_name = F('employee__work_details__department__name')

            ).values(
                    'employee_name',
                    'question_set',
                    'set_number',
                    'set_name_id',
                    'set_name',
                    'author',
                    'department_name',
                    'creation_date',
                    'email_status'
            )
        return Response({
            "data": data
        })



class AllKraFormListAPIView(APIView):
    """
    All Kra Form List APIView
    
    Aslam 22-05-2023
    """
    
    model = AppraisalSendForm

    def get(self, request, pk):
        month = timezone_now().month
        year = timezone_now().year
        params = request.query_params
        query_params = {
            "employee__company_id": pk
        }
        if not AppraisalSendForm.objects.filter(**query_params, creation_date__month=month, creation_date__year=year).exists():
            return Response({
                'error': 'Company Does Not Have All KRA Details!'
            })
        gett = AppraisalSendForm.objects.filter(**query_params, creation_date__month=month, creation_date__year=year).select_related('employee')
        appraisal_form_submit_qs = AppraisalFormSubmit.objects.filter(employee__id__in=gett.values_list('employee_id', flat=True), sentform_date__month=month, sentform_date__year=year)
        gett.filter(employee__id__in=appraisal_form_submit_qs.filter(candidate_status="SUBMITTED").values_list('employee_id', flat=True)).update(candidate_status="SUBMITTED")

        
        gett.filter(score__gt=0).update(manager_acknowledgement="COMPLETED")

        data = gett.annotate(
            employee_name=Concat(F('employee__first_name'), Value(' '), F('employee__middle_name'), Value(' '), F('employee__last_name'), output_field=CharField()),
            set_name_id=F('set_id_id'),
            set_name=F('set_id__name'),
            manageemnt_review=F('comment'),
            Creations_date=F('creation_date'),
            department = F('employee__work_details__department__name')
        ).values('id', 'employee', 'employee_name', 'set_name_id', 'set_name', 'candidate_status', 'manager_acknowledgement', 'score', 'monthly_score_status',
                 'is_revoked', 'manageemnt_review', 'reason', 'department', 'Creations_date'
                 )
        return Response(data)


class SendFormRetriveUpdateAPIView(APIView):
    """
    Send Form Retrive And update API
    
    Aslam 23-05-2023
    """
    model = AppraisalSendForm

    def get(self, request, pk):
        if AppraisalSendForm.objects.filter(pk=pk).exists():
            get_obj = AppraisalSendForm.objects.get(pk=pk)
            serializer = AppraisalSendFormSerializer(get_obj)
            return Response(serializer.data)
        else:
            return Response({
                'error': 'Given Id Does Not Exists'
            })
    
    def put(self, request, pk):
        if AppraisalSendForm.objects.filter(pk=pk).exists():
            company_name = request.user.employee_details.first().company.company_name
            get_obj = AppraisalSendForm.objects.get(pk=pk)
            if get_obj.manager_acknowledgement == 'COMPLETED':
                return Response({
                    'error': 'Manager has already given the score'
                }) 
            serializer = AppraisalSendFormSerializer(get_obj, data=request.data)
            if serializer.is_valid():
                serializer.save()
                obj_data = serializer.data
                domain = f"{self.request.scheme}://{self.request.get_host()}/"
                emp_number = get_obj.employee.work_details.employee_number
                emp_ph_number = get_obj.employee.phone
                emp_tag = emp_number if emp_number else "-"
                if obj_data['score'] > 0:
                    body = f"Hello {get_obj.employee.user.username.title()} [{emp_tag}],\n\nApprasial Status: {get_obj.monthly_score_status}\n\nManager Acknowledgememt: COMPLETED\n\nComment: {get_obj.comment}\n\nScore: {get_obj.score}\n\nPlease refer the link for more information:--- {domain}employeekra\n\nThanks & Regards,\n{company_name.title()}"
                    data = {
                    "subject": "Monthly KRA Score",
                    "body": body,
                    "to_email": get_obj.employee.official_email
                    }
                    if check_alert_notification("Performance Review",'Manager Review', email=True):
                        Util.send_email(data)
            # employee Whatsapp notifications
            try:
                employee_data = {
                        'phone_number': emp_ph_number,
                        'subject': "Monthly KRA Score",
                        'body_text1' :"Manager Acknowledgememt: COMPLETED",
                        'body_text2' :f"Apprasial Status: {get_obj.monthly_score_status}, Score: {get_obj.score}" ,
                        'url': f"{domain}employeekra",
                        "company_name": company_name
                        }
                if check_alert_notification("Performance Review",'Manager Review', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {get_obj.employee.user.username} in KRA checkin: {e}")

                return Response(serializer.data)
            else:
                return Response(serializer.errors)
        else:
            return Response({
                'error': 'Given Id For Update Does Not Exists'
            })
        



# Filtering Candidate Status Accoding Submitted or not Submitted
class CandidateSubmittionAPIView(APIView):
    """
    Candidate Submitted or Not Submitted Filtering APIView

    Aslam 17-05-2023
    """
    model = AppraisalSendForm

    def get(self, request):
        data = request.query_params
        query_params = {
            "candidate_status": data.get('select_candidate_status')
        }
        query_params['employee__company__id'] = data.get('company_id')

        if not AppraisalSendForm.objects.filter(employee__company_id = data.get('company_id')).exists():
            return Response({
                "error": "Company Doesn't Found Any SUBMITTED Or NOT SUBMITTED Detail Of Employee"
            })
        
        if not AppraisalSendForm.objects.filter(candidate_status = data.get('select_candidate_status')).exists():
            return Response({
                'error': "Given Candidate Status Does Not Exists"
            })
        
        candidate_status = AppraisalSendForm.objects.filter(**query_params).select_related(
            'employee',
            'work_details',
            'employee__work_details__department'

            ).annotate(
                       set_number = F('set_id__set_number'),
                       employee_name = F('employee__first_name'),
                       department = F('employee__work_details__department__name'),
                       manageemnt_review = F('comment'),
                       set_name_id=F('set_id_id'),
                        set_name=F('set_id__name'),
                        Creations_date=F('creation_date'),
            ).values(
                'id',
                'set_number',
                'employee',
                'employee_name',
                'set_name_id',
                'set_name',
                'department',
                'Creations_date',
                'is_revoked',
                'candidate_status',
                'manager_acknowledgement',
                'score',
                'monthly_score_status',
                'manageemnt_review',
                'reason'
            )
        return Response({
            "data": candidate_status
        })




class NotificationDateAPIView(APIView):
    """
    Notification Date Create And List APIView

    Aslam 16-05-2023
    """
    def get(self, request, pk):
        query_params = {
            'company__id': pk
        }

        qs = NotificationDates.objects.filter(**query_params).values(
            'company',
            'id',
            'notification_start_date',
            'notification_end_date',
            'reporting_manager_start_date',
            'reporting_manager_end_date',
            'employees_kra_deadline_date'
        )
        return Response(success_response(qs, "Successfully Fetch The Data Of Notification", 200))






class NotificationRetriveUpdate(APIView):
    """
    Retrive And Update Notification API
    """
    model = NotificationDates

    def get(self, request, pk):
        qs = NotificationDates.objects.get(pk=pk)
        get_bj = {
            "notificationStartDate": qs.notification_start_date,
            "notificationEndDate": qs.notification_end_date,
            "reportingManagerStartDate": qs.reporting_manager_start_date,
            "reportingManagerEndDate": qs.reporting_manager_end_date,
            "employeesKraDeadlineDate": qs.employees_kra_deadline_date
        }

        return Response(
            success_response(get_bj, "Successfully fetched Data", 200),
            status=status.HTTP_200_OK
            )
    
    def put(self, request, pk):
        data = request.data
        if pk == 0:
            obj_create = NotificationDates.objects.create(
                company_id = request.user.employee_details.first().company.id,
                notification_start_date = data.get('notification_start_date'),
                notification_end_date = data.get('notification_end_date'),
                reporting_manager_start_date = data.get('reporting_manager_start_date'),
                reporting_manager_end_date = data.get('reporting_manager_end_date'),
                employees_kra_deadline_date = data.get('employees_kra_deadline_date')
            )

            resp = {
                "id": obj_create.id,
                "notificationStartDate": obj_create.notification_start_date,
                "notificationEndDate": obj_create.notification_end_date,
                "reportingManagerStartDate": obj_create.reporting_manager_start_date,
                "reportingManagerEndDate": obj_create.reporting_manager_end_date,
                "employeesKraDeadlineDate": obj_create.employees_kra_deadline_date
            }

            return Response(
                success_response(resp, "Successfully Notification Updated", 200),
                status=status.HTTP_200_OK
                )
        if NotificationDates.objects.filter(pk=pk).exists():
            qs = NotificationDates.objects.get(pk=pk)
            qs.notification_start_date = data.get('notification_start_date')
            qs.notification_end_date = data.get('notification_end_date')
            qs.reporting_manager_start_date = data.get('reporting_manager_start_date')
            qs.reporting_manager_end_date = data.get('reporting_manager_end_date')
            qs.employees_kra_deadline_date = data.get('employees_kra_deadline_date')
            
            if qs.employees_kra_deadline_date < qs.notification_end_date:
                return Response(
                    {"error": "The deadline date for employees' Key Result Areas (KRAs) should be after the notification end"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if qs.employees_kra_deadline_date < qs.reporting_manager_end_date:
                return Response(
                    {"error": "The deadline date for the Reporting Manager should be less than the end date."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            qs.save()

            updated_obj = {
                "id": qs.id,
                "notificationStartDate": qs.notification_start_date,
                "notificationEndDate": qs.notification_end_date,
                "reportingManagerStartDate": qs.reporting_manager_start_date,
                "reportingManagerEndDate": qs.reporting_manager_end_date,
                "employeesKraDeadlineDate": qs.employees_kra_deadline_date
            }
            
            company_id = request.user.employee_details.first().company.id
            month = timezone_now().month
            year = timezone_now().year
            obj_form = AppraisalSendForm.objects.filter(
                                        employee__company_id=company_id, creation_date__month=month, 
                                        creation_date__year = year, candidate_status="NOT SUBMITTED"
                                    ).update(form_deadline_date=data.get('employees_kra_deadline_date'))
            
            return Response(
                success_response(updated_obj, "Successfully Updated", 200),
                status=status.HTTP_200_OK
                )
        
        else:
            return Response(
                error_response({}, "Not a valid data or Matching query Does Not Exists", 400),
                status=status.HTTP_400_BAD_REQUEST
                )

#Notification Email Reminder Api view
class NotificationDueDateKraAPIView(APIView):
    """
    Notification Date Sending E-mail To An Employee
    Regarding KRA Form Submit Reminder

    Aslam 16-05-2023
    """
    model = AppraisalSendForm


    def post(self, request, company_id):
        today = timezone_now().date()
        pre_date = today.strftime('%d')
        current_date = today.strftime('%m-%Y')
        print("current", current_date)
        params = {
            'company__id': company_id
        }

        if not NotificationDates.objects.filter(**params).exists():
            return Response(error_response({}, "Company Does Not Have Notifications Dates"))
        
        notification_date = NotificationDates.objects.filter(**params).first()
        obj = AppraisalSendForm.objects.filter(employee__company__id = company_id).select_related(
                'employee',
                'employee__employee_manager'
                ).annotate(
                            employee_name = Concat(F('employee__first_name'), Value(' ') , F('employee__middle_name'), Value(' '), F('employee__last_name')),
                            employee_official_email = F('employee__official_email'),
                            manager_name = Concat(
                                                    F('employee__employee_manager__manager__first_name'),
                                                    Value(' '),
                                                    F('employee__employee_manager__manager__middle_name'),
                                                    Value(' '),
                                                    F('employee__employee_manager__manager__last_name')
                                                ),
                            manager_official_email = F('employee__employee_manager__manager__official_email'),
                            manager_employee_name = Concat(
                                                            F('employee__employee_manager__employee__first_name'),
                                                            Value(' '), 
                                                            ('employee__employee_manager__employee__middle_name'),
                                                            Value(' '),
                                                            F('employee__employee_manager__employee__last_name')
                                                            )
                            ).values(
                                    'creation_date',
                                    'candidate_status',
                                    'employee_name',
                                    'employee_official_email',
                                    'monthly_score_status',         
                                    'manager_name',
                                    'manager_official_email',
                                    'manager_employee_name'
                                    )

        for qs in obj:
            qs_date = qs['creation_date']
            month_year = qs_date.strftime('%m-%Y')
            
            if qs['candidate_status'] == "NOT SUBMITTED" and month_year == current_date and timezone_now().date() >= notification_date.notification_start_date and timezone_now().date() <= notification_date.notification_end_date:
                body1 = f" Dear {qs['employee_name']},\n\nThis is a gentle reminder that you have to submit your monthly KRA Form before {pre_date} of {today.strftime('%b')} \n\nRegards,\nVitel Global Communications."
                data = {
                    "subject": "Reminder- Monthly check-in due date approaching",
                    "body": body1,
                    "to_email": qs['employee_official_email']
                }
                Util.send_email(data)


            if qs['candidate_status'] == "NOT SUBMITTED" and month_year == current_date and timezone_now().date() == notification_date.employees_kra_deadline_date:
                body2 = f" Dear {qs['employee_name']},\n\nThis is a gentle reminder that you have not submitted your monthly KRA form on the due date of the month {today.strftime('%B')}.\nSo fill the KRA form by {notification_date.employees_kra_deadline_date} \n\nRegards,\nViteGlobal Communications"
                data = {
                    "subject": "Alert- Monthly check-in passed due date",
                    "body": body2,
                    "to_email": qs['employee_official_email']
                }
                Util.send_email(data)
            
            if qs['monthly_score_status'] == "PENDING" and month_year == current_date and timezone_now().date() >= notification_date.reporting_manager_start_date and timezone_now().date() <= notification_date.reporting_manager_end_date:
                body3 = f" Dear {qs['manager_name']},\n\nThis e-mail is a gentle reminder to submit the Monthly check-in assessment for the employee {qs['manager_employee_name']}, before 10th of this month {today.strftime('%m')} \n\nRegards,\nVitel Global Communications."
                data = {
                    "subject": "Monthly check in assessment completion",
                    "body": body3,
                    "to_email": qs['manager_official_email']
                }
                Util.send_email(data)

            if qs['monthly_score_status'] == "PENDING" and month_year == current_date and timezone_now().date() == notification_date.employees_kra_deadline_date:
                body4 = f" Dear {qs['manager_name']},\n This is to notify that you have not given monthly check in score for the employee {qs['manager_employee_name']} for the month of {today.strftime('%b')}. Please complete the Monthly check-in assessment immediately.. \n\nRegards,\nVitel Global Communications"
                data = {
                    "subject": "Monthly check-in assessment pending",
                    "body": body4,
                    "to_email": qs['manager_official_email']
                }
                Util.send_email(data)
        return Response(success_response({}, "Mail Has Been Send To Official E-mail's", 200))


class SendFormEmployeeRetrive(APIView):
    """
    Retrive Send Form By Employee_id
    """
    model = AppraisalSendForm

    def get(self, request, pk):
        month = timezone_now().month
        year = timezone_now().year
        params = request.query_params
        query_params = {
            "employee__id": pk
        }
        if not AppraisalSendForm.objects.filter(**query_params, creation_date__month=month, creation_date__year=year).exists():
            return Response({
                "error": "Employee Does Not Have SendForm Details!"
            })
        send_form_qs = AppraisalSendForm.objects.filter(**query_params, creation_date__month=month, creation_date__year=year)

        form_submit_qs = AppraisalFormSubmit.objects.filter(employee__id__in = send_form_qs.values_list('employee', flat=True))

        send_form_qs.filter(employee__id__in = form_submit_qs.filter(candidate_status='SUBMITTED',sentform_date__month=month, sentform_date__year=year).values_list(
            'employee'
            )).update(candidate_status='SUBMITTED')
        
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
                            'company_name',
                            'employee',
                            'creation_date',
                            'employee_action',
                            'appraisal_status',
                            'score',
                            'manager_acknowledgement',
                            'management_review',
                            'comment',
                            'set_number',
                            'set_name',
                            'reason')
        return Response({
            "data": data
        })




class AppraisalFormSubmitCreateAPIView(ListCreateAPIView):
    serializer_class = AppraisalFormSubmitSerializer
    queryset = AppraisalFormSubmit.objects.all()

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        # if NotificationDates.objects.filter(company_id = request.user.employee_details.first().company.id, employees_kra_deadline_date__gte = timezone_now().date()):
        if AppraisalSendForm.objects.filter(employee_id = request.data.get('employee'),set_id=request.data.get('set_name'),form_deadline_date__gte = timezone_now().date()).exists():
            serializer.is_valid(raise_exception=True)
            instances = serializer.save()
            return Response(
                self.get_serializer(instances, many=True).data, status=status.HTTP_201_CREATED
            )
        else:
            return Response(error_response({}, "You Cross The Dead Line For Submission, Please Connect Your Admin"),status=status.HTTP_400_BAD_REQUEST)


# class AppraisalRetriveFormSubmitAPIView(ListAPIView):
#     """
#     View to retrieve EmployeeAppraisalSetName and Questions
    
#     Aslam, 10.05.2023
#     """

#     serializer_class = AppraisalFormSubmitSerializer
#     lookup_field = "employee"
#     lookup_url_kwarg = "employee_id"
#     queryset = AppraisalFormSubmit.objects.all()

#     def filter_queryset(self, queryset):
#         filter_kwargs = {
#             self.lookup_field: self.kwargs[self.lookup_url_kwarg],
#             "is_deleted": False,
#         }
#         return queryset.filter(**filter_kwargs)

class AppraisalRetriveFormSubmitAPIView(APIView):
    def get(self, request, pk):
        month = timezone_now().month
        year = timezone_now().year
        query_params = {
            'employee__id': pk
        }
        if not AppraisalFormSubmit.objects.filter(**query_params, sentform_date__month=month, sentform_date__year=year).exists():
            return Response({
                "error": "Employee Does Have Any Question And Answer To Show"
            })
        qs = AppraisalFormSubmit.objects.filter(**query_params, sentform_date__month=month, sentform_date__year=year).select_related(
            'employee',
            'question',
            'employee__work_details',
            'employee__work_details__department',
            'employee__company',
            'set_name'
            ).annotate(
                    employee_name = Concat(F('employee__first_name'), F('employee__middle_name'), F('employee__last_name')),
                    employee_number = F('employee__work_details__employee_number'),
                    department = F('employee__work_details__department__name'),
                    name_question = F('question__questions'),
                    company_name = F('employee__company__company_name'),
                    setName = F('set_name__name'),
                    setid = F('set_name__id'),
            ).annotate(
                comment = Subquery(AppraisalSendForm.objects.filter(set_id = OuterRef('setid')).values('comment')[:1]),
                score = Subquery(AppraisalSendForm.objects.filter(set_id = OuterRef('setid')).values('score')[:1])
            ).values(
                'employee_name',
                'employee_number',
                'department',
                'employee_id',
                'name_question',
                'question',
                'answer',
                'company_name',
                'setName',
                'setid',
                'comment',
                'score'
            )
        return Response({
            'data': qs
        })




class AppraisalFormSubmitRetriveUpdateView(APIView):
    """
    View to update EmployeeAppraisalSetName and Questions

    Aslam, 10.05.2023
    """
    
    model = AppraisalFormSubmit

    def get(self, request, pk):
        # data = request.data
        obj = AppraisalFormSubmit.objects.filter(employee__id = pk).annotate(
            emp_id = F('employee__id')
        ).values(
            'id',
            'emp_id',
            'set_name__id',
            'question__id',
            'answer',
            'sentform_date',
            'candidate_status'
        )
        return Response(obj)


    def put(self, request, pk):
        data = request.data
        for i in data:
            gg = AppraisalFormSubmit.objects.filter(id = i['id']).first()
            gg.employee = Employee.objects.get(id = i['emp_id'])
            gg.set_name = AppraisalSetName.objects.get(id = i['set_name__id'])
            gg.question = AppraisalSetQuestions.objects.get(id = i['question__id'])
            gg.answer = i['answer']
            gg.candidate_status = i['candidate_status']
            gg.save()
        return Response({
            "status": status.HTTP_200_OK,
            "response": "updated Successfully"
        })


class AppraisalRetriveQuestionsAPIView(APIView):
    """
    While Candidate_Status == NOT SUBMITTED
    Retrive Questions By Employee_id
    """
    model = AppraisalSendForm

    def get(self, request, pk):
        month = timezone_now().month
        year = timezone_now().year
        param = request.query_params
        query_params = {
            'employee__id': pk,

        }
        set_num = param.get('set_number')
        query_params['set_id__set_number'] = set_num
        if not AppraisalSendForm.objects.filter(**query_params).exists():
            return Response({
            'error': 'Employee Does Not Have Any Question Details To Retrive'
            })
        
        qs = AppraisalSendForm.objects.filter(**query_params,creation_date__month=month, creation_date__year=year).select_related('set_id', 'set_id__setname_questions','set_id__setname_appraisal'
                    ).annotate(
                        question_id=F('set_id__setname_questions__id'),
                        question = F('set_id__setname_questions__questions'),
                        set_number = F('set_id__set_number'),
                        set_name = F('set_id__name'),
                        emp = F('employee')
                    ).annotate(
                        answer =Subquery(AppraisalFormSubmit.objects.filter(question_id = OuterRef('question_id'), employee__id__in = OuterRef('emp')).values('answer')[:1]),
                    ).values(
                        'question_id',
                        'question',
                        'answer',
                        'employee',
                        'set_number',
                        'set_name')
        return Response({
            'data': qs
        })



class AllArchiveEmployerAPIView(APIView):
    """
    All Archive Employer Side APIView
    """
    
    model = AppraisalSendForm

    def get(self, request):
        kra_list = request.query_params
        q_dict = {
            'employee__company_id' : kra_list.get('company')
        }
        month = kra_list.get('month')
        year = kra_list.get('year')
        if not (month or year):
            return Response(
                "Month And year were Required", status=status.HTTP_400_BAD_REQUEST
            )
        q_dict['creation_date__month'] = month
        q_dict['creation_date__year'] = year
        data = AppraisalSendForm.objects.filter(**q_dict).select_related(
            'employee', 'employee__work_details', 'employee__work_details__department'
        ).values(
            'employee__company_id',
            'creation_date', 'set_id__name', 'employee__first_name',
            'employee__work_details__department__name', 
            'is_revoked', 'candidate_status', 'manager_acknowledgement',
            'score', 'monthly_score_status', 'comment', 'reason'
        )
        return Response(data, status=status.HTTP_200_OK)




class AllArchiveEmployeeAPIView(APIView):
    """
    All Archive Of Employee Side APIView
    """

    model = AppraisalSendForm

    def get(self, request):
        kra_list = request.query_params
        q_dict = {
            'employee_id' : kra_list.get('employee')
        }
        month = kra_list.get('month')
        year = kra_list.get('year')
        if not (month or year):
            return Response(
                "Month And year were Required", status=status.HTTP_400_BAD_REQUEST
            )
        q_dict['creation_date__month'] = month
        q_dict['creation_date__year'] = year
        data = AppraisalSendForm.objects.filter(**q_dict).select_related(
            'employee', 'employee__work_details', 'employee__work_details__department'
        ).values(
            'employee__company_id',
            'creation_date', 'set_id__name', 'employee__first_name',
            'employee__work_details__department__name', 
            'is_revoked', 'candidate_status', 'manager_acknowledgement',
            'score', 'monthly_score_status', 'comment', 'reason'
        )
        return Response(data, status=status.HTTP_200_OK)
    




class EmployerRevokeAPIView(APIView):
    """
    Revoke E-mail To Employee by Employer APIview
    """
    
    model = AppraisalSendForm

    def post(self, request):
        data = request.data
        month = timezone_now().month
        year = timezone_now().year
        Context = {}

        if not data.get('company') and data.get('employee'):
            return Response({
                "response": "Company And Employee Required!"
            })
        
        Context['employee__company_id'] = data.get('company')
        Context['employee_id'] = data.get('employee')
        obj_form = AppraisalSendForm.objects.filter(**Context, creation_date__month=month, creation_date__year = year, candidate_status="NOT SUBMITTED").select_related('employee')
        NextDay_Date = datetime.datetime.today() + datetime.timedelta(days=2)
        nextdate = NextDay_Date.strftime('%Y-%m-%d')
        # NotificationDates.objects.filter(company__id__in=obj_form.values('employee__company_id')).update(employees_kra_deadline_date=nextdate)
        first_obj = obj_form.first()
        obj_form.update(form_deadline_date=nextdate, is_revoked=True)
        company_name = request.user.employee_details.first().company.company_name
        domain = f"{self.request.scheme}://{self.request.get_host()}/"
        emp_number = obj_form.first().employee.work_details.employee_number
        emp_tag = emp_number if emp_number else "-"
        if first_obj:
            body = f" Hello {obj_form.first().employee.user.username.title()} [{emp_tag}], \n\nThis is a gentle reminder that you have not submitted your monthly KRA form on the due date of the month {obj_form.first().creation_date.month} \n\nSo fill the KRA form by {nextdate}.\n\nPlease refer the link for more information:--- {domain}employeekra\n\nThanks & Regards,\n{company_name.title()}"
            data1 = {
                "subject": "Revoke Employee",
                "body": body,
                "to_email": obj_form.first().employee.official_email
            }
            if check_alert_notification("Performance Review",'Revoke Employee', email=True):
                Util.send_email(data1)
            # employee Whatsapp notifications
            try:
                month_map = { 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
                month_abbreviation = month_map.get(timezone_now().month)
                employee_data = {
                        'phone_number': f"{obj_form.first().employee.phone}",
                        'subject': "Revoke Employee",
                        'body_text1' :f"This is a gentle reminder that you have not submitted your monthly KRA form on the due date of the month {month_abbreviation} {timezone_now().year}",
                        'body_text2' :f"So fill the KRA form by {NextDay_Date.strftime('%d-%m-%Y')}." ,
                        'url': f"{domain}employeekra",
                        "company_name": company_name
                        }
                if check_alert_notification("Performance Review",'Revoke Employee', whatsapp=True):
                    WhatsappMessage.whatsapp_message(employee_data)
            except Exception as e:
                logger.warning(f"Error while sending Whatsapp notificaton to {obj_form.employee.user.username} in KRA revoke: {e}")
            return Response({"revoke": "Revoke To employee Successfully"})
        else:
            return Response({"response": "No AppraisalSendForm objects found or already submitted for month."})
        


class Employeesubmittiondetail(APIView):

    model = AppraisalFormSubmit
    def get(self, request, pk):
        month = timezone_now().month
        year = timezone_now().year
        param = request.query_params
        query_params = {
            'employee__id': pk
        }
        query_params['set_name__id'] = param.get('set_name')
        q = AppraisalFormSubmit.objects.filter(**query_params,sentform_date__month = month, sentform_date__year = year)
        if not q.exists():
            return Response({
                "error": "On Given Set Name Doesn't Found Any Form Submittion"
            })
        qs = AppraisalFormSubmit.objects.filter(**query_params, sentform_date__month = month, sentform_date__year = year).select_related(
            'employee', 'set_id',
            'set_id__setname_questions',
            'set_name__setnumber_id',
            'employee__work_details',
            'employee__work_details__department'
            ).annotate(
            employee_name = Concat(F('employee__first_name'), Value(' '), F('employee__middle_name'), Value(' '), F('employee__last_name'), output_field=CharField()),
            employee_number = F('employee__work_details__employee_number'),
            department = F('employee__work_details__department__name'),
            name_set = F('set_name__name'),
            ques = F('question__questions'),
            management_review = F('set_name__setnumber_id__comment'),
            score = F('set_name__setnumber_id__score')
        ).values(
            'employee_name',
            'employee_number',
            'department',
            'name_set',
            'ques',
            'answer',
            'management_review',
            'score'
        )
        return Response({
            "data": qs
        })