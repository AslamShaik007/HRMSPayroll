from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path

from rest_framework_simplejwt.views import TokenRefreshView

from HRMSApp import views
from HRMSApp.views import (
    CompanyDetailsRetrieveUpdateView,
    ResendActivationLinkAPIView,
    RoleCreateView,
    RoleRetrieveUpdateView,
    RoleRetrieveView,
    SendResetPasswordEmailView,
    TOTPRegisterView,
    TOTPVerifyView,
    UserLoginView,
    UserRegistrationView,
    RolesFetchApiView, 
    PermissionsFetchApiView,
    GradeApiView,
    ActiveEmployeesAPIView, CompanyCustomizedConfigurationsAPIView,
)
from .multitenant_views import FetchMultitenantCompaniesAPIView , EnableMultiTenant , CreateMultitenantCompanyAPIView


urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("totp/register", TOTPRegisterView.as_view(), name="totp-register"),
    re_path(
        r"^totp/token/(?P<token>[0-9]{6})/$",
        TOTPVerifyView.as_view(),
        name="totp-token",
    ),
    path("", UserRegistrationView.as_view(), name="user"),
    # path("features/add", features_add.as_view(), name="features_add"), # By Uday
    path(
        "register/", UserRegistrationView.as_view(), name="register"
    ),  # User registration API view
    path(
        "<int:id>/update/",
        CompanyDetailsRetrieveUpdateView.as_view(),
        name="update_company",
    ),
    path(
        "<int:id>/",
        CompanyDetailsRetrieveUpdateView.as_view(),
        name="get_company",
    ),
    path(
        "roles/",
        RoleCreateView.as_view(),
        name="create_role",
    ),
    path(
        "roles/fetch/",
        RolesFetchApiView().as_view(),
        name="fetch_roles",
    ),
    path(
        "permissions/details/",
        PermissionsFetchApiView().as_view(),
        name="permissions_details",
    ),
    path(
        "roles/<int:id>/",
        RoleRetrieveUpdateView.as_view(),
        name="update_role",
    ),
    path(
        "company/roles/<int:company_id>/",
        RoleRetrieveView.as_view(),
        name="retrieve_role",
    ),
    path(
        "send-reset-password-email/",
        SendResetPasswordEmailView.as_view(),
        name="send_reset_password_email",
    ),
    path(
        "update/password/",
        views.UpdatePasswordView.as_view(),
        name="update-password",
    ),
    path(
        "change/password/",
        views.UserChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "resend-activation-link/",
        ResendActivationLinkAPIView.as_view(),
        name="resend_activation_link",
    ),
    path(
        "validate/phone/sendotp",
        views.ValidatePhoneSendOTP.as_view(),
        name="validate_phone",
    ),
    path("validate/otp/", views.ValidatePhoneOTP.as_view(), name="validate_otp"),
    path(
        "validate/email/phone/sendotp/",
        views.ValidateEmailPhoneSendOTP.as_view(),
        name="validate_emailphone_sendotp",
    ),
    path(
        "validate/email/phoneotp/",
        views.ValidateEmailPhoneOTP.as_view(),
        name="validate_emailphoneotp",
    ),
    path(
        "delete/attachment/<int:id>/",
        views.AttachmentDeleteView.as_view(),
        name="delete_attachment",
    ),
    path(
        "pincode/adress/",
        views.PincodeToAdressAPIView.as_view(),
        name="get_adress"
    ),
    path(
        "fetch/bankdetails/",
        views.FetchBankDetailes.as_view(),
        name = "get_bank_details",
    ),
    path("grade/fetch/", GradeApiView.as_view(), name="grade_fetch"),
    path("grade/create/", GradeApiView.as_view(), name="grade_create"),
    path("grade/update/", GradeApiView.as_view(), name="grade_update"),
    path("active/employees/", ActiveEmployeesAPIView.as_view(), name="active_employees"),
    # path(
    #     "filter_phone/", MobileNumbrValidationAPIView.as_view(), name="filter_phone"
    # ),  # User model Mobile number existed or not
    # path(
    #     "filter_email/", EmailValidationAPIView.as_view(), name="filter_email"
    # ),  # User model Mobile number existed or not
    path(
        "validate/sentotp/<int:otp>/",
        views.ValidateOTP.as_view(),
        name="validate_sentotp",
    ),
    path(
        "login/sendotp/",
        views.LoginOTP.as_view(),
        name="login_sendotp",
    ),
    path('get_update_configurations/', CompanyCustomizedConfigurationsAPIView.as_view()),
    path('list-multi-tenant-companies/', FetchMultitenantCompaniesAPIView.as_view()),
    path('enable-multitenant/<int:pk>/', EnableMultiTenant.as_view()),
    path('create-multitenant-company/', CreateMultitenantCompanyAPIView.as_view())
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
