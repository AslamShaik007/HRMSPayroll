import os
import sys

import django

sys.path.append('./')

from roles import models as role_models
from roles.utils import ROLES_INPUT
import logging
import copy
logger = logging.getLogger('django')


class RoleModuleMappingsOnInitial:
    """
    Generate All modules, submodules, models, mappings 
    """
    module_names = list(ROLES_INPUT['modules'])
    mods = copy.deepcopy(ROLES_INPUT['modules'])
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

    def main(self, environment, db_name):
        environment = environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
        django.setup()
        django.db.connections.databases['default']['NAME'] = db_name
        logger.critical(f'HRMSProject.settings.{environment}')
        self.fetch_all_submodules()
        logger.critical(f'sub modules {self.submodule_names}')
        self.get_or_create_modules()
        logger.critical("role modules start")
        logger.critical(role_models.RolesModules.objects.filter().count())
        logger.critical("role modules end")
        logger.critical("sub modules start")
        self.get_or_create_submodules()
        logger.critical(role_models.RolesSubModule.objects.filter().count())
        logger.critical("sub modules end")
        logger.critical("models start")
        self.get_or_create_models()
        logger.critical(role_models.RolesSubmoduleAttachModels.objects.filter().count())
        logger.critical("models end")
        self.module_ids = list(role_models.RolesModules.objects.values_list('id', flat=True))
        logger.critical(f"mod ids {self.module_ids}")
        self.submodule_ids = list(role_models.RolesSubModule.objects.values_list('id', flat=True))
        logger.critical(f"submod ids {self.submodule_ids}")
        self.model_ids = list(role_models.RolesSubmoduleAttachModels.objects.values_list('id', flat=True))
        logger.critical(f"model ids { self.model_ids}")
        for module_name, module in self.mods.items():
            logger.critical(module_name)
            module_obj = role_models.RolesModules.objects.filter(name=module_name)
            logger.critical(module_obj.exists())
            if module_obj.exists():
                logger.critical("inside module exists")
                module_obj = module_obj.first()
                logger.critical(module['submodules'].items())
                for submodule_name, submodule_data in module['submodules'].items():
                    logger.critical("inside submodule items")
                    submodel_obj = role_models.RolesSubModule.objects.filter(name=submodule_name)
                    logger.critical(f"sub module name {submodule_name}")
                    if submodel_obj.exists():
                        logger.critical("sub module exists")
                        submodel_obj = submodel_obj.first()
                        logger.critical(module['submodules'][submodule_name])
                        for model_name in module['submodules'][submodule_name].get('models', []):
                            logger.critical("before role submodule attach models")
                            model_obj = role_models.RolesSubmoduleAttachModels.objects.filter(name=model_name)
                            if model_obj.exists():
                                logger.critical("model obj exists")
                                role_models.SubModuleModelLeavelMapping.objects.get_or_create(
                                    model_id=model_obj.first().id, submodule_id=submodel_obj.id
                                )
                                logger.critical("submodule level mapping created")
                            else:
                                print(module_name, submodule_name, model_name)

def module_sub_creation(environment,db_name):
    obj = RoleModuleMappingsOnInitial()
    obj.main(environment, db_name)

import os
import sys

import django

sys.path.append('./')

from roles import models as role_models
from roles.utils import ROLES_INPUT
import logging
import copy
logger = logging.getLogger('django')


class RoleModuleMappingsOnInitial:
    """
    Generate All modules, submodules, models, mappings 
    """
    module_names = list(ROLES_INPUT['modules'])
    mods = copy.deepcopy(ROLES_INPUT['modules'])
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

    def main(self, environment, db_name):
        environment = environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
        django.setup()
        django.db.connections.databases['default']['NAME'] = db_name
        logger.critical(f'HRMSProject.settings.{environment}')
        self.fetch_all_submodules()
        logger.critical(f'sub modules {self.submodule_names}')
        self.get_or_create_modules()
        logger.critical("role modules start")
        logger.critical(role_models.RolesModules.objects.filter().count())
        logger.critical("role modules end")
        logger.critical("sub modules start")
        self.get_or_create_submodules()
        logger.critical(role_models.RolesSubModule.objects.filter().count())
        logger.critical("sub modules end")
        logger.critical("models start")
        self.get_or_create_models()
        logger.critical(role_models.RolesSubmoduleAttachModels.objects.filter().count())
        logger.critical("models end")
        self.module_ids = list(role_models.RolesModules.objects.values_list('id', flat=True))
        logger.critical(f"mod ids {self.module_ids}")
        self.submodule_ids = list(role_models.RolesSubModule.objects.values_list('id', flat=True))
        logger.critical(f"submod ids {self.submodule_ids}")
        self.model_ids = list(role_models.RolesSubmoduleAttachModels.objects.values_list('id', flat=True))
        logger.critical(f"model ids { self.model_ids}")
        for module_name, module in self.mods.items():
            logger.critical(module_name)
            module_obj = role_models.RolesModules.objects.filter(name=module_name)
            logger.critical(module_obj.exists())
            if module_obj.exists():
                logger.critical("inside module exists")
                module_obj = module_obj.first()
                logger.critical(module['submodules'].items())
                for submodule_name, submodule_data in module['submodules'].items():
                    logger.critical("inside submodule items")
                    submodel_obj = role_models.RolesSubModule.objects.filter(name=submodule_name)
                    logger.critical(f"sub module name {submodule_name}")
                    if submodel_obj.exists():
                        logger.critical("sub module exists")
                        submodel_obj = submodel_obj.first()
                        logger.critical(module['submodules'][submodule_name])
                        for model_name in module['submodules'][submodule_name].get('models', []):
                            logger.critical("before role submodule attach models")
                            model_obj = role_models.RolesSubmoduleAttachModels.objects.filter(name=model_name)
                            if model_obj.exists():
                                logger.critical("model obj exists")
                                role_models.SubModuleModelLeavelMapping.objects.get_or_create(
                                    model_id=model_obj.first().id, submodule_id=submodel_obj.id
                                )
                                logger.critical("submodule level mapping created")
                            else:
                                print(module_name, submodule_name, model_name)

def module_sub_creation(environment,db_name):
    obj = RoleModuleMappingsOnInitial()
    obj.main(environment, db_name)
