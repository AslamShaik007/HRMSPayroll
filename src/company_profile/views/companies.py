import traceback
import logging
from django.db.models import Q, Case,When, Value, BooleanField, F
from django.contrib.postgres.aggregates import ArrayAgg

from rest_framework.response import Response
from rest_framework import permissions, response, status
from rest_framework.generics import (
    CreateAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    UpdateAPIView,
    RetrieveUpdateDestroyAPIView
)

from ..models import (
    Announcements,
    AuditorDetails,
    AuditorTypes,
    BankAccountTypes,
    BankDetails,
    CompanyDetails,
    CompanyDirectorDetails,
    CompanyGrades,
    CustomAddressDetails,
    Departments,
    Designations,
    EntityTypes,
    Policies,
    SecretaryDetails,
    StatutoryDetails,
    SubDepartments
)
from ..serializers.companies import (
    BankAccountTypesDetailSerializer,
    BankAccountTypesSerializer,
    ComapanyEntityDetailSerializer,
    ComapanyEntitySerializer,
    CompanyAnnouncementDetailSerializer,
    CompanyAnnouncementSerializer,
    CompanyAuditorDetailSerializer,
    CompanyAuditorSerializer,
    CompanyAuditortypeDetailSerializer,
    CompanyAuditortypeSerializer,
    CompanyBankDetailSerializer,
    CompanyBankSerializer,
    CompanyDepartmentDetailSerializer,
    CompanyDepartmentSerializer,
    CompanyDesignationDetailSerializer,
    CompanyDesignationSerializer,
    CompanyDetailSerializer,
    CompanyDirectorDetailSerializer,
    CompanyDirectorSerializer,
    CompanyGradesDetailSerializer,
    CompanyGradesSerializer,
    CompanyPoliciesDetailSerializer,
    CompanyPoliciesSerializer,
    CompanySecretaryDetailSerializer,
    CompanySecretarySerializer,
    CompanySerializer,
    CompanyStatutoryDetailSerializer,
    CompanyStatutorySerializer,
    CustomAddressDetailSerializer,
    CustomAddressSerializer,
)

from core.utils import timezone_now, success_response, error_response, TimestampToStrDateTime, TimestampToIST, post_department_ats, update_department_ats
from django.conf import settings
from HRMSProject.multitenant_setup import MultitenantSetup



logger = logging.getLogger('django')
class CompanyDetailesCreateView(ListCreateAPIView):
    """
    View to get or create CompanyDetailes

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySerializer
    detailed_serializer_class = CompanyDetailSerializer
    queryset = CompanyDetails.objects.all()


class CompanyDetailesRetrieveUpateView(RetrieveUpdateAPIView):
    """
    View to update CompanyDetailes

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySerializer
    detailed_serializer_class = CompanyDetailSerializer
    lookup_field = "id"
    queryset = CompanyDetails.objects.all()
    
    
    def get_queryset(self):
        print("coming here1 ")
        return super().get_queryset()
    
    def get(self, request, *args, **kwargs):
        try:
            print("coming here")
            MultitenantSetup().create_to_connection(request)
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(list(queryset), many=True)
            MultitenantSetup().go_to_old_connection(request)
            return Response(serializer.data)
        except Exception as e:
            print("exception", e)
            MultitenantSetup().go_to_old_connection(request)
            return Response([])
    
    
    
    
    def patch(self, request, *args, **kwargs):
        data = request.data
        role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        if role == "ADMIN":
            if data.get("brand_name"):
                request.data["is_brand_name_updated"] = True 
            return self.partial_update(request, *args, **kwargs)
        else:
            return response.Response(
                {
                    'message': 'Only Admin can update the company details.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

class CompanyDepartmentCreateView(CreateAPIView):
    """
    View to get or create Departments

    AJAY, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDepartmentSerializer
    detailed_serializer_class = CompanyDepartmentDetailSerializer
    queryset = Departments.objects.all()
    
    def get_queryset(self):
        MultitenantSetup().create_to_connection(request)
        queryset = Departments.objects.all()
        MultitenantSetup().go_to_old_connection(request)
        return super().get_queryset()
    
    def post(self, request, *args, **kwargs):
        data = request.data
        department_qs = Departments.objects.filter(
            company_id=data.get('company'),
            name__icontains=data.get('name').strip()
        )
        if department_qs.exists():
            return response.Response(
                {
                    'message': 'Department with this name already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        sub_depatments = data.get('sub_departments',[])    
        sub_deps = [obj for obj in sub_depatments if obj.get('name') and ('id' in obj or not obj.get('is_deleted'))]
        data['sub_departments'] = sub_deps
        request._full_data = data
        depratments_post = self.create(request, *args, **kwargs)
        # adding data into ATS DB
        payload = {'dept_name': {data.get('name')},
                    'company_id':data.get('company')}
        post_department_ats(payload)
        return depratments_post

class CompanyDepartmentUpateView(RetrieveUpdateDestroyAPIView):
    """
    View to update Company Department

    AJAY, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDepartmentSerializer
    detailed_serializer_class = CompanyDepartmentDetailSerializer
    lookup_field = "id"
    queryset = Departments.objects.filter()
    
    def put(self, request, *args, **kwargs):
        data = request.data
        department_qs = Departments.objects.filter(
            company_id=data.get('company'),
            name=data.get('name')
        ).exclude(id=kwargs.get('id'))
        if department_qs.exists():
            return response.Response(
                {
                    'message': 'Department with this name already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        sub_depatments = data.get('sub_departments',[])    
        sub_deps = [obj for obj in sub_depatments if obj.get('name') and ('id' in obj or not obj.get('is_deleted'))]
        data['sub_departments'] = sub_deps
        if not sub_depatments:
            SubDepartments.objects.filter(department_id=kwargs.get('id')).delete()
        request._full_data = data
        old_dept_name = self.queryset.filter(id=kwargs.get('id')).first().name
        dep_data_update = self.update(request, *args, **kwargs)
        #update dep data ATS
        payload = {
            "company_id":data.get('company'),
            "dept_id":kwargs.get('id'),
            "dept_name":data.get('name'),
            "old_dept_name":old_dept_name
        }
        update_department_ats(payload)
        return dep_data_update
        

    def delete(self, request, id):
        department_qs = Departments.objects.filter(id=id)
        if not department_qs.exists():
            return response.Response(
                {
                    'message': "Department Does not exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        department = department_qs.first()
        if department.employeeworkdetails_set.exists():
            return response.Response(
                {
                    'message': 'Employees Exist in this department'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        department.delete()
        return response.Response(
            {
                'message': 'Department Deleted Successfully'
            },
            status=status.HTTP_200_OK
        )

class CompanyDepartmentRetrieveView(ListAPIView):
    """
    View to retrieve company Department

    AJAY, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDepartmentSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Departments.objects.all().order_by("-id")

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)
    
    def list(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(self.request)
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(list(queryset), many=True)
            MultitenantSetup().go_to_old_connection(self.request)
            return Response(serializer.data)
        except Exception as e:
            MultitenantSetup().go_to_old_connection(self.request)
            return Response([])

    


class CustomAddressDetailsCreateView(CreateAPIView):
    """
    View to create or retrieve Custom Adderess

    AJAY, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomAddressSerializer
    detailed_serializer_class = CustomAddressDetailSerializer
    queryset = CustomAddressDetails.objects.all()
    
    def post(self, request, *args, **kwargs):
        data = request.data
        
        company_id = data.get('company')
        address_line1 = data.get('address_line1')
        address_line2 = data.get('address_line2')
        address_title = data.get('address_title')
        address_qs = CompanyDetails.objects.filter(
            Q(id=company_id,is_deleted=False,customaddressdetails__is_deleted=False) & 
                (Q(customaddressdetails__address_title__icontains=address_title) &
                Q(customaddressdetails__address_line1__icontains=address_line1) &
                Q(customaddressdetails__address_line2__icontains=address_line2) &(
            (Q(corporate_adress_line1__icontains=address_line1) |
            Q(corporate_adress_line2__icontains=address_line2) &
            Q(registered_adress_line1__icontains=address_line1) |
            Q(registered_adress_line2__icontains=address_line2))))
            ).annotate(
            cc_address = Case(
                When(Q(corporate_adress_line1=address_line1), then=True), output_field=BooleanField(),
                default=Value(False)),
            title = Case(
                When(Q(customaddressdetails__address_title=address_title), then=True), output_field=BooleanField(),
                default=Value(False))
        ).values('cc_address','title')
        
        if address_qs.exists():
            message = ''
            result_obj = list(address_qs)[0]
            if result_obj['title'] :
                message = 'Address Title Already Exists'
            else:
                message = 'Address is Already Exists'
            return response.Response(
                {
                    'message': message
                },
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        if CustomAddressDetails.objects.filter(
                                    Q(is_deleted=False) &
                                    (Q(address_title__icontains=address_title.strip()) &
                                    Q(address_line1__icontains=address_line1.strip()) &
                                    Q(address_line2__icontains=address_line2.strip()) 
                                    )
                                ).exclude(id=kwargs.get('id')
                            ).exists():
            return response.Response(
                        {
                            'message': 'Address Is Already Exists'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        return self.create(request, *args, **kwargs)


class CustomAddressDetailsUpdateView(UpdateAPIView):
    """
    View to update Custom Adderess

    AJAY, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomAddressSerializer
    detailed_serializer_class = CustomAddressDetailSerializer
    lookup_field = "id"
    queryset = CustomAddressDetails.objects.all()

    def patch(self, request, *args, **kwargs):
        data = request.data
        
        if data.get('is_deleted'):
            CustomAddressDetails.objects.get(id=kwargs.get('id')).delete()
            return response.Response(
                {
                    'message': 'Custom Address Deleted Successfully.'
                },
                status=status.HTTP_200_OK
            ) 
        
        company_id = data.get('company','')
        address_line1 = data.get('address_line1','')
        address_line2 = data.get('address_line2','')
        address_title = data.get('address_title','')
        if CompanyDetails.objects.filter(
            Q(id=company_id,is_deleted=False,customaddressdetails__is_deleted=False) & 
            (Q(corporate_adress_line1__icontains=address_line1) &
            Q(corporate_adress_line2__icontains=address_line2) |
            Q(registered_adress_line1__icontains=address_line1) &
            Q(registered_adress_line2__icontains=address_line2)
            )).exists():
            return response.Response(
                {
                    'message': 'Address Is Already Exists' 
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if CustomAddressDetails.objects.filter(
                                    Q(is_deleted=False) &
                                    (Q(address_title__icontains=address_title) &
                                    Q(address_line1__icontains=address_line1) &
                                    Q(address_line2__icontains=address_line2) 
                                    )
                                ).exclude(id=kwargs.get('id')
                            ).exists():
            return response.Response(
                        {
                            'message': 'Address Is Already Exists'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
        return self.partial_update(request, *args, **kwargs)
    

class CustomAddressDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Custom Address

    AJAY, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomAddressDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = CustomAddressDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs).order_by('-id')
    
    
    def get(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(request)
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(list(queryset), many=True)
            MultitenantSetup().go_to_old_connection(request)
            return Response(serializer.data)
        except Exception as e:
            MultitenantSetup().go_to_old_connection(request)
            return Response([])


class CompanyDesignationsCreateView(CreateAPIView):
    """
    View to create or retrieve Company Designations

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDesignationSerializer
    detailed_serializer_class = CompanyDesignationDetailSerializer
    queryset = Designations.objects.all()

    def post(self, request, *args, **kwargs):
        data = request.data
        designation_qs = Designations.objects.filter(
            company_id=data.get('company'),
            name=data.get('name')
        )
        if designation_qs.exists():
            return response.Response(
                {
                    'message': 'Designation with this name already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.create(request, *args, **kwargs)


class CompanyDesignationsUpdateView(RetrieveUpdateDestroyAPIView):
    """
    View to update or retrieve Company Designations

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDesignationSerializer
    detailed_serializer_class = CompanyDesignationDetailSerializer
    lookup_field = "id"
    queryset = Designations.objects.all()

    def patch(self, request, *args, **kwargs):
        data = request.data
        designation_qs = Designations.objects.filter(
            company_id=data.get('company'),
            name=data.get('name')
        ).exclude(id=kwargs.get('id'))
        if designation_qs.exists():
            return response.Response(
                {
                    'message': 'Designation with this name already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.update(request, *args, **kwargs)

    def delete(self, request, id):
        designation_qs = Designations.objects.filter(id=id)
        if not designation_qs.exists():
            return response.Response(
                {
                    'message': "Designation Does not exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        designation = designation_qs.first()
        if designation.employeeworkdetails_set.exists():
            return response.Response(
                {
                    'message': 'Employees Exist in this designation'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        designation.delete()
        return response.Response(
            {
                'message': 'Designation Deleted Successfully'
            },
            status=status.HTTP_200_OK
        )

class CompanyDesignationsRetrieveView(ListAPIView):
    """
    View to retrieve Custom Address

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDesignationSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Designations.objects.all().order_by("-id")

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        query = queryset.filter(**filter_kwargs)
        return query
    
    
    def list(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(self.request)
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(list(queryset), many=True)
            # data = serializer.data
            MultitenantSetup().go_to_old_connection(self.request)
            return Response(serializer.data)
        except Exception:
            MultitenantSetup().go_to_old_connection(self.request)
            return Response([])



class CompanyGradesCreateView(CreateAPIView):
    """
    View to create or retrieve Company Grades

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyGradesSerializer
    detailed_serializer_class = CompanyGradesDetailSerializer
    queryset = CompanyGrades.objects.all()

    def post(self, request, *args, **kwargs):
        data = request.data
        grades_qs = CompanyGrades.objects.filter(
            company_id=data.get('company'),
            grade=data.get('grade')
        )
        if grades_qs.exists():
            return response.Response(
                {
                    'message': 'Grade with this name already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.create(request, *args, **kwargs)


class CompanyGradesUpdateView(RetrieveUpdateDestroyAPIView):
    """
    View to update or retrieve Company Grades

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyGradesSerializer
    detailed_serializer_class = CompanyGradesDetailSerializer
    lookup_field = "id"
    queryset = CompanyGrades.objects.all()

    def patch(self, request, *args, **kwargs):
        data = request.data
        grade_qs = CompanyGrades.objects.filter(
            company_id=data.get('company'),
            grade=data.get('grade')
        ).exclude(id=kwargs.get('id'))
        if grade_qs.exists():
            return response.Response(
                {
                    'message': 'Grade with this name already exists'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.update(request, *args, **kwargs)

    def delete(self, request, id):
        grade_qs = CompanyGrades.objects.filter(id=id)
        if not grade_qs.exists():
            return response.Response(
                {
                    'message': "Grade Does not exist"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        grade = grade_qs.first()
        if grade.employeeworkdetails_set.exists():
            return response.Response(
                {
                    'message': 'Employees Exist in this Grade'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        grade.delete()
        return response.Response(
            {
                'message': 'Grade Deleted Successfully'
            },
            status=status.HTTP_200_OK
        )


class CompanyGradesRetrieveView(ListAPIView):
    """
    View to retrieve Grades

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyGradesSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = CompanyGrades.objects.all().order_by("-id")

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class CompanyAnnouncementCreateView(CreateAPIView):
    """
    View to create or retrieve Company Announcement

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyAnnouncementSerializer
    detailed_serializer_class = CompanyAnnouncementDetailSerializer
    queryset = Announcements.objects.all()
    # print(queryset)
    def post(self,request):
        try:
            request_data = request.data
            departments = request_data.get("departments")
            serializer = self.get_serializer(data=request_data)
            if serializer.is_valid() :
                self.perform_create(serializer)
                if departments:
                    serializer.instance.departments.add(*departments.split(','))
            else:
                Error  = ''
                for index, error in enumerate(serializer.errors):
                    Error  += str(serializer.errors.get(error)).split("[ErrorDetail(string='")[1].split("', code=")[0]
                response = error_response(Error,'something went wrong', 400)
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
            
            response = success_response(serializer.data, 'announcements created successfully', 200)
            return Response(response,status=status.HTTP_201_CREATED)
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

class CompanyAnnouncementUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Announcement

    SURESH, 28.12.2022
    """
    model = Announcements
    serializer_class = CompanyAnnouncementSerializer

    def patch(self, request, *args, **kwargs):
        try:
            request_data = request.data
            departments = request_data.get("departments")
            if request_data.get('annoucement_image','') == "null":
                request_data['annoucement_image'] = None
            obj = self.model.objects.get(id=self.kwargs.get('id'))
            serializer = self.get_serializer(obj,data=request_data,partial=True,context={'obj_id':self.kwargs.get('id')})
            if serializer.is_valid() :
                self.perform_update(serializer)
                serializer.instance.departments.clear()
                if departments:
                    serializer.instance.departments.add(*departments.split(','))
            else:
                Error  = ''
                for index, error in enumerate(serializer.errors):
                    Error  += str(serializer.errors.get(error)).split("[ErrorDetail(string='")[1].split("', code=")[0]
                response = error_response(Error,'something went wrong', 400)
                return Response(response, status=status.HTTP_400_BAD_REQUEST)
            response = success_response(serializer.data, 'announcements updated successfully', 200)
            return Response(response,status=status.HTTP_201_CREATED)
        except Exception as e:
            response = error_response(f'{str(e)} Error: {traceback.format_exc()}', 400)
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

class CompanyAnnouncementRetrieveView(ListAPIView):
    """
    View to retrieve Announcements

    SURESH, 05.01.2023
    """
    model = Announcements
    def get(self, request, *args, **kwargs):
        today = timezone_now().date()
        logger.warning(f"Announcements Retrive Api for {today}")
        q_filter = Q(company_id=self.kwargs['company_id'], is_deleted=False, announcement_type='ANNOUNCEMENT')
        query = self.model.objects.filter(q_filter).annotate(
            status=Case(
                When(post_date__gt=today, then=Value("Upcoming")),
                When(expired_date__lt=today, then=Value("Expired")),
                When(post_date__lte=today, expired_date__gte=today, then=Value("Published")),
                default=Value('None')
            ),
            department = ArrayAgg('departments__id', filter = Q(departments__isnull = False)),
            published_by = F('created_by__username'),
            created_at_date = TimestampToStrDateTime(TimestampToIST(F('created_at'), settings.TIME_ZONE)),
            updated_at_date = TimestampToStrDateTime(TimestampToIST(F('updated_at'), settings.TIME_ZONE))
            ).order_by('-id').values()
        # response = success_response(queryset, 'announcements retrived successfully', 200)
        return Response(query,status=status.HTTP_200_OK)
class CompanyPoliciesCreateView(CreateAPIView):
    """
    View to create or retrieve Company Policies

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyPoliciesSerializer
    detailed_serializer_class = CompanyPoliciesDetailSerializer
    queryset = Policies.objects.all()


class CompanyPoliciesUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Policies

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyPoliciesSerializer
    detailed_serializer_class = CompanyPoliciesDetailSerializer
    lookup_field = "id"
    queryset = Policies.objects.all()


class CompanyPoliciesRetrieveView(ListAPIView):
    """
    View to retrieve Policies

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyPoliciesSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = Policies.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


# class CompanyEntityTypeCreateView(CreateAPIView):
#     serializer_class = ComapanyEntitySerializer
#     detailed_serializer_class = ComapanyEntityDetailSerializer
#     queryset = EntityTypes.objects.all()


class CompanyEntityRetrieveView(ListAPIView):
    """
    DroupDown retrieve Company Entity Type

    SURESH, 12.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ComapanyEntitySerializer
    detailed_serializer_class = ComapanyEntityDetailSerializer
    lookup_field = "id"
    queryset = EntityTypes.objects.all()


class CompanyStatutoryDetailsUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Statutory

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyStatutorySerializer
    detailed_serializer_class = CompanyStatutoryDetailSerializer
    lookup_field = "company_id"
    queryset = StatutoryDetails.objects.all()

    def put(self, request, *args, **kwargs):
        role = request.user.employee_details.first().roles.values_list('name', flat=True).first()
        if role == "ADMIN":
            return self.partial_update(request, *args, **kwargs)
        else:
            return response.Response(
                {
                    'message': 'Only Admin can update the company details.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


class CompanyStatutoryDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Statutory Details

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyStatutoryDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = StatutoryDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class CompanyDirectorDetailsCreateView(CreateAPIView):
    """
    View to create or retrieve Company Director

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDirectorSerializer
    detailed_serializer_class = CompanyDirectorDetailSerializer
    queryset = CompanyDirectorDetails.objects.all()
    
    def post(self, request, *args, **kwargs):
        data = request.data
        lookup =  Q(company_id=data.get('company'), 
                    is_deleted=False) & (Q(director_mail_id=data.get('director_mail_id')) |
                                                                    Q(director_phone=data.get('director_phone')) | Q(din_number=data.get('din_number')))
        qs = CompanyDirectorDetails.objects.filter(lookup)
        if qs.exists():
            return response.Response(
                {
                    "message": "Director With Phone Or Email Or Din Number already exists"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # sec_qs = CompanyDirectorDetails.objects.annotate(
        #     sec_email=Subquery(
        #         SecretaryDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(secretary_email=data.get('director_mail_id')) | Q(secretary_phone=data.get('director_phone')))
        #         ).values('secretary_email')[:1]
        #     )
        # ).filter(sec_email__isnull=False)
        # if sec_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Secratry With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # auditor_qs = CompanyDirectorDetails.objects.annotate(
        #     auditor_email=Subquery(
        #         AuditorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(auditor_email=data.get('director_mail_id')) | Q(auditor_phone=data.get('director_phone')))
        #         ).values('auditor_email')[:1]
        #     )
        # ).filter(auditor_email__isnull=False)
        # if auditor_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Auditor With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        return self.create(request, *args, **kwargs)


class CompanyDirectorDetailsUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Director

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDirectorSerializer
    detailed_serializer_class = CompanyDirectorDetailSerializer
    lookup_field = "id"
    queryset = CompanyDirectorDetails.objects.all()

    def put(self, request, *args, **kwargs):
        data = request.data
        lookup =  Q(company_id=data.get('company'), 
                    is_deleted=False) & (Q(director_mail_id=data.get('director_mail_id')) |
                                                                    Q(director_phone=data.get('director_phone')) | Q(din_number=data.get('din_number')))
        qs = CompanyDirectorDetails.objects.filter(lookup).exclude(id=kwargs.get('id'))
        if qs.exists():
            return response.Response(
                {
                    "message": "Director With Phone Or Email Or Din Number already exists"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # sec_qs = CompanyDirectorDetails.objects.annotate(
        #     sec_email=Subquery(
        #         SecretaryDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(secretary_email=data.get('director_mail_id')) | Q(secretary_phone=data.get('director_phone')))
        #         ).values('secretary_email')[:1]
        #     )
        # ).filter(sec_email__isnull=False)
        # if sec_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Secratry With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # auditor_qs = CompanyDirectorDetails.objects.annotate(
        #     auditor_email=Subquery(
        #         AuditorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(auditor_email=data.get('director_mail_id')) | Q(auditor_phone=data.get('director_phone')))
        #         ).values('auditor_email')[:1]
        #     )
        # ).filter(auditor_email__isnull=False)
        # if auditor_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Auditor With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        return self.update(request, *args, **kwargs)

class CompanyDirectorDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Statutory Details

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyDirectorSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = CompanyDirectorDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


# class CompanyAuditorCreateView(CreateAPIView):
#     serializer_class = CompanyAuditortypeSerializer
#     detailed_serializer_class = CompanyAuditortypeDetailSerializer
#     queryset = AuditorTypes.objects.all()


class ComapanyAuditortypeRetrieveView(ListAPIView):
    """
    DroupDown retrieve Company AuditorType

    SURESH, 28.12.2022
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyAuditortypeSerializer
    detailed_serializer_class = CompanyAuditortypeDetailSerializer
    lookup_field = "id"
    queryset = AuditorTypes.objects.all()


class CompanyAuditorDetailsCreateView(CreateAPIView):
    """
    View to create or retrieve Company Auditor

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyAuditorSerializer
    detailed_serializer_class = CompanyAuditorDetailSerializer
    queryset = AuditorDetails.objects.all()

    def post(self, request, *args, **kwargs):
        data = request.data
        lookup =  Q(company_id=data.get('company'), is_deleted=False)&(Q(auditor_email=data.get('auditor_email')) | Q(auditor_phone=data.get('auditor_phone')))
        auditor_qs = AuditorDetails.objects.filter(lookup)
        if auditor_qs.exists():
            return response.Response(
                {
                    "message": "Auditor With Email Or Phone number already exists"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # sec_qs = AuditorDetails.objects.annotate(
        #     sec_email=Subquery(
        #         SecretaryDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(secretary_email=data.get('auditor_email')) | Q(secretary_phone=data.get('auditor_phone')))
        #         ).values('secretary_email')[:1]
        #     )
        # ).filter(sec_email__isnull=False)
        # if sec_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Secratry With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # director_qs = AuditorDetails.objects.annotate(
        #     director_email=Subquery(
        #         CompanyDirectorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(director_mail_id=data.get('auditor_email')) | Q(director_phone=data.get('auditor_phone')))
        #         ).values('director_mail_id')[:1]
        #     )
        # ).filter(director_email__isnull=False)
        # if director_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Director With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        return self.create(request, *args, **kwargs)


class CompanyAuditorDetailsUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Auditor

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyAuditorSerializer
    detailed_serializer_class = CompanyAuditorDetailSerializer
    lookup_field = "id"
    queryset = AuditorDetails.objects.all()

    def put(self, request, *args, **kwargs):
        data=request.data
        lookup =  Q(company_id=data.get('company'), is_deleted=False)&(Q(auditor_email=data.get('auditor_email')) | Q(auditor_phone=data.get('auditor_phone')))
        auditor_qs = AuditorDetails.objects.filter(lookup).exclude(id=kwargs.get('id'))
        if auditor_qs.exists():
            return response.Response(
                {
                    "message": "Auditor With Email Or Phone number already exists"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # sec_qs = AuditorDetails.objects.annotate(
        #     sec_email=Subquery(
        #         SecretaryDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(secretary_email=data.get('auditor_email')) | Q(secretary_phone=data.get('auditor_phone')))
        #         ).values('secretary_email')[:1]
        #     )
        # ).filter(sec_email__isnull=False)
        # if sec_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Secratry With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # director_qs = AuditorDetails.objects.annotate(
        #     director_email=Subquery(
        #         CompanyDirectorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(director_mail_id=data.get('auditor_email')) | Q(director_phone=data.get('auditor_phone')))
        #         ).values('director_mail_id')[:1]
        #     )
        # ).filter(director_email__isnull=False)
        # if director_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Director With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        return self.update(request, *args, **kwargs)

class CompanyAuditorDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Auditors Details

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyAuditorDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = AuditorDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class CompanySecretaryDetailsCreateView(CreateAPIView):
    """
    View to create or retrieve Company Secretary

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySecretarySerializer
    detailed_serializer_class = CompanySecretaryDetailSerializer
    queryset = SecretaryDetails.objects.all()

    def post(self, request, *args, **kwargs):
        data=request.data
        lookup =  Q(company_id=data.get('company'), is_deleted=False)&(Q(secretary_email=data.get('secretary_email')) | Q(secretary_phone=data.get('secretary_phone')))
        secretory_qs = SecretaryDetails.objects.filter(lookup)
        if secretory_qs.exists():
            return response.Response(
                {
                    "message": "Secretary with Email or Phone Number Already Exists"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # auditor_qs = SecretaryDetails.objects.annotate(
        #     auditor_email=Subquery(
        #         AuditorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(auditor_email=data.get('secretary_email')) | Q(auditor_phone=data.get('secretary_phone')))
        #         ).values('auditor_email')[:1]
        #     )
        # ).filter(auditor_email__isnull=False)
        # if auditor_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Auditor With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # director_qs = SecretaryDetails.objects.annotate(
        #     director_email=Subquery(
        #         CompanyDirectorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(director_mail_id=data.get('secretary_email')) | Q(director_phone=data.get('secretary_phone')))
        #         ).values('director_mail_id')[:1]
        #     )
        # ).filter(director_email__isnull=False)
        # if director_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Director With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        return self.create(request, *args, **kwargs)


class CompanySecretaryDetailsUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Secretary

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySecretarySerializer
    detailed_serializer_class = CompanySecretaryDetailSerializer
    lookup_field = "id"
    queryset = SecretaryDetails.objects.all()

    def put(self, request, *args, **kwargs):
        data = request.data
        lookup =  Q(company_id=data.get('company'), is_deleted=False)&(Q(secretary_email=data.get('secretary_email')) | Q(secretary_phone=data.get('secretary_phone')))
        secretory_qs = SecretaryDetails.objects.filter(lookup).exclude(id=kwargs.get('id'))
        if secretory_qs.exists():
            return response.Response(
                {
                    "message": "Secretary with Email or Phone Number Already Exists"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        # auditor_qs = SecretaryDetails.objects.annotate(
        #     auditor_email=Subquery(
        #         AuditorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(auditor_email=data.get('secretary_email')) | Q(auditor_phone=data.get('secretary_phone')))
        #         ).values('auditor_email')[:1]
        #     )
        # ).filter(auditor_email__isnull=False)
        # if auditor_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Auditor With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        # director_qs = SecretaryDetails.objects.annotate(
        #     director_email=Subquery(
        #         CompanyDirectorDetails.objects.filter(
        #             Q(company_id=data.get('company'), is_deleted=False)&(Q(director_mail_id=data.get('secretary_email')) | Q(director_phone=data.get('secretary_phone')))
        #         ).values('director_mail_id')[:1]
        #     )
        # ).filter(director_email__isnull=False)
        # if director_qs.exists():
        #     return response.Response(
        #         {
        #             "message": "Director With Email Or Phone number already exists"
        #         },
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        return self.update(request, *args, **kwargs)


class CompanySecretaryDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Auditors Details

    SURESH, 05.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanySecretarySerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = SecretaryDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


class CompanyBankDetailsCreateView(CreateAPIView):
    """
    View to create or retrieve Company Secretary

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyBankSerializer
    detailed_serializer_class = CompanyBankDetailSerializer
    queryset = BankDetails.objects.filter(is_deleted=False)


class CompanyBankDetailsUpdateView(UpdateAPIView):
    """
    View to update or retrieve Company Secretary

    SURESH, 28.12.2022
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyBankSerializer
    detailed_serializer_class = CompanyBankDetailSerializer
    lookup_field = "id"
    queryset = BankDetails.objects.all()


class CompanyBankDetailsRetrieveView(ListAPIView):
    """
    View to retrieve Auditors Details

    SURESH, 06.01.2023
    """

    # permission_classes = [permissions.IsAuthenticated]
    serializer_class = CompanyBankDetailSerializer
    lookup_field = "company"
    lookup_url_kwarg = "company_id"
    queryset = BankDetails.objects.all()

    def filter_queryset(self, queryset):
        filter_kwargs = {
            self.lookup_field: self.kwargs[self.lookup_url_kwarg],
            "is_deleted": False,
        }
        return queryset.filter(**filter_kwargs)


# class BankAccountTypesCreateView(CreateAPIView):
#     serializer_class = BankAccountTypesSerializer
#     detailed_serializer_class = BankAccountTypesDetailSerializer
#     queryset = BankAccountTypes.objects.all()


class BankAccountTypesRetrieveView(ListAPIView):
    """
    DroupDown retrieve Bank Accout Types

    SURESH, 06.01.2023
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BankAccountTypesSerializer
    detailed_serializer_class = BankAccountTypesDetailSerializer
    lookup_field = "id"
    queryset = BankAccountTypes.objects.filter().exclude(account_type=40)
    
    
    
    def list(self, request, *args, **kwargs):
        try:
            MultitenantSetup().create_to_connection(request)
            queryset = self.filter_queryset(self.get_queryset())

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(list(queryset), many=True)
            MultitenantSetup().go_to_old_connection(request)
            return Response(serializer.data)
        except Exception:
            MultitenantSetup().go_to_old_connection(request)
            return Response([])


class GetSubDepartments(ListAPIView):
    model = SubDepartments
    
    def get(self,request):
        dep_id = request.query_params.get('dep_id').split(',')
        q_filter = Q(department_id__in=dep_id, is_deleted=False)
        data = self.model.objects.filter(q_filter).values('id','name','department_id','department__name')
        response = success_response(data, 'announcements created successfully', 200)
        return Response(response,status=status.HTTP_200_OK)
    
class CompanyTickerRetrieveView(ListAPIView):

    model = Announcements
    def get(self, request, *args, **kwargs):
        today = timezone_now().date()
        q_filter = Q(company_id=self.kwargs['company_id'], is_deleted=False, announcement_type='TIKKER')
        query = self.model.objects.filter(q_filter).annotate(
            status=Case(
                When(post_date__gt=today, then=Value("Upcoming")),
                When(expired_date__lt=today, then=Value("Expired")),
                When(post_date__lte=today, expired_date__gte=today, then=Value("Published")),
                default=Value('None')
            ),
            department = ArrayAgg('departments__id', filter = Q(departments__isnull = False))
            ).order_by('-id').values()
        # response = success_response(queryset, 'announcements retrived successfully', 200)
        return Response(query,status=status.HTTP_200_OK)