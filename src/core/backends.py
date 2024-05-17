import logging
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest


UserModel = get_user_model()
logger = logging.getLogger(__name__)


class LoginBackend(ModelBackend):
    """
    Logind backend to authenticate user

    AJAY, 26.12.2022
    """

    def authenticate(
        self, request: HttpRequest, password: Optional[str] = ..., **kwargs: Any
    ) -> Optional[AbstractBaseUser]:
        """
        authenticator backend

        AJAY, 26.12.2022
        """
        user = None
        try:
            user = UserModel.objects.get(email=kwargs.get("email", ""))
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
            return user

        if user.check_password(password):
            return user

        return None