from django.urls import path

from investment_declaration import views
from investment_declaration import v2_views
from investment_declaration import dashboard_views
# from investment_declaration.views import InvestmentDeclarationOnlyStatusViewSet


urlpatterns = [
    path(
        "declarationforms/types/",
        views.FormChoicesRetriveApiView.as_view(),
        name="basic_declaratin_formstype",
    ),
    path(
        "create/declarations/",
        views.InvestmentDeclarationCreateView.as_view(),
        name="generate_investment_declaratins",
    ),
    path(
        "declarations/update/<int:id>/",
        views.InvestmentDeclarationUpdateView.as_view(),
        name="update_investment_declaratins",
    ),
    path(
        "retrieve/declarations/",
        views.InvestmentDeclarationRetriveAPIView.as_view(),
        name="retrive_investment_declarations",
    ),
    path(
        "update/declarations/<int:id>/",
        views.InvestmentDeclarationUpdateView.as_view(),
        name="update_investment_declaration",
    ),
    path(
        "status/update/<int:id>/",
        views.InvestmentDeclarationStatusUpdateView.as_view(),
        name="investment_declaratins_status_update",
    ),
    # path(
    #     "create/declaration/attachments/",
    #     views.AttachmentListCreateView.as_view(),
    #     name="investment_declaration_attachments",
    # ),
    path(
        "delete/declaration/attachments/<int:id>/",
        views.AttachmentDeleteView.as_view(),
        name="delete_investment_declaration_attachments",
    ),
    path("employee/reimbursement/", views.EmployeeReimbursementAPIView.as_view(), name="employee_reimbursement"),
    path("update/reimbursement/<int:id>/", views.EmployeeReimbursementAPIView.as_view(), name="update_reimbursement"),
    path("v2/retrieve/declarations/",v2_views.InvestmentDeclarationGetAPIViewV2.as_view(),name = "get_declarations"),
    path("v2/retrieve/employee/sal/",v2_views.SavingDeclarationSalDOJAPIView.as_view(),name = "get_employee_sal"),
    path("v2/employee/reimbursement/", v2_views.EmployeeReimbursementAPIViewV2.as_view(), name="employee_reimbursement_v2"),
    path("v2/reimbursement/requests/", dashboard_views.AdminReimbursmentRequestsCountAPIViewV2.as_view(), name="reimbursement_requests_v2"),
    path("employeePreviousSalaryDetails", views.EmployeePreviousSalaryDetails.as_view(), name='employee-previous-salary-details'),
    path("regimeselect", views.RegimeSelect.as_view()),
    path("investmentdeclaration-hra",views.DeclarationHra.as_view(),name= "get-hra"),
]


