import os
import sys

import django

sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    django.db.connections.databases['default']['NAME'] = sys.argv[-1]

from roles import models as role_models
from roles.utils import ROLES_INPUT


class RoleModuleMappingsOnInitial:
    """
    Generate All modules, submodules, models, mappings 
    """
    module_names = list(ROLES_INPUT['modules'])
    submodule_names = []
    module_ids = []
    submodule_ids = []
    model_ids = []
    
    def fetch_all_submodules(self):
        [self.submodule_names.extend(list(ROLES_INPUT['modules'][module_name]['submodules'])) for module_name in ROLES_INPUT['modules'].keys()]

    
    def get_or_create_modules(self):
        list(map(lambda module_name: role_models.RolesModules.objects.get_or_create(
                name=module_name
            ), self.module_names))
    def get_or_create_submodules(self):
        
        list(map(lambda submodule_name: role_models.RolesSubModule.objects.get_or_create(
                name=submodule_name
            ), self.submodule_names))

    def get_or_create_models(self):
        list(map(lambda x: role_models.RolesSubmoduleAttachModels.objects.get_or_create(name=x.__name__), django.apps.apps.get_models()))

    def main(self):
        self.fetch_all_submodules()
        self.get_or_create_modules()
        self.get_or_create_submodules()
        self.get_or_create_models()
        self.module_ids = list(role_models.RolesModules.objects.values_list('id', flat=True))
        self.submodule_ids = list(role_models.RolesSubModule.objects.values_list('id', flat=True))
        self.model_ids = list(role_models.RolesSubmoduleAttachModels.objects.values_list('id', flat=True))
        for module_name, module in ROLES_INPUT['modules'].items():
            module_obj = role_models.RolesModules.objects.filter(name=module_name)
            if module_obj.exists():
                module_obj = module_obj.first()
                for submodule_name, submodule_data in module['submodules'].items():
                    submodel_obj = role_models.RolesSubModule.objects.filter(name=submodule_name)
                    if submodel_obj.exists():
                        submodel_obj = submodel_obj.first()
                        for model_name in module['submodules'][submodule_name].get('models', []):
                            model_obj = role_models.RolesSubmoduleAttachModels.objects.filter(name=model_name)
                            if model_obj.exists():
                                role_models.SubModuleModelLeavelMapping.objects.get_or_create(
                                    model_id=model_obj.first().id, submodule_id=submodel_obj.id
                                )
                            else:
                                print(module_name, submodule_name, model_name)

if __name__ == "__main__":
    RoleModuleMappingsOnInitial().main()

