import contextlib

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class QuerysetFilterSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = data.filter(is_deleted=False)
        return super().to_representation(data)


class ContentTypeRelatedField(serializers.RelatedField):
    """
    Related field for grabbing the ContentType using
    the app_label and model

    AJAY, 05.05.2023
    """

    queryset = ContentType.objects.all()
    default_error_messages = {
        "does_not_exist_1": _(
            "ContentType with app_label={app_label}, model={model} " "does not exist."
        ),
        "does_not_exist_2": _("ContentType with pk={pk} " "does not exist."),
        "found_two_types": _(
            "Multiple models named {model} exists. " "Please specify an app_label."
        ),
        "invalid": _("Invalid value."),
    }

    def to_internal_value(self, data):
        """
        Internal value that will be parsed
        by the serializer into an object

        AJAY, 05.05.2023
        """
        if data:
            if isinstance(data, dict):
                try:
                    return self.get_queryset().get(
                        app_label=data["app_label"], model=data["model"]
                    )
                except ObjectDoesNotExist:
                    self.fail(
                        "does_not_exist_1",
                        app_label=data["app_label"],
                        model=data["model"],
                    )
            elif isinstance(data, str):
                try:
                    return self.get_queryset().get(pk=data)
                except ObjectDoesNotExist:
                    self.fail(
                        "does_not_exist_2",
                        pk=data,
                    )
                except ValueError:
                    try:
                        return self.get_queryset().get(model=data)
                    except MultipleObjectsReturned:
                        self.fail(
                            "found_two_types",
                            model=data,
                        )
        self.fail("invalid")

    def to_representation(self, obj):
        with contextlib.suppress(AttributeError):
            return obj.model_class().__name__
        return None

class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super(DynamicFieldsModelSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields.keys())
            for field_name in existing - allowed:
                self.fields.pop(field_name)