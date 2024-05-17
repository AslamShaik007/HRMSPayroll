from django.urls import path

from .views import BillingAPIView

app_name = 'billing'

urlpatterns = [
    path('view/', BillingAPIView.as_view(), name='view'),
    path('auto/create/', BillingAPIView.as_view(), name='auto_create'),
    path('auto/update/', BillingAPIView.as_view(), name='auto_update'),
]


