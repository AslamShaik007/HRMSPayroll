# python packages
import json
import pandas as pd
from django.db import transaction
import traceback
from nested_multipart_parser.drf import DrfNestedParser  

# django packages
from django.shortcuts import get_object_or_404
from django.db import models as db_models
from django.contrib.postgres.aggregates import ArrayAgg

# rest framework packages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

# self app imports
from .models import (OnBoardingModule, OnBoardingSubModule, OnBoardingTask, 
                     OnBoardingCheckList, EmployeeCheckList, EmployeeOnboardStatus, Template, TaskType, OnBoardingFiles)

# others 
from core.utils import success_response, error_response

from directory.models import EmployeeReportingManager
# Create your views here.

class TemplateView(APIView):
    model=Template
    def get(self,request, *args, **kwargs):
        data = self.model.objects.filter(is_deleted=False).annotate(
            onboarding_module_id = db_models.F('onboardingmodule_template')).values()
        return Response(
            success_response(data,'Template Data Fetched Successfully', 200),
            status=status.HTTP_200_OK
        )
    def post(self,request, *args, **kwargs):
        request_data = request.data
        company_id = request_data.get('company_id',1)
        tenent_id = request_data.get('tenent_id',1)
        name = request_data.get('name')
        t_status = request_data.get('status','InActive')
        if self.model.objects.filter(name__icontains=name, is_deleted=False).exists():
            message = f"{name} already exits"
            return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
        data = self.model.objects.create(name=name,status=t_status)
        OnBoardingModule.objects.create(company_id=company_id, tenent_id=tenent_id, template_id=data.id)
        return Response(
            success_response([],f'Template {name} Created Successfully', 201),
            status=status.HTTP_201_CREATED
        )
    def patch(self,request, *args, **kwargs):
        request_data = request.data
        obj_id = kwargs.get('id')
        name = request_data.get('name')
        t_status = request_data.get('status','InActive')
        
        if self.model.objects.filter(name__icontains=name, is_deleted=False).exists():
            message = f"{name} already exits"
            return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
            
        obj = get_object_or_404(self.model, id=obj_id)
        obj.name=name
        obj.status=t_status
        obj.save()
        return Response(
            success_response([],f'Template {name} Updated Successfully', 200),
            status=status.HTTP_200_OK
        )
        
    def delete(self,request, *args, **kwargs):
        obj_id = kwargs.get('id')
        obj = get_object_or_404(self.model, id=obj_id)
        obj.is_deleted=True
        obj.status='InActive'
        obj.save()
        return Response(
            success_response([],f'Template {obj.name} Deleted Successfully', 200),
            status=status.HTTP_200_OK
        )      

class AssignTemplateView(APIView):
    model=EmployeeOnboardStatus
    def post(self,request, *args, **kwargs):
        request_data = request.data
        employee_id = request_data.get('employee_id').split(',')
        template_id = request_data.get('template_id',1)
        tenent_id = request_data.get('tenent_id',1)
        on_boarding_module = OnBoardingModule.objects.filter(template_id=template_id).first()
        employee_onboard_objs = []
        for emp_id in employee_id:
            if not self.model.objects.filter(onboarding_module=on_boarding_module, employee_id=emp_id).exists():
                employee_onboard_objs.append(EmployeeOnboardStatus(onboarding_module=on_boarding_module, employee_id=emp_id))
        if employee_onboard_objs:
            EmployeeOnboardStatus.objects.bulk_create(employee_onboard_objs)
        return Response(
            success_response([],f'Template Assigned Successfully', 201),
            status=status.HTTP_201_CREATED
        )
     
class OnBoardingModuleView(APIView):
    model = OnBoardingModule
    
    def get(self,request, *args, **kwargs):
        query_params = self.request.query_params
        company_id = query_params.get('company_id',1)
        template_id=query_params.get('template_id',1)
        data = self.model.objects.filter(company_id=company_id, template_id=template_id, 
                                         template__is_deleted=False, template__status='Active').annotate(
                                    template_name = db_models.F('template__name'),
                                    owner = db_models.F('created_by')
                            ).values('id','tenent_id','updated_by','created_at','updated_at',"template_name","template")
        return Response(
            success_response(data,'On Boarding Modules fetch successfully', 200),
            status=status.HTTP_200_OK
        )
    def post(self,request, *args, **kwargs):
        request_data = request.data

        obj, is_created = self.model.objects.get_or_create(company_id=request_data.get('company_id'), template_id=request_data.get('template_id'))
        obj.tenent_id = request_data.get('tenent_id',None)
        obj.save()
        
        return Response(
            success_response([],'On Boarding Modules created successfully', 201),
            status=status.HTTP_201_CREATED
        )
    def delete(self,request, *args, **kwargs):
        obj_id = kwargs.get('id')
        obj = get_object_or_404(self.model, id=obj_id)
        obj.is_deleted=True
        obj.save()
        return Response(
            success_response([],'On Boarding Module deleted successfully', 200),
            status=status.HTTP_200_OK
        )
        
class OnBoardingSubModuleView(APIView):
    model = OnBoardingSubModule
    def get(self,request, *args, **kwargs):
        company_id = self.request.query_params.get('company_id',1)
        employee_id = self.request.query_params.get('employee_id','')
        module_filters = db_models.Q(is_deleted=False, module__company_id=company_id, module__template__status='Active')
        if employee_id:
            module_filters &= db_models.Q(module__employeeonboardstatus__employee_id=employee_id, module__employeeonboardstatus__is_deleted=False)
        query = OnBoardingSubModule.objects.filter( 
                                         module_filters                   
                                    ).annotate(
                                            module_type = db_models.F('task_type'),
                                            tasks = ArrayAgg(
                                                db_models.expressions.Case(
                                                    db_models.When(on_boarding_task__isnull=True,
                                                        then=db_models.expressions.Func(
                                                            db_models.Value(''), db_models.Value(''),
                                                            function='jsonb_build_object',
                                                            output_field=db_models.JSONField()
                                                        ),
                                                    ),
                                                    db_models.When(db_models.Q(on_boarding_task__isnull=False),
                                                            then=       
                                                            db_models.expressions.Func(
                                                                db_models.Value('id'), "on_boarding_task__id",
                                                                db_models.Value('name'), "on_boarding_task__name",
                                                                db_models.Value('is_deleted'), "on_boarding_task__is_deleted",
                                                                # db_models.Value('onboarding_file'), "on_boarding_task__onboarding_file",
                                                                # db_models.Value('description'), "on_boarding_task__description",
                                                                function="jsonb_build_object",
                                                                output_field=db_models.JSONField()
                                                            )
                                                    )
                                                ),
                                                            distinct=True,
                                                            filter=db_models.Q(on_boarding_task__is_deleted=False),
                                            )
                                            ).values('id','name','status','tasks','module_type').order_by("id")
        print("query:",query)
        q1_filters = db_models.Q(
            on_boarding_check_lists__isnull=False,
            on_boarding_check_lists__is_deleted=False
        )
        if employee_id:
            q1_filters &= db_models.Q(
                            on_boarding_check_lists__employee_check_list__isnull=False,
                            on_boarding_check_lists__employee_check_list__employee_id=employee_id,
                            on_boarding_check_lists__employee_check_list__is_completed=True,
                                )
            
        # mapping checks counts to related tasks
        task_ids = [j['id'] for i in query for j in i.get('tasks', []) if j and 'id' in j]
        check_counts = OnBoardingTask.objects.filter(id__in=task_ids).annotate(
            total=db_models.Count('on_boarding_check_lists__id', filter=db_models.Q(on_boarding_check_lists__is_deleted=False, on_boarding_check_lists__isnull=False), distinct=True),
            completed=db_models.Count('on_boarding_check_lists__employee_check_list__id', filter=db_models.Q(q1_filters), distinct=True),
            file_count = db_models.Count('on_boarding_task_files__id', 
                                                    filter=db_models.Q
                                                        (on_boarding_task_files__isnull=False,
                                                        on_boarding_task_files__is_deleted=False
                                                    ), distinct=True),
        ).values('id', 'total', 'completed','file_count')
        task_counts_map = {task['id']: {'total': task['total'], 'completed': task['completed'], 'file_count': task['file_count']} for task in check_counts}
        for i in query:
            tasks = i.get('tasks', [])
            counts = {task_id: task_counts_map.get(task_id, {'total': 0, 'completed': 0, 'file_count': 0}) for task_id in (j['id'] for j in tasks if j and 'id' in j)}
            for task in tasks:
                if task and 'id' in task:
                    task.update(counts.get(task['id'], {'total': 0, 'completed': 0}))
                    if employee_id:
                        task['completed'] = counts.get(task['id'], {'completed': 0})['completed']
                    else:
                        task['completed']=0
                
        return Response(
            success_response(query,'Data Retrieved Successfully', 200),
            status=status.HTTP_200_OK
        )
        
    def post(self,request, *args, **kwargs):
        request_data = request.data
        name = request_data.get('name')
        module_id = request_data.get('module_id')
        if self.model.objects.filter(module_id=module_id, name=name).exists():
            message = f"{name} Already Exists"
            return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            ) 
        obj, is_created = self.model.objects.get_or_create(module_id=module_id, name=name)
        obj.task_type = request_data.get('task_type',"Pre On Boarding")
        obj.status = request_data.get('status',"Active")
        obj.save()
        
        return Response(
            success_response([],f'{name} created successfully', 201),
            status=status.HTTP_201_CREATED
        )
    def patch(self,request, *args, **kwargs):
        
        obj_id = kwargs.get('id')
        request_data=request.data
        obj = get_object_or_404(self.model, id=obj_id)
        if not request_data.get('name',""):
            message = "Please Provide Name"
            return Response(
                error_response(message,message),
                status=status.HTTP_400_BAD_REQUEST
            )
        name = request_data.get('name')
        obj.name = name
        obj.task_type = request_data.get('task_type',"Pre On Boarding")
        obj.status = request_data.get('status',"Active")
        obj.save()
        
        return Response(
            success_response([],f'{name} Updated successfully', 200),
            status=status.HTTP_200_OK
            
        )
    def delete(self,request, *args, **kwargs):
        obj_id = kwargs.get('id')
        obj = get_object_or_404(self.model, id=obj_id)
        obj.is_deleted=True
        obj.save()
        return Response(
            success_response([],f'{obj.name} deleted successfully', 200),
            status=status.HTTP_200_OK
        )
      
class OnBoardingTaskView(APIView):
    
    model=OnBoardingTask
    parser_classes = [DrfNestedParser]
    def get(self,request, *args, **kwargs):
        task_id = self.request.query_params.get('task_id')
        employee_id = self.request.query_params.get('employee_id','')
        q_filters = db_models.Q(id=task_id)
        
        key = db_models.Value(False)
        emp_filter = db_models.Q(on_boarding_check_lists__is_deleted=False)
        if employee_id and EmployeeCheckList.objects.filter(task_check__task_id=task_id, employee_id=employee_id).exists():
            key = "on_boarding_check_lists__employee_check_list__is_completed"
            emp_filter &= db_models.Q(
                                    on_boarding_check_lists__is_deleted=False,
                                    on_boarding_check_lists__employee_check_list__employee_id=employee_id,
                                )
        # if employee_id:
        query = OnBoardingTask.objects.filter(q_filters).annotate(
                check_list = ArrayAgg(
                                    db_models.Case(
                                            db_models.When(on_boarding_check_lists__isnull=True,
                                                        then=db_models.expressions.Func(
                                                                    db_models.Value(''), db_models.Value(''),
                                                                    function='jsonb_build_object',
                                                                    output_field=db_models.JSONField()
                                                                ),
                                                            ),
                                            db_models.When(on_boarding_check_lists__isnull=False, 
                                                        then= db_models.expressions.Func(
                                                                db_models.Value('id'), "on_boarding_check_lists__id",
                                                                db_models.Value('title'), "on_boarding_check_lists__title",
                                                                db_models.Value('name'), "on_boarding_check_lists__check_name",
                                                                db_models.Value("is_completed"), key,
                                                                function="jsonb_build_object",
                                                                output_field=db_models.JSONField()
                                                            )
                                        ),
                                            default=db_models.Value(None),
                                            output_field=db_models.JSONField()
                                    ),
                            distinct=True, filter = emp_filter
                        ),
                files = ArrayAgg(
                    db_models.Case(
                            db_models.When(on_boarding_task_files__isnull=True,
                                                                            then=db_models.expressions.Func(
                                                                        db_models.Value(''), db_models.Value(''),
                                                                        function='jsonb_build_object',
                                                                    output_field=db_models.JSONField()
                                                                ),
                                                            ),
                            db_models.When(on_boarding_task_files__isnull=False, 
                            then= db_models.expressions.Func(
                                                db_models.Value('id'), "on_boarding_task_files__id",
                                                db_models.Value('file_name'), "on_boarding_task_files__file_name",
                                                db_models.Value('onboarding_file'), "on_boarding_task_files__onboarding_file",
                                                db_models.Value('is_deleted'), "on_boarding_task_files__is_deleted",
                                                function="jsonb_build_object",
                                                output_field=db_models.JSONField()
                                            )
                        ),default=db_models.Value(None),
                            output_field=db_models.JSONField(),
                            # filter = db_models.Q(on_boarding_check_lists__is_deleted=False)
                    )
            , distinct=True,
            filter = db_models.Q(on_boarding_task_files__is_deleted=False))
                        ).values('id','name','description','check_list','files')
        # else:
        #     query = OnBoardingTask.objects.filter(q_filters).annotate(
        #         check_list = ArrayAgg(
        #                             db_models.Case(
        #                                     db_models.When(on_boarding_check_lists__isnull=True,
        #                                                             then=db_models.expressions.Func(
        #                                                             db_models.Value(''), db_models.Value(''),
        #                                                             function='jsonb_build_object',
        #                                                             output_field=db_models.JSONField()
        #                                                         ),
        #                                                     ),
        #                                     db_models.When(on_boarding_check_lists__isnull=False, 
        #                                     then= db_models.expressions.Func(
        #                                                         db_models.Value('id'), "on_boarding_check_lists__id",
        #                                                         db_models.Value('name'), "on_boarding_check_lists__check_name",
        #                                                         db_models.Value('title'), "on_boarding_check_lists__title",
        #                                                         # db_models.Value('is_completed'), "on_boarding_check_lists__employee_check_list__is_completed",
        #                                                         function="jsonb_build_object",
        #                                                         output_field=db_models.JSONField()
        #                                                     ),
        #                                 ),default=db_models.Value(None),
        #                                     output_field=db_models.JSONField()
        #                             )
        #                     , distinct=True,
        #                     filter = db_models.Q(on_boarding_check_lists__is_deleted=False)),
        #         files = ArrayAgg(
        #             db_models.Case(
        #                     db_models.When(on_boarding_task_files__isnull=True,
        #                                                         then=db_models.expressions.Func(
        #                                                             db_models.Value(''), db_models.Value(''),
        #                                                             function='jsonb_build_object',
        #                                                             output_field=db_models.JSONField()
        #                                                         ),
        #                                                     ),
        #                     db_models.When(db_models.Q(on_boarding_task_files__isnull=False), 
        #                     then= db_models.expressions.Func(
        #                                         db_models.Value('id'), "on_boarding_task_files__id",
        #                                         db_models.Value('file_name'), "on_boarding_task_files__file_name",
        #                                         db_models.Value('onboarding_file'), "on_boarding_task_files__onboarding_file",
        #                                         db_models.Value('is_deleted'), "on_boarding_task_files__is_deleted",
        #                                         function="jsonb_build_object",
        #                                         output_field=db_models.JSONField()
        #                                     )
        #                 ),default=db_models.Value(None),
        #                     output_field=db_models.JSONField()
        #             )
        #     , distinct=True,
        #     filter = db_models.Q(on_boarding_task_files__is_deleted=False))
        #                 ).values('id','name','description','check_list','files')

        return Response(
                success_response(query,'Data Retrieved Successfully', 200),
                status=status.HTTP_200_OK
            )
    def post(self,request, *args, **kwargs):
        sid =transaction.set_autocommit(autocommit=False)
        try:
            request_data = request.data
            request_data = request_data.dict()
            checks = request_data.pop('checks',[])
            if checks and isinstance(checks,str):
                checks = json.loads(checks)
                request_data['checks'] = checks   
            name = request_data.get('name')
            sub_module_id = request_data.get('sub_module')
            description = request_data.get('description','')
            if not name:
                message = "Please Provide Name"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not sub_module_id:
                message = "Please Provide Sub Module Id"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            if self.model.objects.filter(sub_module_id=sub_module_id, name=name, is_deleted=False).exists():
                message = "Task Already Exist"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            task_obj = self.model.objects.create(name=name, description=description, sub_module_id=sub_module_id)
            if checks:
                title = request_data.get('check_list_title','')
                for obj in checks:
                    if OnBoardingCheckList.objects.filter(task_id=task_obj.id, check_name=obj['check'], title=title).exists():
                        transaction.rollback(sid)
                        return Response(
                                    error_response(f"{obj['check']} check already exists", f"{obj['check']} check already exists"),
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                    is_created = OnBoardingCheckList.objects.create(task_id=task_obj.id, check_name=obj['check'], is_deleted=obj['is_deleted'], title=title)
            #handling multipe files
            # handling multipe files
            files_data = request_data.get('file_data','')
            if files_data:
                for file_obj in files_data:
                    file_name=file_obj.get('file_name','')
                    # if not file_name:
                    #     transaction.rollback(sid)
                    #     return Response(
                    #             error_response("file name is mandatory", "file name is mandatory"),
                    #             status=status.HTTP_400_BAD_REQUEST
                    #         ) 
                    # if not file_obj.get('onboarding_file',''):
                    #     transaction.rollback(sid)
                    #     return Response(
                    #             error_response("file is mandatory", "file is mandatory"),
                    #             status=status.HTTP_400_BAD_REQUEST
                    #         ) 
                    if OnBoardingFiles.objects.filter(task_files_id=task_obj.id, file_name=file_name).exists():
                        transaction.rollback(sid)
                        return Response(
                                error_response(f"{file_name} file already exists", f"{file_name} file already exists"),
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    onboarding_file=file_obj['onboarding_file'][0]
                    OnBoardingFiles.objects.create(task_files_id=task_obj.id, file_name=file_name, onboarding_file=onboarding_file)
            transaction.commit()
            return Response(
                success_response([],f'{name} created successfully', 201),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            transaction.rollback(sid)
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def patch(self,request, *args, **kwargs):
        sid = transaction.set_autocommit(autocommit=False)
        try:
            task_obj = get_object_or_404(self.model, id=self.kwargs.get('id'))
            request_data = request.data
            request_data = request_data.dict()
            checks = request_data.pop('checks',[])
            if checks and isinstance(checks,str):
                checks = json.loads(checks)
                request_data['checks'] = checks   
            name = request_data.get('name')
            sub_module_id = task_obj.sub_module_id
            description = request_data.get('description','')
            title = request_data.get('check_list_title','')
            
            if not name:
                message = "Please Provide Name"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            if self.model.objects.filter(sub_module_id=sub_module_id, name=name, is_deleted=False).exclude(id=self.kwargs.get('id')).exists():
                message = "Task Already Exist"
                return Response(
                    error_response(message,message),
                    status=status.HTTP_400_BAD_REQUEST
                )
            task_obj.name=name
            task_obj.description=description
            task_obj.save()
            
            if checks:
                for obj in checks:
                    if 'id' in obj:
                        if OnBoardingCheckList.objects.filter(task_id=self.kwargs.get('id'), check_name=obj['check'], 
                                                              is_deleted=obj['is_deleted'], title=title).exclude(id=obj['id']).exists():
                            transaction.rollback(sid)
                            return Response(
                                    error_response(f"{obj['check']} check already exists", f"{obj['check']} check already exists"),
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                        OnBoardingCheckList.objects.filter(id=obj['id']).update(check_name=obj['check'], is_deleted=obj['is_deleted'], title=title)
                    else:
                        if OnBoardingCheckList.objects.filter(task_id=self.kwargs.get('id'), check_name=obj['check'], 
                                                              is_deleted=obj['is_deleted'], title=title).exists():
                            transaction.rollback(sid)
                            return Response(
                                    error_response(f"{obj['check']} check already exists", f"{obj['check']} check already exists"),
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                        OnBoardingCheckList.objects.create(task_id=self.kwargs.get('id'), check_name=obj['check'], is_deleted=obj['is_deleted'], title=title)
            
            # handling multipe files
            files_data = request_data.get('file_data','')
            if files_data:
                for file_obj in files_data:
                    file_name=file_obj.get('file_name','')
                    # if not file_name:
                    #     transaction.rollback(sid)
                    #     return Response(
                    #             error_response("file name is mandatory", "file name is mandatory"),
                    #             status=status.HTTP_400_BAD_REQUEST
                    #         )
                    
                    # if not file_obj.get('onboarding_file',''):
                    #     transaction.rollback(sid)
                    #     return Response(
                    #             error_response("file is mandatory", "file is mandatory"),
                    #             status=status.HTTP_400_BAD_REQUEST
                    #         ) 
                    if 'id' in file_obj:
                        if OnBoardingFiles.objects.exclude(id=file_obj['id']).filter(task_files_id=self.kwargs.get('id'), file_name=file_name).exists():
                            return Response(
                                    error_response(f"{file_name} file already exists", f"{file_name} file already exists"),
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                        ob_file_obj = OnBoardingFiles.objects.filter(id=file_obj['id']).first()
                    else:
                        if OnBoardingFiles.objects.filter(task_files_id=self.kwargs.get('id'), file_name=file_name).exists():
                            return Response(
                                    error_response(f"{file_name} file already exists", f"{file_name} file already exists"),
                                    status=status.HTTP_400_BAD_REQUEST
                                )
                        ob_file_obj = OnBoardingFiles.objects.create(task_files_id=self.kwargs.get('id'))
                    if 'is_deleted' in file_obj:
                        is_dltd = True if file_obj.get('is_deleted','') == 'true' else False
                        ob_file_obj.is_deleted = is_dltd
                    ob_file_obj.file_name = file_name
                    if file_obj.get('onboarding_file',''):
                        file=file_obj['onboarding_file'][0]
                        ob_file_obj.onboarding_file = file if not isinstance(file, str) else None
                    ob_file_obj.save()
                    
            #creating employee check list
            employee_id = request_data.get('employee_id','')
            if employee_id and checks:
                for task_check in checks:
                    cmp_check_status = task_check.get('is_completed', False)
                    if 'id' in task_check:
                        obj, is_created = EmployeeCheckList.objects.get_or_create(
                            employee_id=employee_id, task_check_id=task_check['id']
                        )
                        obj.is_deleted= task_check['is_deleted']
                        if 'is_completed' in task_check:
                            obj.is_completed= cmp_check_status if cmp_check_status is not None else False
                        obj.save()
                    else:
                        task_check_id = OnBoardingCheckList.objects.filter(task_id=self.kwargs.get('id')).first()
                        obj, is_created = EmployeeCheckList.objects.get_or_create(
                            employee_id=employee_id, task_check_id=task_check_id.id
                        )
                        obj.is_deleted= task_check['is_deleted']
                        if 'is_completed' in task_check:
                            obj.is_completed= cmp_check_status if cmp_check_status is not None else False
                        obj.save()
            transaction.commit()
            return Response(
                success_response([],f'{name} updated successfully', 201),
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            transaction.rollback(sid)
            return Response(
                error_response(f'{e} Error: {traceback.format_exc()}', "Some thing went wrong"),
                status=status.HTTP_400_BAD_REQUEST
            )
            
    def delete(self,request, *args, **kwargs):
        obj_id = kwargs.get('id')
        obj = get_object_or_404(self.model, id=obj_id)
        obj.is_deleted=True
        obj.save()
        return Response(
            success_response([],f'{obj.name} deleted successfully', 200),
            status=status.HTTP_200_OK
        )
        
class TaskTypeChoices(APIView):
    model = TaskType
    
    def get(self, request, *args, **kwargs):
        data = [
            {"name": choice[1], 'id':i+1}
            for i,choice in enumerate(TaskType.choices)
        ]
        return Response(
                success_response(data, "Successfully Fetched TaskType Choices", 200),
                status=status.HTTP_200_OK
            )

class OnboardHierarchy(APIView):
    model = EmployeeReportingManager
    
    def get(self, request, *args, **kwargs):
        emp_id = self.request.query_params.get('employee_id','')
        if not emp_id:
            emp_id = request.user.employee_details.first().id
        my_list = []
        tag = True
        while tag:
            query = EmployeeReportingManager.objects.filter(employee_id=emp_id,manager_type__manager_type=10,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False
                                                        ).annotate(
                                                              image = db_models.F('employee__employee_image'),
                                                              designation = db_models.F('employee__work_details__designation__name'),
                                                              name = db_models.F('employee__user__username'),
                                                              bio = db_models.F('employee__bio'),
                                                              role = db_models.F('employee__roles__name'),
                                                            ).values('id','image','designation','name','manager_id', 'bio','employee_id', 'role')
            if query.exists():
                my_list.append(query.first())
                emp_id = query.first().get('manager_id')
            else:
                query = EmployeeReportingManager.objects.filter(manager_id=emp_id,manager_type__manager_type=10,
                                                            manager__work_details__employee_status='Active',
                                                            is_deleted=False
                                                        ).annotate(
                                                              image = db_models.F('manager__employee_image'),
                                                              designation = db_models.F('manager__work_details__designation__name'),
                                                              name = db_models.F('manager__user__username'),
                                                              bio = db_models.F('manager__bio'),
                                                              role = db_models.F('manager__roles__name'),
                                                            ).values('id','image','designation','name','manager_id','bio','employee_id', 'role')
                if query.exists():
                    my_list.append(query.first())
                break
        new_onboard_list = []
        if my_list:
            for data in my_list:
                if data['role'] not in ["EMPLOYEE", "TEAM LEAD"]:
                    new_onboard_list.append(data)
        return Response(
                success_response(new_onboard_list, "Successfully Fetched Onboard Hierarchy Details", 200),
                status=status.HTTP_200_OK
            )