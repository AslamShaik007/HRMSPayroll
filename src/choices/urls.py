from django.urls import path

from choices import views


urlpatterns = [
    path(
        "retrieve/choices/",
        views.ListChoicesView.as_view(),
        name="get_choices",
    ),
]
