from django.db import models
from django.contrib.auth.models import Permission
from core.models import AbstractModel

from HRMSApp.models import Roles, CompanyDetails


class BasicPermissionsModel(models.Model):
    can_view = models.BooleanField(default=False, null=True, blank=True)
    can_add = models.BooleanField(default=False, null=True, blank=True)
    can_delete = models.BooleanField(default=False, null=True, blank=True)
    can_change = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        abstract = True

class RolesModules(AbstractModel):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name

class RolesSubModule(AbstractModel):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name

class RolesSubmoduleAttachModels(AbstractModel):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name

class RoleModuleMapping(AbstractModel, BasicPermissionsModel):
    role = models.ForeignKey(Roles, on_delete=models.CASCADE, null=True, blank=True)
    module = models.ForeignKey(RolesModules, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, null=True, blank=True)
    permissions = models.ManyToManyField(Permission, default=[])
    
    def __str__(self):
        return f'Company: {self.company.company_name} :: Role: {self.role.name} :: Module: {self.module.name}'

class ModuleSubmoduleMapping(AbstractModel, BasicPermissionsModel):
    role_module_map = models.ForeignKey(RoleModuleMapping, on_delete=models.CASCADE)
    submodule = models.ForeignKey(RolesSubModule, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'Role -> {self.role_module_map.role.name} - Module - {self.role_module_map.module.name} SubModule - {self.submodule.name}'


class RoleSubmoduleModelMapping(AbstractModel, BasicPermissionsModel):
    mod_sub_map = models.ForeignKey(ModuleSubmoduleMapping, on_delete=models.CASCADE)
    model = models.ForeignKey(RolesSubmoduleAttachModels, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.mod_sub_map.role_module_map.role.name}->M-{self.mod_sub_map.role_module_map.module.name}->sm-{self.mod_sub_map.submodule.name} - Model {self.model.name}'


class SubModuleModelLeavelMapping(AbstractModel):
    model = models.ForeignKey(RolesSubmoduleAttachModels, on_delete=models.CASCADE)
    submodule = models.ForeignKey(RolesSubModule, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'SubModule - {self.submodule.name} -> Model - {self.model.name}'
