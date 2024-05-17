from django.urls import path

from .views import TicketApiView, CentralTicketUpdateAPIView

urlpatterns = [
    path('ticketapi/', TicketApiView.as_view(), name='ticketapi'),
    path('ticketapi/listing-tickets/', TicketApiView.as_view(), name='listing_ticketapi'),
    path('ticketapi/create/', TicketApiView.as_view(), name='ticketapi_create'),
    path('ticketapi/auto/update/', CentralTicketUpdateAPIView.as_view(), name='ticketapi_auto_update'),
]
