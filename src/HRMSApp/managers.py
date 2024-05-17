from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

from core.models import (
    AbstractModelContentTypeQuerySet,
    AbstractModelManager,
    AbstractModelQuerySet,
)


class UserQuerySet(AbstractModelQuerySet):
    """
    QuerySet for Users

    AJAY, 28.12.2022
    """

    ...


class UserManager(BaseUserManager):
    def _create_user(self, email=None, username=None, password=None, **extra_fields):
        """
        creates and saves a User with the given
        Email, Username and password.

        AJAY, 28.12.2022
        """
        if email:
            email = self.normalize_email(email)

        if username:
            username = self.model.normalize_username(username)

        user = self.model(email=email, username=username, **extra_fields)

        user.set_password(password)

        user.save()
        return user

    def create_user(self, email=None, username=None, password=None, **extra_fields):
        """
        creates and saves a User with the given Email, Username and password.
        without Staff or SuperUser permissions.

        AJAY, 28.12.2022
        """
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)

        return self._create_user(email, username, password, **extra_fields)

    def create_superuser(self, email, username, password, **extra_fields):
        """
        creates and saves a Super User with the given
        email, username and password.

        AJAY, 28.12.2022
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must has is_staff=True"))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must has is_superuser=True"))
        return self._create_user(email, username, password, **extra_fields)


UserManager = UserManager.from_queryset(UserQuerySet)


class CountryQuerySet(AbstractModelQuerySet):
    """
    Country QuerySet

    AJAY, 26.12.2022
    """

    def get_by_symbol(self, symbol, **kwargs):
        """
        Get country object by symbol

        AJAY, 26.12.2022
        """
        return self.get(symbol=symbol, **kwargs)


class CountryModelManager(AbstractModelManager):
    """
    Country Model Manager

    AJAY, 26.12.2022
    """

    ...


CountryManager = CountryModelManager.from_queryset(CountryQuerySet)


class RoleQuerySet(AbstractModelQuerySet):
    ...


class RoleModelManager(AbstractModelManager):
    ...


RoleManager = RoleModelManager.from_queryset(RoleQuerySet)


#####################
# Attachment Stuff
#####################


class AttachmentQuerySet(AbstractModelQuerySet, AbstractModelContentTypeQuerySet):
    """
    Queryset for Attachment.

    AJAY, 04.05.2023
    """

    pass


class AttachmentModelManager(AbstractModelManager):
    """
    Model manager for Attachment.

    AJAY, 04.05.2023
    """

    pass


AttachmentManager = AttachmentModelManager.from_queryset(AttachmentQuerySet)
