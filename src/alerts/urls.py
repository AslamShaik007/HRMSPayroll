from django.urls import path


from alerts.views import AlertApiView, NotificationAlertApiView


urlpatterns = [
    path('', AlertApiView.as_view()),
    path('notification/', NotificationAlertApiView.as_view())
]
