import django_filters
from django.db.models import Q
from directory.models import Employee


class ActiveEmployeeFilter(django_filters.FilterSet):
    # company__company_name = django_filters.CharFilter()    
    
    dept_id = django_filters.CharFilter(field_name="work_details__department_id")

    emp_id = django_filters.CharFilter(field_name="id")

    class Meta:
        model = Employee
        fields = ["dept_id", "emp_id"]

    # def filter_by_name(self, queryset, name, value):
    #     return queryset.filter(
    #         Q(first_name__icontains=value)
    #         | Q(middle_name__icontains=value)
    #         | Q(last_name__icontains=value)
    #     )

    def my_custom_filter(self, queryset, name, value):        
        if value == "All":            
           value = True 

        return queryset.filter(**{
                name: value,
            })   