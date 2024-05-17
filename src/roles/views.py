import pandas as pd
import traceback
from django.contrib.auth.models import Permission
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from HRMSApp.custom_permissions import IsHrAdminPermission
from HRMSApp.models import Roles
from directory.models import Employee, EmployeeReportingManager, EmployeeWorkHistoryDetails

from .models import (
    RolesModules, RolesSubModule, RolesSubmoduleAttachModels,
    RoleModuleMapping, ModuleSubmoduleMapping,
    RoleSubmoduleModelMapping, SubModuleModelLeavelMapping
)
from .utils import ROLES_INPUT

from rest_framework.parsers import MultiPartParser, JSONParser
from core.utils import error_response, timezone_now
from django.db import models as db_models
from HRMSProject.multitenant_setup import MultitenantSetup
import logging
import os
from django.db import connection
from HRMSProject.module_creation_script import module_sub_creation

logger = logging.getLogger('django')



class CustomPermissionsAPIView(APIView):
    """
    Created-By: Padmaraju P
    """
    parser_classes = (JSONParser,)
    permission_classes = [permissions.IsAuthenticated]
    model = RoleModuleMapping
    
    
    def get(self, request):
        """
        Will Provide Exisitng Permissions of roles,
        can be Added Or Updated by Admin Only
        """
        query_params = request.query_params
        role_id = query_params.get('role_id')
        company_id = query_params.get('company_id')
        if not role_id and not company_id:
            return Response(
                'Role ID and Company ID were Required',
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            MultitenantSetup().create_to_connection(request)
            existed_data = RoleModuleMapping.objects.filter(role_id=role_id, company_id=company_id).values(
                'module_id',
                'module__name', 'can_add', 'can_delete', 'can_change', 'can_view',
                'modulesubmodulemapping__submodule__id',
                'modulesubmodulemapping__submodule__name',
                'modulesubmodulemapping__can_add', 'modulesubmodulemapping__can_delete',
                'modulesubmodulemapping__can_change', 'modulesubmodulemapping__can_view',
                )
            existed_data_convert = {
                'modules': {}
            }
            final_output = ROLES_INPUT
            for module_data in existed_data:
                if module_data['module__name'] not in existed_data_convert['modules'].keys():
                    existed_data_convert['modules'][module_data['module__name']] = {
                        'module_name':  module_data['module__name'],
                        'add': False, 'delete': False, 'change': False, 'view': False,
                        'submodules': {}
                    }
                if module_data['modulesubmodulemapping__submodule__name'] not in existed_data_convert['modules'][module_data['module__name']]['submodules'].keys():
                    existed_data_convert['modules'][module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']] = {
                        'submodule__name': module_data['modulesubmodulemapping__submodule__name'],
                        'add': False, 'delete': False, 'change': False, 'view': False
                    }
                existed_data_convert['modules'][module_data[
                    'module__name']]['add'] = module_data['can_add']
                existed_data_convert['modules'][
                    module_data['module__name']]['delete'] = module_data['can_delete']
                existed_data_convert['modules'][
                    module_data['module__name']]['change'] = module_data['can_change']
                existed_data_convert['modules'][
                    module_data['module__name']]['view'] = module_data['can_view']
                existed_data_convert['modules'][
                    module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['add'] = module_data['modulesubmodulemapping__can_add']
                existed_data_convert['modules'][
                    module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['change'] = module_data['modulesubmodulemapping__can_change']
                existed_data_convert['modules'][
                    module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['view'] = module_data['modulesubmodulemapping__can_view']
                existed_data_convert['modules'][
                    module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['delete'] = module_data['modulesubmodulemapping__can_delete']
            for module_name in final_output['modules'].keys():
                if existed_data_convert['modules'].get(module_name):
                    final_output['modules'][module_name]['add'] = existed_data_convert['modules'][module_name]['add']
                    final_output['modules'][module_name]['delete'] = existed_data_convert['modules'][module_name]['delete']
                    final_output['modules'][module_name]['view'] = existed_data_convert['modules'][module_name]['view']
                    final_output['modules'][module_name]['change'] = existed_data_convert['modules'][module_name]['change']
                    for sub_module in ROLES_INPUT['modules'][module_name]['submodules'].keys():
                        if existed_data_convert['modules'][module_name]['submodules'].get(sub_module):
                            final_output['modules'][module_name]['submodules'][sub_module]['add'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['add']
                            final_output['modules'][module_name]['submodules'][sub_module]['view'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['view']
                            final_output['modules'][module_name]['submodules'][sub_module]['delete'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['delete']
                            final_output['modules'][module_name]['submodules'][sub_module]['change'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['change']
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                final_output,
                status=status.HTTP_200_OK
            )
        except Exception:
            MultitenantSetup().go_to_old_connection(request)
            return Response(
                [],
                status=status.HTTP_200_OK
            )
    
    def post(self, request):
        try:
            
            """
            Functionality
            1. Initially Fetch Data from frontend                                                           Done
            2. Update Or Create Accordingly in the Database                                                 Done
            3. Add Model Permissions For Role                                                               Done
            """
            data = request.data
            role_id = data.get('role_id')
            company_id = data.get('company_id')
            role_data = data.get('role_data')
            add_permission_models = []
            delete_permission_models = []
            update_permission_models = []
            view_permission_models = []
            
            if not role_id:
                return Response(
                    {
                        'message': 'Role ID is Required'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not company_id:
                return Response(
                    {
                        'message': 'Company ID is Required'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not role_data:
                return Response(
                    {
                        'message': 'Roles Data is Missing'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            sub_mods = SubModuleModelLeavelMapping.objects.filter()
            if not sub_mods.exists():
                environ = os.environ.get('APP_ENV', 'qa')
                new_db_name = connection.settings_dict['NAME']
                module_sub_creation(
                    environ,
                    new_db_name
                )
            role_modules_to_update = list(role_data['modules'])
            role_obj = Roles.objects.get(id=role_id)
            for module_name in role_modules_to_update:
                role_modules_qs = RoleModuleMapping.objects.filter(role_id=role_id, module__name=module_name, company_id=company_id)
                if role_modules_qs.exists():
                    role_module_mapping_obj = role_modules_qs.first()
                    role_module_mapping_obj.can_add = role_data['modules'][module_name]['add']
                    role_module_mapping_obj.can_view = role_data['modules'][module_name]['view']
                    role_module_mapping_obj.can_delete = role_data['modules'][module_name]['delete']
                    role_module_mapping_obj.can_change = role_data['modules'][module_name]['change']
                    role_module_mapping_obj.save()
                else:
                    module_obj = RolesModules.objects.get(name=module_name)
                    role_module_mapping_obj = RoleModuleMapping.objects.create(
                        role_id=role_id, module_id=module_obj.id, company_id=company_id,
                        can_add=role_data['modules'][module_name]['add'], can_view=role_data['modules'][module_name]['view'],
                        can_delete=role_data['modules'][module_name]['delete'], can_change=role_data['modules'][module_name]['change']
                    )
                submodules_to_update = list(role_data['modules'][module_name]['submodules'])
                for submodule_name in submodules_to_update:
                    module_submodule_qs = ModuleSubmoduleMapping.objects.filter(role_module_map_id=role_module_mapping_obj.id, submodule__name=submodule_name)
                    if module_submodule_qs.exists():
                        submodule_obj = RolesSubModule.objects.get(name=submodule_name)
                        module_submodule_obj = module_submodule_qs.first()
                        module_submodule_obj.can_add = role_data['modules'][module_name]['submodules'][submodule_name]['add']
                        module_submodule_obj.can_view = role_data['modules'][module_name]['submodules'][submodule_name]['view']
                        module_submodule_obj.can_delete = role_data['modules'][module_name]['submodules'][submodule_name]['delete']
                        module_submodule_obj.can_change = role_data['modules'][module_name]['submodules'][submodule_name]['change']
                        module_submodule_obj.save()
                    else:
                        submodule_obj = RolesSubModule.objects.get(name=submodule_name)
                        module_submodule_obj = ModuleSubmoduleMapping.objects.create(
                            role_module_map_id=role_module_mapping_obj.id, submodule_id=submodule_obj.id,
                            can_add=role_data['modules'][module_name]['submodules'][submodule_name]['add'],
                            can_view=role_data['modules'][module_name]['submodules'][submodule_name]['view'],
                            can_delete=role_data['modules'][module_name]['submodules'][submodule_name]['delete'],
                            can_change=role_data['modules'][module_name]['submodules'][submodule_name]['change']
                        )
                    # fetch all models from Submodule
                    models = SubModuleModelLeavelMapping.objects.filter(submodule_id=submodule_obj.id).values_list('model__name', flat=True)
                    # check for each model if RoleSubmoduleModelMapping 
                    for model_name in models:
                        role_submod_model_map_qs = RoleSubmoduleModelMapping.objects.filter(
                            mod_sub_map_id=module_submodule_obj.id, model__name=model_name
                        )
                        permission_add = Permission.objects.get(codename=f'add_{model_name}'.lower())
                        permission_view = Permission.objects.get(codename=f'view_{model_name}'.lower())
                        permission_delete = Permission.objects.get(codename=f'delete_{model_name}'.lower())
                        permission_change = Permission.objects.get(codename=f'change_{model_name}'.lower())
                        if role_submod_model_map_qs.exists():
                            role_submod_model_map_obj = role_submod_model_map_qs.first()
                            role_submod_model_map_obj.can_add = role_data['modules'][module_name]['submodules'][submodule_name]['add']
                            role_submod_model_map_obj.can_view = role_data['modules'][module_name]['submodules'][submodule_name]['view']
                            role_submod_model_map_obj.can_delete = role_data['modules'][module_name]['submodules'][submodule_name]['delete']
                            role_submod_model_map_obj.can_change = role_data['modules'][module_name]['submodules'][submodule_name]['change']
                            role_submod_model_map_obj.save()
                        else:
                            model_obj = RolesSubmoduleAttachModels.objects.get(name=model_name)
                            role_submod_model_map_obj = RoleSubmoduleModelMapping.objects.create(
                                mod_sub_map_id=module_submodule_obj.id, model_id=model_obj.id,
                                can_add = role_data['modules'][module_name]['submodules'][submodule_name]['add'],
                                can_view=role_data['modules'][module_name]['submodules'][submodule_name]['view'],
                                can_change=role_data['modules'][module_name]['submodules'][submodule_name]['change'],
                                can_delete=role_data['modules'][module_name]['submodules'][submodule_name]['delete'],
                            )

                        if role_data['modules'][module_name]['submodules'][submodule_name]['add']:
                            role_module_mapping_obj.permissions.add(permission_add.id)
                            add_permission_models.append({role_module_mapping_obj.id: permission_add.id})
                        else:
                            role_module_mapping_obj.permissions.remove(permission_add.id)
                        if role_data['modules'][module_name]['submodules'][submodule_name]['view']:
                            role_module_mapping_obj.permissions.add(permission_view.id)
                            view_permission_models.append({role_module_mapping_obj.id: permission_view.id})
                            
                        else:
                            role_module_mapping_obj.permissions.remove(permission_view.id)
                        if role_data['modules'][module_name]['submodules'][submodule_name]['delete']:
                            role_module_mapping_obj.permissions.add(permission_delete.id)
                            delete_permission_models.append({role_module_mapping_obj.id: permission_delete.id})
                        else:
                            role_module_mapping_obj.permissions.remove(permission_delete.id)
                        if role_data['modules'][module_name]['submodules'][submodule_name]['change']:
                            role_module_mapping_obj.permissions.add(permission_change.id)
                            update_permission_models.append({role_module_mapping_obj.id: permission_change.id})
                        
                        else:
                            role_module_mapping_obj.permissions.remove(permission_change.id)
            role_obj.save()
            list(map(lambda x: RoleModuleMapping.objects.get(id=list(x.keys())[0]).permissions.add(*x.values()), add_permission_models))
            list(map(lambda x: RoleModuleMapping.objects.get(id=list(x.keys())[0]).permissions.add(*x.values()), view_permission_models))
            list(map(lambda x: RoleModuleMapping.objects.get(id=list(x.keys())[0]).permissions.add(*x.values()), delete_permission_models))
            list(map(lambda x: RoleModuleMapping.objects.get(id=list(x.keys())[0]).permissions.add(*x.values()), update_permission_models))
            role_module_mapping_obj.save()
            return Response(
                'Roles Were Updated',
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                error_response(f'{e} at Module: {module_name} Sub Module: {submodule_name} Model: {model_name} Error At: {traceback.format_exc()}')
            )

class EmployeeRoleAssign(APIView):

    model = Roles
    
    def post(self, request):
        data = request.data
        emp_ids = data.get('employe_ids')
        role_id = data.get('role_id')
        if emp_ids is None:
            return Response(
                {
                    "error": "Please Select Employees"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if role_id is None:
            return Response(
                {
                    "error": "Please Select Role to Assign"
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        role_check = Roles.objects.filter(id = role_id, name='CEO').annotate(
                    emps_count = db_models.Count('roles_employees',distinct=True,filter = db_models.Q(roles_employees__is_deleted=False))
                ).values('emps_count')

        if role_check.exists() and (len(emp_ids) > 1 or role_check.first()['emps_count'] != 0):
            return Response(
                    {
                        "error": "CEO Role Can't be assigned for multiple employees"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        emps = Employee.objects.filter(id__in=emp_ids).select_related('user')
        track = transaction.set_autocommit(autocommit=False)
        
        if Roles.objects.filter(id = role_id, name='EMPLOYEE').exists():
            # man_emp_ids = emps.exclude(roles__name = 'EMPLOYEE').values_list('id',flat=True)
            # EmployeeReportingManager.objects.filter(db_models.Q(manager_id__in = emp_ids) | db_models.Q(employee_id__in = man_emp_ids)).delete()
            EmployeeReportingManager.objects.filter(db_models.Q(manager_id__in = emp_ids)).update(is_deleted=True)
            EmployeeWorkHistoryDetails.objects.filter(manager_id__in=emp_ids, work_to__isnull=True).update(work_to=timezone_now())
            
            
        for emp in emps:
            if emp.user.is_superuser:
                transaction.rollback(track)
                return Response(
                    {
                        "error": f"{emp.first_name} role can't be changed as he is Super Admin"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            emp.roles.clear()
            emp.roles.add(role_id)
            
        transaction.commit()
        return Response(
            {
                "message": "Role Assigned Successfully"
            },
            status=status.HTTP_200_OK
        )

def get_role_data_of_user(role_id, company_id):
    existed_data = RoleModuleMapping.objects.filter(role_id=role_id, company_id=company_id).values(
        'module_id',
        'module__name', 'can_add', 'can_delete', 'can_change', 'can_view',
        'modulesubmodulemapping__submodule__id',
        'modulesubmodulemapping__submodule__name',
        'modulesubmodulemapping__can_add', 'modulesubmodulemapping__can_delete',
        'modulesubmodulemapping__can_change', 'modulesubmodulemapping__can_view',
        )
    existed_data_convert = {
        'modules': {}
    }
    final_output = ROLES_INPUT
    for module_data in existed_data:
        if module_data['module__name'] not in existed_data_convert['modules'].keys():
            existed_data_convert['modules'][module_data['module__name']] = {
                'module_name':  module_data['module__name'],
                'add': False, 'delete': False, 'change': False, 'view': False,
                'submodules': {}
            }
        if module_data['modulesubmodulemapping__submodule__name'] not in existed_data_convert['modules'][module_data['module__name']]['submodules'].keys():
            existed_data_convert['modules'][module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']] = {
                'submodule__name': module_data['modulesubmodulemapping__submodule__name'],
                'add': False, 'delete': False, 'change': False, 'view': False
            }
        existed_data_convert['modules'][module_data[
            'module__name']]['add'] = module_data['can_add']
        existed_data_convert['modules'][
            module_data['module__name']]['delete'] = module_data['can_delete']
        existed_data_convert['modules'][
            module_data['module__name']]['change'] = module_data['can_change']
        existed_data_convert['modules'][
            module_data['module__name']]['view'] = module_data['can_view']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['add'] = module_data['modulesubmodulemapping__can_add']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['change'] = module_data['modulesubmodulemapping__can_change']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['view'] = module_data['modulesubmodulemapping__can_view']
        existed_data_convert['modules'][
            module_data['module__name']]['submodules'][module_data['modulesubmodulemapping__submodule__name']]['delete'] = module_data['modulesubmodulemapping__can_delete']
    for module_name in final_output['modules'].keys():
        # print(module_name)
        if existed_data_convert['modules'].get(module_name):
            final_output['modules'][module_name]['add'] = existed_data_convert['modules'][module_name]['add']
            final_output['modules'][module_name]['delete'] = existed_data_convert['modules'][module_name]['delete']
            final_output['modules'][module_name]['view'] = existed_data_convert['modules'][module_name]['view']
            final_output['modules'][module_name]['change'] = existed_data_convert['modules'][module_name]['change']
            for sub_module in ROLES_INPUT['modules'][module_name]['submodules'].keys():
                # print(sub_module)
                if existed_data_convert['modules'][module_name]['submodules'].get(sub_module):
                    final_output['modules'][module_name]['submodules'][sub_module]['add'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['add']
                    final_output['modules'][module_name]['submodules'][sub_module]['view'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['view']
                    final_output['modules'][module_name]['submodules'][sub_module]['delete'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['delete']
                    final_output['modules'][module_name]['submodules'][sub_module]['change'] = existed_data_convert['modules'][module_name]['submodules'][sub_module]['change']
                if final_output['modules'][module_name]['submodules'][sub_module].get('models'):
                    del final_output['modules'][module_name]['submodules'][sub_module]['models']
                if '-' in sub_module or '&' in sub_module:
                    s_data = final_output['modules'][module_name]['submodules'][sub_module]
                    del final_output['modules'][module_name]['submodules'][sub_module]
                    sub_module = sub_module.replace('-', '_').replace('&', '_')
                    final_output['modules'][module_name]['submodules'][sub_module] = s_data
            sub_mod_data = final_output['modules'][module_name]['submodules']
            del final_output['modules'][module_name]['submodules']
            final_output['modules'][module_name][f'{module_name}_submodules'] = sub_mod_data
        if '-' in module_name or '&' in module_name:
            m_data = final_output['modules'][module_name]
            del final_output['modules'][module_name]
            module_name = module_name.replace('-', '_').replace('&', '_')
            final_output['modules'][module_name] = m_data
    return final_output['modules']

class MobileRolesDataFetch(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    parser_classes = ()
    
    def get(self, request):
        employee = request.user.employee_details.first()
        data = get_role_data_of_user(employee.roles.first().id, employee.company.id)
        
        return Response({
                "success": True,
                "message":  "Data fetched successfuly",
                "data": data
            }, status=status.HTTP_200_OK)
