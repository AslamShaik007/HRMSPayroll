import os
import sys

import django

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()

from django.contrib.auth.models import Permission
from HRMSApp.models import Roles
from core.utils import generate_random_string
from roles import models as role_models
from roles.utils import ROLES_INPUT


def role_creation():
    roles_data =Roles.DEFAULT_ADMIN_ROLES

    for role_name in roles_data:
        role = Roles.objects.filter(
            name=role_name
        )
        if not role.exists():
            code_name = f'{role_name.lower()}-{generate_random_string()}'
            Roles.objects.create(
                name=role_name,
                slug=code_name.lower(),
                code=code_name.upper()
            )
role_creation()

def role_company_module_setup(company_id, role_id):
    module_names = list(ROLES_INPUT['modules'])
    submodule_names = []
    modules = role_models.RolesModules.objects.filter(name__in=module_names).values_list('id', flat=True)
    [submodule_names.extend(list(ROLES_INPUT['modules'][module_name]['submodules'])) for module_name in ROLES_INPUT['modules'].keys()]
    for module in modules:
        role_module_map, role_module_map_created = role_models.RoleModuleMapping.objects.get_or_create(
            module_id=module,
            role_id=role_id,
            company_id=company_id,
            can_add=True,
            can_change=True,
            can_view=True,
            can_delete=True
        )
        submodules = role_models.RolesSubModule.objects.filter(name__in=list(ROLES_INPUT['modules'][
                role_module_map.module.name
            ]['submodules'])).values_list('id', flat=True)
        for submodule in submodules:
            module_submodule_map, module_submodule_map_created = role_models.ModuleSubmoduleMapping.objects.get_or_create(
                role_module_map_id=role_module_map.id,
                submodule_id=submodule,
                can_add=True,
                can_change=True,
                can_view=True,
                can_delete=True
            )
            submod_models = role_models.SubModuleModelLeavelMapping.objects.filter(submodule_id=module_submodule_map.submodule.id).values(
                'model_id', 'model__name'
            )
            for model in submod_models:
                role_models.RoleSubmoduleModelMapping.objects.get_or_create(
                    mod_sub_map_id=module_submodule_map.id, model_id=model['model_id'],
                    can_add=True,
                    can_change=True,
                    can_view=True,
                    can_delete=True
                )
                permission_add = Permission.objects.get(codename=f'add_{model["model__name"]}'.lower())
                permission_view = Permission.objects.get(codename=f'view_{model["model__name"]}'.lower())
                permission_delete = Permission.objects.get(codename=f'delete_{model["model__name"]}'.lower())
                permission_change = Permission.objects.get(codename=f'change_{model["model__name"]}'.lower())
                role_module_map.permissions.add(permission_add.id)
                role_module_map.permissions.add(permission_view.id)
                role_module_map.permissions.add(permission_change.id)
                role_module_map.permissions.add(permission_delete.id)
    print("role_module_map_created", role_module_map_created, "module_submodule_map_created", module_submodule_map_created, )
    
