import logging
import threading
import traceback

from django.conf import settings
from django.contrib.auth import get_user_model

import jwt


logger = logging.getLogger(__name__)


class CurrentUserMiddleware:
    """
    Middleware to load the user accessing the current thread into a local
    memory.

    AJAY, 24.12.2022
    """

    __users = {}
    __current_request = {}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request = self.process_request(request)
        return self.get_response(request)

    def process_request(self, request):
        """
        Store User into current thead when processing a request.

        AJAY, 24.12.2022
        """
        self.__current_request['request'] = request
        try:
            token = request.META.get("HTTP_AUTHORIZATION", " ").split(" ")[1]
            if not token:
                return request

            token_data = jwt.decode(
                token, key=settings.SECRET_KEY, algorithms=["HS256"], verify=False
            )
            user = get_user_model().objects.get(id=token_data.get("user_pk", None))
            if user.is_authenticated:
                request.user = user
                logger.debug(f"Setting request.user, {request.user}")
                self.__class__.set_user(user)
        except Exception:
            traceback.print_exc()
            logger.error(traceback.format_exc())

        return request

    def process_response(self, get_response):
        """
        Delete User from current thread when the request is complete.

        AJAY, 24.12.2022
        """
        self.__class__.clear_user()
        return get_response

    def process_exception(self, request, exception):
        """
        If there is an exception, clear the current User.

        AJAY, 24.12.2022
        """
        self.__class__.clear_user()

    @classmethod
    def get_request_details(cls):
        return cls.__current_request['request']

    @classmethod
    def get_user(cls, default=None):
        """
        Retrieve User from the current thread.

        AJAY, 24.12.2022
        """
        return cls.__users.get(threading.current_thread(), default)

    @classmethod
    def set_user(cls, user):
        """
        Store User into the current thread.

        AJAY, 24.12.2022
        """
        cls.__users[threading.current_thread()] = user

    @classmethod
    def clear_user(cls):
        """
        Clear User from the current thread.

        AJAY, 24.12.2022
        """
        cls.__users.pop(threading.current_thread(), None)

    @classmethod
    def clear_all_users(cls):
        """
        Clear all Users from the current thread.

        AJAY, 24.12.2022
        """
        cls.__users = {}


def get_current_user():
    """
    Return the current User from the CurrentUserMiddleware

    AJAY, 11.05.2023
    """
    return CurrentUserMiddleware.get_user()

def get_request_details():
    return CurrentUserMiddleware.get_request_details()


def clear_current_user():
    """
    Clear all Users from the CurrentUserMiddleware

    AJAY, 11.05.2023
    """
    return CurrentUserMiddleware.clear_user()


def clear_all_users():
    """
    Clear all Users from the CurrentUserMiddleware

    AJAY, 11.05.2023
    """
    return CurrentUserMiddleware.clear_all_users()

