from django.urls import path

from performance_management import views
from performance_management import v2_views, dashboard_views


urlpatterns = [
    #Set Name And Questions API Urls
    path('set/names/create/', views.AppraisalSetNameCreateAPIView.as_view(), name="set_names"),
    path('set/names/list/<int:company_id>/', views.AppraisalSetNameRetriveAPIView.as_view(), name="set_names_list"),
    path('set/names/update/<int:pk>/', views.AppraisalSetNameUpdateView.as_view(), name="set_names_update"),


    #Send Form Api urls
    path('sendform/department/list/<int:pk>/', views.SendFormDepartmentListAPIView.as_view(), name="sendform_departments"),
    path('sendform/email/', views.SendFormEmailAPIVew.as_view(), name="sendform_email"),
    path('sendform/list/<int:pk>/', views.SendFormListAPIView.as_view(), name="sendform_list"),
    path('sendform/update/<int:pk>/', views.SendFormRetriveUpdateAPIView.as_view(), name="sendform_update"),

    path('sendform/emp/retrive/<int:pk>/', views.SendFormEmployeeRetrive.as_view(), name="sendform_emp_retrive"),
    
    #After employee Form Submittion Retrive Details For Update The Score
    path('employee/submittion/detail/retrive/<int:pk>/', views.Employeesubmittiondetail.as_view(), name="employee_submittion_detail"),

    #Filter Submitted or Not Submitted Api Urls
    path('candidate/submittion/', views.CandidateSubmittionAPIView.as_view(), name="candidate_submittion"),


    #Retrive All Departments Name API Urls
    path('departments/name/retrive/<int:pk>/', views.RetriveAllDepartments.as_view(), name="department_retrive"),


    #ALL Kra Form List Api Urls
    # path('allkra/formlist/', views.AllKraFormListAPIView.as_view(), name="allkra_formlist"),
    path('allkra/retrive/<int:pk>/', views.AllKraFormListAPIView.as_view(), name="allkra_retrive"),


    #Notification Api Urls
    path('notificationdate/create/<int:pk>/', views.NotificationDateAPIView.as_view(), name="notificationdate_create"),
    path('notificationdate/retrive/update/<int:pk>/', views.NotificationRetriveUpdate.as_view(), name="notificationdate_retrive_update"),
    path('notification/duedate/<int:company_id>/', views.NotificationDueDateKraAPIView.as_view(), name="notificationdate_duedate"),


    #Form Submit Api Urls
    path('employee/kra/create/', views.AppraisalFormSubmitCreateAPIView.as_view(), name="employee_kra"),
    path('employee/kra/retrive/<int:pk>/', views.AppraisalRetriveFormSubmitAPIView.as_view(), name="employee_kra_retrive"),
    path('employee/kra/update/<int:pk>/', views.AppraisalFormSubmitRetriveUpdateView.as_view(), name="update_formsubmit"),


    #Retriveing Only Questions And Id Api Urls
    # path('employee/kra/list/', views.AppraisalFormSubmitRetriveAPIView.as_view(), name="employee_kra_list"),
    path('retrive/questions/<int:pk>/', views.AppraisalRetriveQuestionsAPIView.as_view(), name="retrive_questions"),


    path('allarchive/employer/', views.AllArchiveEmployerAPIView.as_view(), name="allarchive_employer"),
    path('allarchive/employee/', views.AllArchiveEmployeeAPIView.as_view(), name="allarchive_employee"),
    path('revoke/employee/', views.EmployerRevokeAPIView.as_view(), name="revoke_employee"),



    # V2 Performance Management Api's
    path('v2/set/names/list/<int:company_id>/', v2_views.AppraisalSetNameRetriveAPIViewV2.as_view(), name='setname_retrive'),
    path('v2/departments/name/retrive/<int:company_id>/', v2_views.RetriveAllDepartmentsV2.as_view(), name='department_name_retrive'),
    path('v2/sendform/department/list/<int:department_id>/', v2_views.SendFormDepartmentListAPIViewV2.as_view(), name='sendform_department_retrive'),
    path('v2/sendform/list/<int:company_id>/', v2_views.SendFormListAPIViewV2.as_view(), name='sendform_retrive_list'),
    path('v2/allkra/retrive/<int:company_id>/', v2_views.AllKraFormListAPIViewV2.as_view(), name='allkra_retrive_list'),
    path('v2/candidate/submittion/', v2_views.CandidateSubmittionAPIViewV2.as_view(), name='candidate_status'),
    path('v2/notificationdate/create/<int:company_id>/', v2_views.NotificationDateAPIViewV2.as_view(), name='notification_retrive'),
    path('v2/sendform/emp/retrive/<int:employee_id>/', v2_views.SendFormEmployeeRetriveV2.as_view(), name='sendform_retrive_emp'),
    path('v2/employee/kra/retrive/<int:employee_id>/', v2_views.AppraisalRetriveFormSubmitAPIViewV2.as_view(), name='formsubmit_retrive_emp'),
    path('v2/retrive/questions/<int:employee_id>/', v2_views.AppraisalRetriveQuestionsAPIViewV2.as_view(), name='question_retrive_emp'),
    path('v2/allarchive/', v2_views.AllArchiveAPIViewV2.as_view(), name='all_archive_api'),
    
    
    # Dashboard APIs
    path('emp/kra/', dashboard_views.UserKraDetails.as_view(), name='user_kra_details'),
    path('admin/kra/', dashboard_views.AdminPendingKraDetails.as_view(), name='admin_kra_details')
    
    
]
