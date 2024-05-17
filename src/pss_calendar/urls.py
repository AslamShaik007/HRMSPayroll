from django.urls import path

from pss_calendar import views, v2_views, dashboard_views


urlpatterns = [
    path(
        "holiday/",
        views.CompanyHolidaysCreateView.as_view(),
        name="create_holiday",
    ),
    path(
        "update/holiday/<int:id>/",
        views.CompanyHolidaysUpdateView.as_view(),
        name="update_holiday",
    ),
    path(
        "holiday/<int:company_id>/",
        views.CompanyHolidaysRetrieveView.as_view(),
        name="get_holiday",
    ),
    path("import/holiday/", views.HolidaysImportView.as_view(), name="import_holiday"),
    path(
        "event/",
        views.CompanyEventsCreateView.as_view(),
        name="create_event",
    ),
    path(
        "update/event/<int:id>/",
        views.CompanyEventsUpdateView.as_view(),
        name="update_event",
    ),
    path(
        "event/<int:company_id>/",
        views.CompanyEventsRetrieveView.as_view(),
        name="get_event",
    ),
    
    
    # v2 urls
    path(
        "v2/event/<int:company_id>/",
        v2_views.CompanyEventsRetrieveViewV2.as_view(),
        name="v2_get_events",
    ),
    
    path(
        "v2/holiday/<int:company_id>/",
        v2_views.CompanyHolidaysRetrieveViewV2.as_view(),
        name="v2_get_holiday",
    ),
    
    
    #dashboard APIs
    path("db/holiday/",dashboard_views.CompanyHolidaysDashboardView.as_view(),name="get_holiday_dashboard"),
    path("db/event/",dashboard_views.CompanyEventsDashboardView.as_view(),name="get_event_dashboard"),
]
