"""
Core Model to be used throughout the System
"""
import traceback
import logging
import json
from collections import ChainMap
from django.apps import apps

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models, connections
# from model_utils import FieldTracker
# from django.db.models.signals import class_prepared, pre_init
from django.utils.translation import gettext_lazy as _

from core.middlewares import get_current_user, get_request_details

from core.utils import get_ip_address

logger = logging.getLogger(__name__)
from core.utils import get_updated_payload_data
logger = logging.getLogger('django')
# models.options.DEFAULT_NAMES = models.options.DEFAULT_NAMES + ("db_prefix",)


def model_prefix(sender, **kwargs):
    """
    If the model has a `db_prefix` attribute, use that, otherwise use the `DB_PREFIX` setting. If
    there's a prefix, prepend it to the model's `db_table` attribute

    :param sender: The model class

    ```refer: https://github.com/anexia/django-model-prefix```

    AJAY, 12.01.2023
    """

    prefix = getattr(settings, "DB_PREFIX", None)

    # Model defined prefix
    if hasattr(sender._meta, "db_prefix"):
        prefix = sender._meta.db_prefix

    if prefix and not sender._meta.db_table.startswith(prefix):
        sender._meta.db_table = prefix + sender._meta.db_table


# pre_init.connect(model_prefix)
# class_prepared.connect(model_prefix)


def get_model_relations_to_delete(opts):
    # The candidate relations are the ones that come from N-1 and 1-1 relations.
    # N-N  (i.e., many-to-many) relations aren't candidates for deletion.
    return (
        f
        for f in opts.get_fields(include_hidden=True)
        if f.auto_created and not f.concrete and (f.one_to_one or f.one_to_many)
    )


class AbstractModelQuerySet(models.QuerySet):
    """
    Overwritten the Django Model QuerySet to be used as a
    default for all QuerySets

    AJAY, 24.12.2022
    """

    def get_created_by(self, user, **kwargs):
        return self.filter(created_by=user, **kwargs)
    
    def update(self, *args, **kwargs):
        
        # print(list(self.values_list('pk', flat=True)))
        try:
            obj = None
            
            try:
                request_module = get_request_details()
                
                data = list(self.model.objects.filter(
                    pk__in=self.values_list('pk', flat=True)
                ).values())
                model_name = self.model._meta.verbose_name 
                obj = apps.get_model("company_profile", "LoggingRecord").objects.create(
                    user=get_current_user(),
                    user_name=get_current_user().username, method=request_module.method,
                    end_point=request_module.build_absolute_uri(),
                    ip_address=get_ip_address(request_module),
                    is_success_entry=True,
                    company_name=get_current_user().employee_details.first().company.company_name,
                    old_data=json.dumps(data, default=str),
                    model_name  = model_name
                )
            except Exception as e:
                # print(e, "Error2", traceback.format_exc())
                ...
        except Exception as e:
            # print(e, "Error3", traceback.format_exc())
            ...

        super().update(*args, **kwargs)
        if obj is not None and request_module.method != "POST":
            payload =  list(self.model.objects.filter(
                        pk__in=self.values_list('pk', flat=True)
                    ).values())
            obj.payload = json.dumps(payload, default=str)
            obj.model_name  = self.model._meta.verbose_name
            obj.save()


class AbstractModelContentTypeQuerySet(models.QuerySet):
    """
    QuerySet for object that use ContentType

    AJAY, 24.12.2022
    """

    def get_for_object(self, obj, **extra_filters):
        obj_ct = ContentType.objects.get_for_model(obj)
        return self.filter(content_type=obj_ct, object_id=obj.pk, **extra_filters)


class AbstractModelManager(models.Manager):
    """
    Overwritten the Django Model Manager to be used as a default
    for all Managers

    AJAY, 24.12.2022
    """

    pass


class AbstractModel(models.Model):
    """
    Overwritten the Django Model to be used as a default for all Models

    AJAY, 24.12.2022
    """

    objects = AbstractModelManager.from_queryset(AbstractModelQuerySet)()

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now=False,
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"), auto_now=True, auto_now_add=False
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Created by"),
        related_name="%(app_label)s_%(class)s_created_by",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Updated by"),
        related_name="%(app_label)s_%(class)s_modified_by",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        editable=False,
    )    

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        try:
            from HRMSApp.models import User
            request_module = get_request_details()
            if 'db_setup' not in request_module.build_absolute_uri():
                # if self._state.adding or self.created_by is None:
                #     self.created_by = get_current_user()
                # if get_current_user() is not None:
                #     self.updated_by = get_current_user()
                user = User.objects.filter(id = get_current_user().id)
                if user:
                    self.updated_by = user.first()
                    if request_module.method == 'POST':
                        self.created_by = user.first()
                          
        except Exception as e:
            pass
        
        obj = None
        
        try:
            request_module = get_request_details()
            if self.pk is not None and request_module.method != "POST" and self.__class__.__name__ != "EmployeeMonthlyAttendanceRecords":
                data = list(self.__class__.objects.filter(
                    pk=self.pk
                ).values())
                print(self.__class__.__name__)
                model_name = self.__class__.objects.model._meta.verbose_name 
                obj = apps.get_model("company_profile", "LoggingRecord").objects.create(
                    user=get_current_user(),
                    user_name=get_current_user().username, method=request_module.method,
                    end_point=request_module.build_absolute_uri(),
                    ip_address=get_ip_address(request_module),
                    is_success_entry=True,
                    company_name=get_current_user().employee_details.first().company.company_name,
                    old_data=json.dumps(data, default=str),
                    model_name  = model_name
                )
        except Exception as e:
            # print(e, "Error", traceback.format_exc())
            ...

        super().save(*args, **kwargs)
        try: 
            request_module = get_request_details()
            if request_module.method == "POST" and self.__class__.__name__ != "EmployeeMonthlyAttendanceRecords":                    
                model_name = self.__class__.objects.model._meta.verbose_name 
                if '/login/' not in request_module.build_absolute_uri():
                    name_of_model = self.__class__.__name__
                    payload_data = self.__class__.objects.filter(
                                    pk=self.pk
                                ).values()
                    if name_of_model in ["AuditorDetails","BankDetails","StatutoryDetails","EmployeeCertifications","EmployeeEducationDetails","EmployeeDocuments",
                                         "EmployeeWorkDetails","EmployeeReportingManager","EmployeeFamilyDetails","EmployeeSalaryDetails","LeavesHistory","EmployeeEmergencyContact",
                                         "EmployeeCheckInOutDetails"]:
                        payload_data = get_updated_payload_data(payload_data,name_of_model)
                    if name_of_model == 'EmployeeCheckInOutDetails':
                        for obj in payload_data:
                            if obj['time_in'] is None:
                                return
                    obj = apps.get_model("company_profile", "LoggingRecord").objects.create(
                        user=get_current_user(),
                        user_name=get_current_user().username, method=request_module.method,
                        end_point=request_module.build_absolute_uri(),
                        ip_address=get_ip_address(request_module),
                        is_success_entry=True,
                        company_name=get_current_user().employee_details.first().company.company_name,
                        # old_data=json.dumps([], default=str),
                        model_name  = model_name,
                        payload=json.dumps(list(payload_data), default=str)
                    )
                    
                else:
                    obj = apps.get_model("company_profile", "LoggingRecord").objects.create(
                        user=self.user,
                        user_name=self.user.username, method=request_module.method,
                        end_point=request_module.build_absolute_uri(),
                        ip_address=get_ip_address(request_module),
                        is_success_entry=True,
                        company_name=get_current_user().employee_details.first().company.company_name,
                        # old_data=json.dumps([], default=str),
                        model_name  = model_name,
                        payload=json.dumps([{'username': self.official_email}], default=str)
                    )
        except Exception as e:
            # print(e, "Error", traceback.format_exc())
            ...
        if obj is not None and request_module.method != "POST":            
            name_of_model = self.__class__.__name__              
            payload_data = self.__class__.objects.filter(
                            pk=self.pk
                        ).values()
            old_data_list = json.loads(obj.old_data)
            if name_of_model in ["AuditorDetails","BankDetails","StatutoryDetails","EmployeeCertifications","EmployeeEducationDetails","EmployeeDocuments",
                                    "EmployeeWorkDetails","EmployeeReportingManager","EmployeeFamilyDetails","EmployeeSalaryDetails","LeavesHistory","EmployeeEmergencyContact"]:  
                payload_data = get_updated_payload_data(payload_data,name_of_model)
                old_data_list = get_updated_payload_data(old_data_list,name_of_model)
            obj.payload = json.dumps(list(payload_data), default=str)
            obj.old_data = json.dumps(old_data_list, default=str)
            obj.model_name  = self.__class__.objects.model._meta.verbose_name
            obj.save()


class Utils:
    # * wrote imports here to avoid circular import

    @staticmethod
    def get_relation_types(relation: str) -> int:
        """
        It takes a relation type value and returns it's integer

        :param relation: The relationship type
        :type relation: str
        :return: The relationship type is being returned.

        AJAY, 25.01.2023
        """
        from directory.models import RelationshipTypes

        relation_types = dict(
            ChainMap(*[{y: x} for x, y in RelationshipTypes.RELATIONSHIP_TYPE_CHOICES])
        )

        return relation_types.get(relation, None)

    @staticmethod
    def get_employee_type(employee_type: str) -> int:
        """
        It takes a employee type value and returns an it's integer

        :param employee_type: str
        :type employee_type: str
        :return: The employee_types dictionary is being returned.

        AJAY, 25.01.2023
        """
        from directory.models import EmployeeTypes

        employee_types = dict(
            ChainMap(*[{y: x} for x, y in EmployeeTypes.EMPLOYEE_TYPE_CHOICES])
        )
        return employee_types.get(employee_type, None)
