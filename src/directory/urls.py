# from HRMSApp.views import *
from django.urls import path

from directory import views
from directory import v2_views, dashboard_views

urlpatterns = [
    # DropDown URL's
    path(
        "employee/type/",
        views.CompanyEmployeeTypeRetrieveView.as_view(),
        name="get_employee_type",
    ),
    path(
        "manager/type/",
        views.CompanyManagerTypeRetrieveView.as_view(),
        name="get_manager_type",
    ),
    path(
        "qualification/type/",
        views.QualificationTypeRetrieveView.as_view(),
        name="get_qualification_type",
    ),
    path(
        "course/type/",
        views.CourseTypeRetrieveView.as_view(),
        name="get_course_type",
    ),
    path(
        "document/type/",
        views.DocumentsTypeRetrieveView.as_view(),
        name="get_document_type",
    ),
    path(
        "relationship/type/",
        views.RelationshipTypeRetrieveView.as_view(),
        name="get_relationship_type",
    ),
    path(
        "certification/type/",
        views.CertificationCourseTypeRetrieveView.as_view(),
        name="get_certification_type",
    ),
    # Add Employee Related All Url's
    path(
        "add/employee/",
        views.EmployeeCreateView.as_view(),
        name="add_employee",
    ),
    path(
        "bulk_update/employee/",
        views.EmployeeBulkUpdateView.as_view(),
        name="bulk_update_employee",
    ),
    path(
        "import/employee/",
        views.EmployeeImportView.as_view(),
        name="import_employee",
    ),
    path(
        "get_update/employee/<int:id>/",
        views.EmployeeRetrieveUpdateView.as_view(),
        name="update_employee",
    ),
    path(
        "get/employee/<int:company_id>/",
        views.EmployeeRetrieveView.as_view(),
        name="get_employee",
    ),
    path(
        "employee/manager/",
        views.EmployeeReportingManagerCreateView.as_view(),
        name="generate_employee_manager",
    ),
    path(
        "update/employee/manager/<int:id>/",
        views.EmployeeReportingManagerUpdateView.as_view(),
        name="update_employee_manager",
    ),
    path(
        "fetch/manager/employee/data/",
        views.ManagerEmployeeDetails.as_view(),
        name="manager_employee_details",
    ),
    path(
        "employee/manager/<int:employee_id>/",
        views.EmployeeReportingManagerRetrieveView.as_view(),
        name="get_employee_manager",
    ),
    path(
        "employee/education/",
        views.EmployeeEducationDetailsCreateView.as_view(),
        name="create_employee_education",
    ),
    path(
        "update/employee/education/<int:id>/",
        views.EmployeeEducationDetailsUpdateView.as_view(),
        name="update_employee_education",
    ),
    path(
        "employee/education/<int:employee_id>/",
        views.EmployeeEducationDetailsRetrieveView.as_view(),
        name="get_employee_education",
    ),
    path(
        "employee/family/",
        views.EmployeeFamilyDetailsCreateView.as_view(),
        name="create_employee_family",
    ),
    path(
        "update/employee/family/<int:id>/",
        views.EmployeeFamilyDetailsUpdateView.as_view(),
        name="update_employee_family",
    ),
    path(
        "employee/family/<int:employee_id>/",
        views.EmployeeFamilyDetailsRetrieveView.as_view(),
        name="get_employee_family",
    ),
    path(
        "emargency/contact/",
        views.EmployeeEmergencyContactCreateView.as_view(),
        name="create_emargency_contact",
    ),
    path(
        "update/emargency/contact/family/<int:id>/",
        views.EmployeeEmergencyContactUpdateView.as_view(),
        name="update_emargency_contact",
    ),
    path(
        "emargency/contact/<int:employee_id>/",
        views.EmployeeEmergencyContactRetrieveView.as_view(),
        name="get_emargency_contact",
    ),
    path(
        "employee/documents/",
        views.EmployeeDocumentsCreateView.as_view(),
        name="create_employee_documents",
    ),
    path(
        "update/employee/documents/<int:id>/",
        views.EmployeeDocumentsUpdateView.as_view(),
        name="update_employee_documents",
    ),
    path(
        "employee/documents/<int:employee_id>/",
        views.EmployeeDocumentsRetrieveView.as_view(),
        name="get_employee_documents",
    ),
    path(
        "employee/certification/",
        views.EmployeeCertificationsCreateView.as_view(),
        name="create_employee_certification",
    ),
    path(
        "update/employee/certification/<int:id>/",
        views.EmployeeCertificationsUpdateView.as_view(),
        name="update_employee_certification",
    ),
    path(
        "employee/certification/<int:employee_id>/",
        views.EmployeeCertificationsRetrieveView.as_view(),
        name="get_employee_certification",
    ),
    path(
        "employee/work/",
        views.EmployeeDocumentationWorkCreateView.as_view(),
        name="create_employee_work",
    ),
    path(
        "update/employee/work/<int:id>/",
        views.EmployeeDocumentationWorkUpdateView.as_view(),
        name="update_employee_work",
    ),
    path(
        "employee/work/<int:employee_id>/",
        views.EmployeeDocumentationWorkRetrieveView.as_view(),
        name="get_employee_work",
    ),
    
    path(
        "employee/details/",
        views.ChatBotEmployeeDetailsAPIView.as_view()
    ),
    path(
        "employee/payroll/details/",
        views.ChatboatEmployeePayrollInformation.as_view()
    ),
    path("work/history/", views.EmployeeWorkHistoryDetailsRetriveView.as_view(), name="employee_work_history_details"),
    path("last/workingday/", views.GetLastWorkingDay.as_view(), name="v2_get_last_working_day"),
    
    path("employee/experience/", views.ExperienceAPIView.as_view(), name="get_employee_experience"),
    path('employee/experience/<int:employee_id>/', views.ExperienceAPIView.as_view(), name='experience-detail'),
    path("add/new/employee/", views.OnboardingEmployeeCreateView.as_view(), name="add_employee"),
    path("add/new/employee/<int:employee_id>/", views.OnboardingEmployeeCreateView.as_view(), name="update_employee"),
    path("employee/work/docs/",views.EmployeeDocumentationWorkView.as_view(),name="create_employee_work_docs"),
    path("employee/work/docs/<int:id>/",views.EmployeeDocumentationWorkView.as_view(),name="update_employee_work_docs"),
    path("send/letter/<int:id>/", views.OfferLetterEmailApi.as_view(), name="conditional_offer_letter_sending"),
    path("update/status/", views.UpdateOfferLetterStatus.as_view(), name="update_offer_letter_status"),
    path("update/status/<int:id>/", views.UpdateOfferLetterStatus.as_view(), name="update_bgv_status"),
    path("status/choices/", views.LetterStatusChoices.as_view(), name='status_choices'),
    path("ats/col/update/", views.OfferLetterUpdateAtsAPIView.as_view(), name="conditional_offer_letter_update_ats"),
    path('smtp/setup/', views.CompanySMTPSetupAPIView.as_view(), name='company-smtp-setup-list-create'),
    path('smtp/setup/<int:company_id>/', views.CompanySMTPSetupAPIView.as_view(), name='company-smtp-setup-retrieve-update-destroy'),
    path("ats/emp/details/", views.EmployeeStatusDetailsAPIView.as_view(), name="col_bgv_al_status_info"),
    path("welcome/email/", views.CustomWelcomeMessage.as_view(), name="welcome_email"),
    path("test/email/", views.TestEmail.as_view(), name="test_email"),
    # V2 Views
    path("v2/get/employee/<int:company_id>/", v2_views.EmployeeDetailsAPIViewV2.as_view(), name="v2_get_employees"),
    path("v2/get_update/employee/<int:id>/", v2_views.EmployeeRetriveAPIViewV2.as_view(), name="v2_get_update_employee"),
    path("v2/employee/documents/<int:id>/", v2_views.EmployeeDocumentsAPIViewV2.as_view(), name="v2_get_employee_documents"),
    path("v2/employee/education/<int:id>/", v2_views.EmployeeEducationDetailsAPIViewV2.as_view(), name="v2_get_employee_education"),
    path("v2/employee/certification/<int:id>/", v2_views.EmployeeCertificationsAPIViewV2.as_view(), name="v2_get_employee_certification"),
    path("v2/employee/family/<int:id>/", v2_views.EmployeeFamilyDetailsAPIViewV2.as_view(), name="v2_get_employee_family"),
    path("v2/emargency/contact/<int:id>/", v2_views.EmployeeEmergencyContactAPIViewV2.as_view(), name="v2_get_employee_emargency_contact"),
    path("v2/employee/work/<int:id>/", v2_views.EmployeeDocumentationWorkAPIViewV2.as_view(), name="v2_get_employee_emargency_work"),
    path("v2/fetch/manager/employee/data/", v2_views.ManagerEmployeeDetailsV2.as_view(), name="v2_get_employee_emargency_manager"),
    path("v2/employee/manager/<int:id>/", v2_views.EmployeeReportingManagerAPIViewV2.as_view(), name="v2_get_employee_emargency_emp_manager"),
    
    path("v2/import/employee/", v2_views.EmployeeImportViewV2.as_view(), name="v2_import_employee"),
    path("v2/compliance/numbers/", v2_views.EmployeeComplianceNumbersAPIViewV2.as_view(), name="v2_employee_complience_numbers"),
    path("v2/employee/delete/<int:employee_id>/", v2_views.EmployeeSoftDelete.as_view(), name="v2_employee_detele"),
    path("v2/dep/employee/", v2_views.DeptEmployeeAPIView.as_view(), name="employee_department_wise"),
    path("v2/resign/", v2_views.GetResignationInfo.as_view(), name="employee_resign"),
    path("v2/company/policy/<int:id>/", v2_views.CompanyPolicyView.as_view(), name="company_policy"),
    path("v2/company/policy/", v2_views.CompanyPolicyView.as_view(), name="company_policy"),
    path("v2/company/policy/types/", v2_views.CompanyPolicyTypesDetails.as_view(), name="company_policy"),
    path("v2/company/policy/choices/", v2_views.CompanyPolicyStatusChoices.as_view(), name="company_policy_status_choices"),
    path("v2/company/policy/visibility/", v2_views.CompanyPolicyVisibilityChoices.as_view(), name="company_policy_visibility_choices"),
    path("v2/ats/permission/view/", v2_views.ATSPermissionView.as_view(), name="ats_permission_view"),
    path("v2/get/employee/preboard/<int:company_id>/", v2_views.EmployeePreBoardingDetailsAPIView.as_view(), name="v2_get_prebord_employees"),


    
    
    #Dashboard Views
    path("my/team/", dashboard_views.EmployeeTeamDetailsView.as_view(), name="my_team_details"),
    path("my/birthdate/", dashboard_views.BirthdayBuddies.as_view(), name="my_birthdate_details"),
    path("service/year/", dashboard_views.ServiceYear.as_view(), name="service_year"),
    path("manager/dep/", dashboard_views.ManagerDepartments.as_view(), name="manager_dep"),
    path("employee/hierarchy/", dashboard_views.OrganizationHierarchy.as_view(), name="employee_hierarchy"),
    path("ctc/history", views.CTCHistoryApi.as_view(), name="ctc-history"),
    
]
