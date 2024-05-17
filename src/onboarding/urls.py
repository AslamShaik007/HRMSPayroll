from django.urls import path
from .views import OnBoardingModuleView, OnBoardingSubModuleView, OnBoardingTaskView, TemplateView, AssignTemplateView, TaskTypeChoices, OnboardHierarchy


urlpatterns = [
    path('template/', TemplateView.as_view(), name='get_template'),
    path('template/<int:id>/', OnBoardingTaskView.as_view(), name='update_template'),
    path('assign/template/', AssignTemplateView.as_view(), name='assign_template'),
    path('modules/', OnBoardingModuleView.as_view(), name='get_on_boarding_modules'),
    path('modules/<int:id>/', OnBoardingModuleView.as_view(), name='update_on_boarding_modules') ,
    path('sub/modules/', OnBoardingSubModuleView.as_view(), name='get_on_boarding_modules'),
    path('sub/modules/<int:id>/', OnBoardingSubModuleView.as_view(), name='update_on_boarding_modules'),
    path('sub/modules/task/', OnBoardingTaskView.as_view(), name='get_on_boarding_modules_task'),
    path('sub/modules/task/<int:id>/', OnBoardingTaskView.as_view(), name='update_on_boarding_modules_tasks') ,
    path('task/types/', TaskTypeChoices.as_view(), name='task_types'),
    path("hierarchy/", OnboardHierarchy.as_view(), name="onboard_hierarchy"),
]
