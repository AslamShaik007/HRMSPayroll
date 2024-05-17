from django.contrib import admin

from .models import (RolesModules, RolesSubModule, 
                    RolesSubmoduleAttachModels, RoleModuleMapping, 
                    RoleSubmoduleModelMapping, ModuleSubmoduleMapping, SubModuleModelLeavelMapping)


@admin.register(RolesModules)
class RolesModuleAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'name')
    search_fields = ('name', '__str__')

@admin.register(RolesSubModule)
class RolesSubModuleAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'name')
    search_fields = ('name', '__str__')

@admin.register(RolesSubmoduleAttachModels)
class RolesSubmoduleAttachModelsAdmin(admin.ModelAdmin):
    list_display = ('id', '__str__', 'name')
    search_fields = ('name', '__str__')

@admin.register(RoleModuleMapping)
class RoleModuleMappingAdmin(admin.ModelAdmin):
    
    def role_name(self, obj):
        return obj.role.name
    
    def module_name(self, obj):
        return obj.module.name
    
    def company_name(self, obj):
        return obj.company.company_name
    
    list_display = ('id', '__str__', 'role_name', 'module_name', 'company_name')
    list_filter = ('role__name', 'module__name', 'company__company_name')
    raw_id_fields = ('role', 'module', 'company')


@admin.register(SubModuleModelLeavelMapping)
class SubModuleModelLeavelMappingAdmin(admin.ModelAdmin):
    
    def model_name(self, obj):
        return self.model.name
    def submodule_name(self, obj):
        return self.submodule.name    
    list_display = ('id', '__str__', 'model_name', 'submodule_name')
    list_filter = ('submodule__name', 'model__name')
    raw_id_fields = ('model', 'submodule')

@admin.register(ModuleSubmoduleMapping)
class ModuleSubmoduleMappingAdmin(admin.ModelAdmin):
    
    def role_name(self, obj):
        return obj.role_module_map.role.name
    
    def module_name(self, obj):
        return obj.role_module_map.module.name
    
    def company_name(self, obj):
        return obj.role_module_map.company.company_name
    
    def submodule_name(self, obj):
        return obj.submodule.name
    
    list_display = ('id', '__str__', 'role_name', 'module_name', 'company_name', 'submodule_name')
    list_filter = ('role_module_map__role__name', 'role_module_map__module__name', 'role_module_map__company__company_name', 'submodule__name')
    raw_id_fields = ('role_module_map', 'submodule')

@admin.register(RoleSubmoduleModelMapping)
class RoleSubmoduleModelMappingAdmin(admin.ModelAdmin):
    
    def role_name(self, obj):
        return obj.mod_sub_map.role.name
    
    def module_name(self, obj):
        return obj.mod_sub_map.module.name
    
    def company_name(self, obj):
        return obj.mod_sub_map.company.company_name
    
    list_display = ('id', '__str__', 'role_name', 'module_name', 'company_name')
    list_filter = ('mod_sub_map__role_module_map__role__name', 'mod_sub_map__role_module_map__module__name', 'mod_sub_map__role_module_map__company__company_name')
    raw_id_fields = ('mod_sub_map', 'model')
