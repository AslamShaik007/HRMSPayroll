
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from .docs.generators import OpenAPISchemaGenerator
from .docs.swagger_intro import DESCRIPTION

from .db_setup import DBCreation, CentralCompanyCreationAPIView, CreateCompany

app_urls = [
    path("admin/", admin.site.urls),
    path('api/roles/', include("roles.urls")),
    path("api/user/", include("HRMSApp.urls")),
    path("api/company/", include("company_profile.urls")),
    path("api/directory/", include("directory.urls")),
    path("api/choices/", include("choices.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/pss_calendar/", include("pss_calendar.urls")),
    path("api/leave/", include("leave.urls")),
    path("api/attendance/", include("attendance.urls")),
    path("api/performance_management/", include("performance_management.urls")),
    path("api/investment_declaration/", include("investment_declaration.urls")),
    path("api/payroll/", include("payroll.api_urls")),
    path("payroll/", include("payroll.urls")),    
    path('support/', include(("support.urls", "support"), namespace='support')),
    path('billing/', include(("billing.urls", "billing"), namespace='billing')),
    path('central/db_setup/', CreateCompany.as_view()),
    path('central/company_setup/', CentralCompanyCreationAPIView.as_view()),
    path('api/aiml/', include("aiml_app.urls")),
    path('api/alerts/', include("alerts.urls")),
    path('api/onboarding/', include("onboarding.urls")),
]


schema_view = get_schema_view(
    openapi.Info(
        title="HRMS Software API",
        default_version="v1",
        description=DESCRIPTION,
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@pss.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    generator_class=OpenAPISchemaGenerator,
    patterns=app_urls,
)

external_urls = [
    # re_path(
    #     r"^swagger(?P<format>\.json|\.yaml)$",
    #     schema_view.without_ui(cache_timeout=0),
    #     name="schema-json",
    # ),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # re_path(
    #     r"^docs/$", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    # ),
    # OpenAPI schema
    # path(
    #     "docs/",
    #     schema_view.with_ui("redoc", cache_timeout=0),
    #     name="openapi-schema",
    # ),
]

urlpatterns = external_urls + app_urls
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
