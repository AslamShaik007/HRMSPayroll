import os
import sys
import django
import pandas as pd
import traceback
from typing import Any
sys.path.append('./')
if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]
    
from django.apps import apps
from django.db import transaction

from core.utils import load_class, timezone_now
from HRMSApp.models import FutureModule
from directory.models import EmployeeReportingManager, ManagerType, Employee, EmployeeWorkHistoryDetails
from django.db import models as db_models

class RunFutureModules:

    # @transaction.atomic()
    def handle(self, *args: Any, **options: Any):
        futures = FutureModule.objects.filter(
            status=FutureModule.QUEUE, effective_date__lte=timezone_now().date()
        )
        for module in futures:
            sid = transaction.set_autocommit(autocommit=False)
            try:
                ct = module.content_type
                payload = module.payload
                model = apps.get_model(app_label=ct.app_label, model_name=ct.model)  #model coming
                qs: Employee = model.objects.filter(id__in=payload["id"])
                if ("manager_details" in payload and payload['manager_details'].get("reporting_manager")):
                    reporting_manager_id = int(payload["manager_details"]["reporting_manager"])
                    employee_ids = payload["id"]
                    manager_type_first = ManagerType.objects.filter(manager_type=10).first()
                    if reporting_manager_id in employee_ids: employee_ids.remove(reporting_manager_id)
                    
                    company_id = Employee.objects.get(id=reporting_manager_id).company_id
                    data = {'ids':employee_ids,'rep_m':reporting_manager_id}
                    
                    for emp_id in employee_ids:
                        if EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager_id, 
                                                                manager_type__manager_type=ManagerType.PRIMARY, is_deleted=False).exists():
                            continue
                        elif EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager_id, 
                                                                manager_type__manager_type=ManagerType.SECONDARY, is_deleted=False).exists():
                            EmployeeReportingManager.objects.filter(employee_id=emp_id,
                                                                    manager_type__manager_type=ManagerType.PRIMARY, 
                                                                is_deleted=False).update(is_deleted=True)
                            EmployeeReportingManager.objects.filter(employee_id=emp_id, manager_id=reporting_manager_id, 
                                                                manager_type__manager_type=ManagerType.SECONDARY, is_deleted=False).update(
                                                                    manager_type = manager_type_first 
                                                                )
                        else:
                            EmployeeReportingManager.objects.filter(employee_id=emp_id,
                                                                    manager_type__manager_type=ManagerType.PRIMARY, 
                                                                is_deleted=False).update(is_deleted=True)
                            EmployeeReportingManager.objects.create(
                                employee_id=emp_id, manager_id=reporting_manager_id,manager_type = manager_type_first
                            )
                    
                    emp_df = pd.DataFrame(data)
                    
                    # emp_df['is_exist'] = emp_df.ids.apply(
                    # lambda a: bool(EmployeeReportingManager.objects.filter(
                    #     employee_id=a,manager_type__manager_type=10,is_deleted=False
                    #     ).exists()))
                    # emp_df.apply(lambda obj:EmployeeReportingManager.objects.filter(
                    #         employee_id=obj['ids'],manager_type__manager_type=10,is_deleted=False
                    #         ).update(manager_id = obj['rep_m']) if obj['is_exist'] else EmployeeReportingManager.objects.get_or_create(
                    #             employee_id=obj['ids'], manager_id=obj['rep_m'],manager_type = manager_type_first
                    #         ),axis=1)
                    
                    # emp_df.apply(lambda obj:EmployeeReportingManager.objects.get_or_create(employee_id = obj['rep_m'],
                    #                                         manager_id = obj['ceo'],manager_type = manager_type_first),axis=1)
                
                    # all_emps = list(EmployeeReportingManager.objects.filter(
                    #     manager_id=ceo_employee,manager_type__manager_type = 10).values_list('employee',flat=True))        
                            
                    # emp_rep_ceo = {'emps_1':all_emps}
                    # new_emp_df = pd.DataFrame(emp_rep_ceo)
                    # EmployeeReportingManager.objects.filter(employee_id = ceo_employee).delete()
                    # new_emp_df.emps_1 = new_emp_df.emps_1.apply(lambda emp :'' if EmployeeReportingManager.objects.filter(manager_id = emp).exists() else 
                    #                 EmployeeReportingManager.objects.filter(employee_id = emp).delete())
                    current_date = timezone_now()
                    m_type = "Primary"
                    emp_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).update(manager_type=m_type) 
                                        if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True, work_from__date=current_date.date()).exists()
                                        else (EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['ids'], manager_id=obj['rep_m'], work_from=current_date, manager_type=m_type),
                                            EmployeeWorkHistoryDetails.objects.filter(db_models.Q(employee_id=obj['ids'],manager_id=obj['rep_m'], work_to__isnull=True), ~db_models.Q(manager_type=m_type)).update(work_to=current_date)), axis=1)
                    emp_df['manager_ids'] = emp_df.apply(lambda obj:
                                        list(EmployeeReportingManager.objects.filter(employee_id=obj['ids'], is_deleted=False).values_list('manager_id',flat=True)), axis=1)                   
                    emp_df.apply(lambda obj:
                        EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['ids'],work_to__isnull=True,department__isnull=True).exclude(manager_id__in =obj['manager_ids']).update(work_to=timezone_now()), axis=1)    
                
                if 'work_details' in payload and payload['work_details'].get('department',''):
                    e_ids = payload.get('id')
                    dep_id =  payload['work_details'].get('department')
                    dep_df = pd.DataFrame(e_ids,columns=['e_ids']) 
                    dep_df['dep_id'] = dep_id 
                    if len(dep_df) !=0:
                        dep_df.apply(lambda obj: ''
                                        if EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['e_ids'],department_id=obj['dep_id'], work_to__isnull=True).exists()
                                        else EmployeeWorkHistoryDetails.objects.get_or_create(employee_id=obj['e_ids'],department_id=obj['dep_id'], work_from=timezone_now()), axis=1 )
                        
                        dep_df.apply(lambda obj: EmployeeWorkHistoryDetails.objects.filter(employee_id=obj['e_ids'],department_id__isnull=False, work_to__isnull=True
                                                                                       ).exclude(department_id=obj['dep_id']).update(work_to=timezone_now()), axis=1)   
                for instance in qs:
                    serializer = load_class(module.serializer)(
                        instance=instance, data=payload, partial=True
                    )
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                    module.status = FutureModule.SUCCESS
                if "commit" in sys.argv:
                    transaction.commit()
                else:
                    module.status = FutureModule.QUEUE
                    transaction.rollback(sid)
            except Exception as e:
                traceback.print_exc()
                module.logs = traceback.format_exc()
                module.status = FutureModule.FAIL
                transaction.rollback(sid)
                print("exception:",e)
            module.save()
            
        if "commit" in sys.argv:
            print("future modules run successfully!")
        else:
            print("Dry Run!")
        
        # print("future modules run successfully!")
if __name__ == "__main__":
    RunFutureModules().handle()