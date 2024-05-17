import logging

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


class TimeStampedModelMixin(models.Model):
    """
    Abstract model which adds timestamp fields to any models

    AJAY, 23.11.2022
    """

    created_at = models.DateTimeField(
        verbose_name=_("Created at"), auto_now=False, auto_now_add=True
    )
    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"), auto_now=True, auto_now_add=False
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Saving with update_fields won't save updated_at
        if kwargs.get("update_fields"):
            kwargs["update_fields"] = list(
                set(list(kwargs["update_fields"]) + ["updated_at"])
            )

        super().save(*args, **kwargs)


class AuditedModelMixin(models.Model):
    """
    Abstract model which adds foreign keys to the user model to store the
    creator or the modifier of the recored for auditing purposes

    Fields are made nullable for objects created by Shell
    """

    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(
        verbose_name=_("Created at"), auto_now=False, auto_now_add=True
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
        """
        Overwritting save to ensure the created_by is automatically populated
        """
        # Fallback for the self.created_by
        # Leave this import in here because it is a model level import and will
        # break the model file if you move it to the top
        from django.contrib.auth import get_user_model

        if kwargs.get("update_fields"):
            kwargs["update_fields"] = list(
                set(list(kwargs["update_fields"]) + ["updated_at"])
            )

        UserModel = get_user_model()
        try:
            if self.created_by is None:
                self.created_by = UserModel.objects.get(pk=self.created_by_id)
            self.updated_by = UserModel.objects.get(pk=self.updated_by_id)
        except UserModel.DoesNotExist:
            self.created_by = None
            self.updated_by = None
        # End of fallback

        # TODO: FILL WITH ACCURATE VALUES
        # if self._state.adding and _created_by is None:
        #     self.created_by = current_user
        # if get_current_user() is not None:
        #     self.updated_by = current_user
        super().save(*args, **kwargs)


class UUIDModelMixin(models.Model):
    """
    Abstract model which replaces the default Django primary key field with a
    proper UUID

    AJAY, 24.12.2022
    """

    id = models.IntegerField(
        verbose_name=_("Identifier"),
        primary_key=True,
        editable=False,
        help_text=_("Primiary Key"),
        db_index=True,
    )

    class Meta:
        abstract = True

    def __str__(self):
        return "{}".format(self.id)


class OrderableModelMixin(models.Model):
    """
    Orderable model mixin

    AJAY, 31.01.2023
    """

    ordering = models.IntegerField(verbose_name=_("Ordering"), blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ["ordering"]

    def save(self, *args, **kwargs):
        # Auto calculate ordering
        if self.ordering is None:
            model = self.__class__
            try:
                last = model.objects.order_by("-ordering")[0]
                self.ordering = last.ordering + 1
            except IndexError:
                # This item is first row
                self.ordering = 0

        super().save(*args, **kwargs)
