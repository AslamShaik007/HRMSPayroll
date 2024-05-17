from django.urls import path

from HRMSApp.views import *  # noqa

from .views import companies
from .views import companies_v2 as v2_views
from company_profile import dashboard_views as views

urlpatterns = [
    # Company Detailes Urls
    path(
        "details/<int:id>/",
        companies.CompanyDetailesRetrieveUpateView.as_view(),
        name="update_company_details",
    ),
    # Organization_Custom_address_title Urls
    path(
        "custom/address/",
        companies.CustomAddressDetailsCreateView.as_view(),
        name="generate_custom_address",
    ),
    path(
        "update/custom/address/<int:id>/",
        companies.CustomAddressDetailsUpdateView.as_view(),
        name="custom_address_update",
    ),
    path(
        "custom/address/<int:company_id>/",
        companies.CustomAddressDetailsRetrieveView.as_view(),
        name="get_custom_address",
    ),
    # Department API view urls
    path(
        "department/",
        companies.CompanyDepartmentCreateView.as_view(),
        name="create_department",
    ),
    path(
        "update/department/<int:id>/",
        companies.CompanyDepartmentUpateView.as_view(),
        name="update_department",
    ),
    path(
        "department/<int:company_id>/",
        companies.CompanyDepartmentRetrieveView.as_view(),
        name="get_company_departments",
    ),
    # Designation Master API view urls
    path(
        "designation/",
        companies.CompanyDesignationsCreateView.as_view(),
        name="generate_designation",
    ),
    path(
        "update/designation/<int:id>/",
        companies.CompanyDesignationsUpdateView.as_view(),
        name="update_designation",
    ),
    path(
        "designation/<int:company_id>/",
        companies.CompanyDesignationsRetrieveView.as_view(),
        name="get_designation",
    ),
    # Company Grades Urls
    path(
        "grades/",
        companies.CompanyGradesCreateView.as_view(),
        name="generate_company_grades",
    ),
    path(
        "update/grades/<int:id>/",
        companies.CompanyGradesUpdateView.as_view(),
        name="update_company_grades",
    ),
    path(
        "grades/<int:company_id>/",
        companies.CompanyGradesRetrieveView.as_view(),
        name="get_company_grades",
    ),
    # Company Announcements URLS's
    path(
        "announcement/",
        companies.CompanyAnnouncementCreateView.as_view(),
        name="generate_company_announcement",
    ),
    path(
        "update/announcement/<int:id>/",
        companies.CompanyAnnouncementUpdateView.as_view(),
        name="update_company_announcement",
    ),
    path(
        "announcement/<int:company_id>/",
        companies.CompanyAnnouncementRetrieveView.as_view(),
        name="get_company_announcement",
    ),
    path(
    "ticker/<int:company_id>/",
    companies.CompanyTickerRetrieveView.as_view(),
    name="get_company_ticker",
    ),
    # Company Policies urls
    path(
        "policies/",
        companies.CompanyPoliciesCreateView.as_view(),
        name="generate_company_policies",
    ),
    path(
        "update/policies/<int:id>/",
        companies.CompanyPoliciesUpdateView.as_view(),
        name="update_company_policies",
    ),
    path(
        "policies/<int:company_id>/",
        companies.CompanyPoliciesRetrieveView.as_view(),
        name="get_company_policies",
    ),
    # Retriev Company Entity_Type
    # path(
    #     "createentity/",
    #     companies.CompanyEntityTypeCreateView.as_view(),
    #     name="generate_company_Entity",
    # ),
    path(
        "entity/type/",
        companies.CompanyEntityRetrieveView.as_view(),
        name="get_company_entitytype",
    ),
    # Company_Statutory_COMPANY_ID Urls
    path(
        "update/statutory/<int:company_id>/",
        companies.CompanyStatutoryDetailsUpdateView.as_view(),
        name="update_company_statutory",
    ),
    path(
        "statutory/<int:company_id>/",
        companies.CompanyStatutoryDetailsRetrieveView.as_view(),
        name="get_company_statutory",
    ),
    # Company Directors URL's
    path(
        "director/",
        companies.CompanyDirectorDetailsCreateView.as_view(),
        name="generate_company_director",
    ),
    path(
        "update/director/<int:id>/",
        companies.CompanyDirectorDetailsUpdateView.as_view(),
        name="update_company_director",
    ),
    path(
        "director/<int:company_id>/",
        companies.CompanyDirectorDetailsRetrieveView.as_view(),
        name="get_company_director",
    ),
    # Company Auditors URL's
    path(
        "auditor/",
        companies.CompanyAuditorDetailsCreateView.as_view(),
        name="generate_company_Auditor",
    ),
    path(
        "update/auditor/<int:id>/",
        companies.CompanyAuditorDetailsUpdateView.as_view(),
        name="update_company_Auditor",
    ),
    path(
        "auditor/<int:company_id>/",
        companies.CompanyAuditorDetailsRetrieveView.as_view(),
        name="get_company_auditor",
    ),
    path(
        "auditor/type/",
        companies.ComapanyAuditortypeRetrieveView.as_view(),
        name="get_company_auditor",
    ),
    # path(
    #     "createauditor/",
    #     companies.CompanyAuditorCreateView.as_view(),
    #     name="generate_company_Auditor",
    # ),
    # Company Sectreatory URL's
    path(
        "secretary/",
        companies.CompanySecretaryDetailsCreateView.as_view(),
        name="generate_company_Secretary",
    ),
    path(
        "update/secretary/<int:id>/",
        companies.CompanySecretaryDetailsUpdateView.as_view(),
        name="update_company_Secretary",
    ),
    path(
        "secretary/<int:company_id>/",
        companies.CompanySecretaryDetailsRetrieveView.as_view(),
        name="get_company_secretary",
    ),
    # Company Bank Detailes URL's
    path(
        "bank/",
        companies.CompanyBankDetailsCreateView.as_view(),
        name="generate_company_bank",
    ),
    path(
        "update/bank/<int:id>/",
        companies.CompanyBankDetailsUpdateView.as_view(),
        name="update_company_bank",
    ),
    path(
        "bank/<int:company_id>/",
        companies.CompanyBankDetailsRetrieveView.as_view(),
        name="get_company_secretary",
    ),
    path(
        "bankaccount/type/",
        companies.BankAccountTypesRetrieveView.as_view(),
        name="get_company_auditor",
    ),
    path('get/sub/departments/', companies.GetSubDepartments.as_view(), name='get_sub_departments'),
    # path(
    #     "createaccounttype/",
    #     companies.BankAccountTypesCreateView.as_view(),
    #     name="generate_company_Auditor",
    # ),
    
# V2 APIS starts here
path('v2/details/<int:id>/', v2_views.CompanyDetailsAPIViewV2.as_view(), name='v2_company_details'),
path('v2/bank/details/<int:id>/', v2_views.CompanyBankDetailsV2.as_view(), name='v2_company_bank_details'),
path('v2/secretary/details/<int:id>/', v2_views.CompanySecretaryDetailsV2.as_view(), name='v2_company_secretary_details'),
path('v2/directory/details/<int:id>/', v2_views.CompanyDirectoryDetailsV2.as_view(), name='v2_company_directory_details'),
path('v2/auditor/details/<int:id>/', v2_views.CompanyAuditorDetailsV2.as_view(), name='v2_company_auditor_details'),
path('v2/customaddress/details/<int:id>/', v2_views.CompanyCustomAddressDetailsV2.as_view(), name='v2_company_customaddress_details'),
path('v2/departments/details/<int:id>/', v2_views.CompanyDepartmentDetailsV2.as_view(), name='v2_company_departments_details'),
path('v2/designation/details/<int:id>/', v2_views.CompanyDesignationDetailsV2.as_view(), name='v2_company_designation_details'),
path('v2/grade/details/<int:id>/', v2_views.CompanyGradeDetailsV2.as_view(), name='v2_company_grade_details'),
path('v2/logging/records/', v2_views.LoggingRecordsAPIViewV2.as_view(), name='v2_logging_records'),
path('v2/manager/departments/details/<int:id>/', v2_views.ManagerDepartmentDetailsV2.as_view(), name='v2_manager_departments_details'),
#Dashboard Views
path('v2/emp/departments/count/', views.AdminDepartmentsDetails.as_view(), name='v2_department_count'),
path('v2/emp/pending/signup/', views.AdminPendingEmployeeSignups.as_view(), name='v2_pending_emp_signup'),
path('dashboard/announcements/', views.EmployeeAnnouncementsView.as_view(), name='dashboard_announcements'),
path('dashboard/bestemployee/', views.BestEmployyeDashboardView.as_view(), name='dashboard_bestemployees'),
path('dashboard/ticker/', views.EmployeeTickerView.as_view(), name='dashboard_ticker'),

#Employee Missing Info Records
path('employee/missing/info/',v2_views.EmployeeMissingInfoListAPIView.as_view(),name='emploee_missing_info'),

#Setup Wizard Email Notification
path('setupwizard/notification/',v2_views.SetupWizardNotificationAPIView.as_view(),name='setupwizard_notification'),
path('default/leaverules/',v2_views.DefaultLeaveRulesAPIView.as_view(),name='default_leaverules'),
path('size/update/',v2_views.CompanySizeUpdateAPIView.as_view(),name='company_size_update'),

]
