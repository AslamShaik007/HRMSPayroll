"""
Django settings for HRMSProject project.

Generated by 'django-admin startproject' using Django 4.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

from kombu import Exchange, Queue


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

###############################################################################
# FOLDER DEFINITIONS
###############################################################################

BASE_DIR = Path(__file__).resolve().parent.parent

SRC_DIR = os.path.dirname(BASE_DIR)
PROJECT_DIR = os.path.dirname(BASE_DIR.parent)

LOG_FILE = "debug.log"
LOG_PATH = BASE_DIR.parent / LOG_FILE

if not os.path.exists(LOG_PATH):
    f = open(LOG_PATH, "a").close()


# LOGS_DIR = os.path.join(PROJECT_DIR, "logs")
PUBLIC_DIR = os.path.join(PROJECT_DIR, "public")
STATIC_DIR = os.path.join(PUBLIC_DIR, "static")
MEDIA_DIR = os.path.join(PUBLIC_DIR, "media")

FOLDER_CREATION_CHECK = [PUBLIC_DIR, STATIC_DIR, MEDIA_DIR]

for FOLDER in FOLDER_CREATION_CHECK:
    if not os.path.exists(FOLDER):
        os.makedirs(FOLDER)


###############################################################################
# STATIC / MEDIA
###############################################################################
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
STATIC_ROOT = STATIC_DIR
MEDIA_ROOT = MEDIA_DIR
REPORT_MEDIA_URL = MEDIA_URL

# STATICFILES_DIRS = (os.path.join(SRC_DIR, "static"),)
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)

COMPRESS_ENABLED = True
COMPRESS_URL = STATIC_URL
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.rCSSMinFilter",  # This will compress the CSS, uncomment it for debugging.
]
COMPRESS_JS_FILTERS = [
    "compressor.filters.jsmin.JSMinFilter",  # This will compress the JS, uncomment it for debugging.
]



###############################################################################
# APPLICATION DEFINITION
###############################################################################

SITE_ID = 1

SITE_NAME = ["pss", "hrms"]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "django_filters",
    "django_chunk_upload_handlers",
    "django_extensions",
]

EXTERNAL_LIBS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "django_celery_beat",
    "django_celery_results",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "post_office",
    "compressor",
    "drf_yasg",
    "whitenoise.runserver_nostatic",  # changed
    "crispy_forms",
    "django_crontab",
    "storages"
]

PSS_APPS = [
    "HRMSApp",
    "company_profile",
    "core",
    "directory",
    "choices",
    "reports",
    "leave",
    "pss_calendar",
    "attendance",
    "payroll",
    "investment_declaration",
    "performance_management",
    "roles",
    "billing",
    "support",
    "alerts",
    "onboarding"
]

INSTALLED_APPS = DJANGO_APPS + EXTERNAL_LIBS + PSS_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # changed
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "HRMSProject.router_middleware.XHeaderMiddleware",
    "HRMSProject.logging_middileware.LogggingMiddleware",
    "core.middlewares.CurrentUserMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "core.backends.LoginBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "HRMSProject.urls"

###############################################################################
# TEMPLATE DEFINITION
###############################################################################

template_dirs = [
    os.path.join(BASE_DIR.parent, "templates"),
    # os.path.join(BASE_DIR, "HRMSApp/templates"),
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": template_dirs,
        # "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        },
    },
]

WSGI_APPLICATION = "HRMSProject.wsgi.application"

###############################################################################
# DB SETTINGS
###############################################################################

# https://docs.djangoproject.com/en/4.0/ref/settings/#databases


DB_PREFIX = "tbl_"

###############################################################################
# REST FRAMEWORK SETTINGS
###############################################################################

# JWT Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "core.permissions.ActionBasedPermission",    
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
        "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
        # Any other renders
    ),
    "DEFAULT_PARSER_CLASSES": (
        # If you use MultiPartFormParser or FormParser, we also have a camel case version
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        # Any other parsers
    ),
    "JSON_UNDERSCOREIZE": {
        "no_underscore_before_number": True,
    },
    "DATE_INPUT_FORMATS": ["%d-%m-%Y", "%d/%m/%Y"],
}

###############################################################################
# PASSWORD VALIDATORS & ADMIN SETTINGS
###############################################################################

# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

ADMIN_DEFAULT_PASSWORD = "pss@2023!"
ADMIN_URL_PATH = "pss-hrms-admin"
ADMIN_SHOW = False


###############################################################################
# INTERNATIONALIZATION & LOCALIZATION - Default to IND format
###############################################################################

DATE_INPUT_FORMATS = [
    "%d-%m-%Y",  # '10-01-2023'
    "%Y-%m-%d",  # '2023-01-10'
    "%d/%m/%Y",  # '10/01/2023'
    # "%Y/%m/%d",  # '2023/01/10'
]
TIME_INPUT_FORMATS = [
    "%H:%M:%S",  # '14:30:59'
    "%H:%M",  # '14:30'
    "%I:%M %P",  # '4:30 AM'
    "%I:%M %p",  # '4:30 pm'
    "g.i a",  # '4.30 a.m.'
]

DATE_FORMAT = "d-m-Y"  # '10-01-2023'
TIME_FORMAT = "g.i a"  # '4.30 p.m.'
DATETIME_FORMAT = "d-m-Y g.i a"  # '10-01-2023 4.30 p.m.'

SHORT_DATE_FORMAT = "d/m/Y"  # '10/01/2023'
SHORT_DATETIME_FORMAT = "d/m/Y g.i a"  # '10/01/2023 4.30 p.m.'

LONG_DATETIME_FORMAT = "d/m/Y H:i"  # '10/01/2023 16:30:00'

DATE_INPUT_FORMAT = "d-m-Y"  # '10-01-2023'
TIME_INPUT_FORMAT = "g.i a"  # '4.30 p.m.'
DATETIME_INPUT_FORMAT = "d-m-Y g.i a"  # '10-01-2023 4.30 p.m.'


def generate_datetime_input_formats(date_input_formats, time_input_formats):
    """
    Generate the Datetime Input Formats from the DATE_INPUT_FORMAT and the
    TIME_INPUT_FORMAT

    AJAY, 10.01.2023
    """
    datetime_input_formats = tuple()
    for dif in date_input_formats:
        datetime_input_formats += (f"{dif}",)
        for tif in time_input_formats:
            datetime_input_formats += (f"{dif} {tif}",)
    return datetime_input_formats


DATETIME_INPUT_FORMATS = generate_datetime_input_formats(
    DATE_INPUT_FORMATS, TIME_INPUT_FORMATS
)

# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_L10N = False
USE_TZ = True


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "HRMSApp.User"

###############################################################################
# EMAIL CONFIGURATION
###############################################################################

# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mail.vitelglobal.in"
EMAIL_PORT = 587
EMAIL_HOST_USER = "enquiry@vitelglobal.in"
EMAIL_HOST_PASSWORD = "Hy8c&Zcj5$wU"
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "enquiry@vitelglobal.in"

###############################################################################
# POST_OFFICE SETTINGS
###############################################################################

POST_OFFICE = {"DEFAULT_PRIORITY": "medium", "LOG_LEVEL": 2}

###############################################################################
# GOOGLE CAPTCHA SETTINGS
###############################################################################

RECAPTCHA_PUBLIC_KEY = "6LdsweIhAAAAALygpi_2lGLVhyEJScocu-nXLOdL"
RECAPTCHA_PRIVATE_KEY = "6LdsweIhAAAAABR-NiDbdLnm4I4TSA9Ys51SHIQ5"

RECAPTCHA_REUIRED_SCORE = 0.85

###############################################################################
# JWT SETTINGS
###############################################################################

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=3600),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "pk",
    "USER_ID_CLAIM": "user_pk",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
}

PASSWORD_RESET_TIMEOUT = 86400  # 1 Day


###############################################################################
# CORS CONFIGURATION
###############################################################################

# ALLOWED_HOSTS = ["localhost"]
CORS_ALLOW_METHODS = (
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
)
CORS_ALLOW_HEADERS = (
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "Access-Control-Allow-Origin",
    "cache-control",
    "expires",
    "x-total-count",
    "X-CURRENT-COMPANY",
    "X-SELECTED-COMPANY"
)

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = False
CORS_ORIGIN_WHITELIST = []
CORS_URLS_REGEX = r"^/api/.*$"


###############################################################################
# Session Security Settings
###############################################################################

SESSION_SECURITY_ENABLED = False
SESSION_SECURITY_WARN_AFTER = 1770  # Warning 30 seconds before auto logout
SESSION_SECURITY_EXPIRE_AFTER = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_COOKIE_SECURE = False  # while move in to production change it to True
SESSION_COOKIE_HTTPONLY = True
# SESSION_COOKIE_DOMAIN = None

# MEDIA_ROOT = BASE_DIR / "media"


###############################################################################
# FILE Settings
###############################################################################

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


###############################################################################
# FILE EXTENSIONS SETTINGS
###############################################################################

ALLOWED_FILE_EXTENSIONS = [
    ".PNG",
    ".JPG",
    ".JPEG",
    ".GIF",
    ".PDF",
    ".DOC",
    ".DOCX",
    ".XLS",
    ".XLSX",
    ".PPT",
    ".PPTX",
    ".TXT",
    ".CSV",
    ".ZIP",
    ".MSG",
]

# additional validation by checking the file type
ALLOWED_MIME_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/csv",
    "application/zip",
    "application/vnd.ms-outlook",
    "application/CDFV2",
    "application/CDFV2-encrypted",
    "application/CDFV2-unknown",
    "application/CDFV2-corrupt",
)


FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760


###############################################################################
# TOTP Settings
###############################################################################

OTP_TOTP_ISSUER = "issuer_hrms@pss.com"

##############################################################################
# CACHES SETTINGS
##############################################################################


# Need to run python manage.py createcachetable
def make_key(key, key_prefix, version):
    return ":".join([key_prefix, str(version), str(key)]).replace(" ", "_")


DEFAULT_CACHE_TIMEOUT = 3000


###############################################################################
# SWAGGER SETTINGS
###############################################################################
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {"basic": {"type": "basic"}},
    "VALIDATOR_URL": "http://localhost:8189",
}

REDOC_SETTINGS = {"LAZY_RENDERING": True, "REQUIRED_PROPS_FIRST": False}

###############################################################################
# CELERY SETTINGS
###############################################################################

# CELERY_BROKER_URL = "localhost"

# Celery settings
BROKER_URL = "redis://localhost:6379"
CELERY_RESULT_BACKEND = "redis://localhost:6379"

# CELERY_BROKER_POOL_LIMIT = 1
# CELERY_BROKER_CONNECTION_TIMEOUT = 10

# configure queues, currently we have only one
# CELERY_DEFAULT_QUEUE = "default"
# CELERY_QUEUES = (Queue("default", Exchange("default"), routing_key="default"),)

# Sensible settings for celery
# CELERY_ALWAYS_EAGER = False
# CELERY_ACKS_LATE = True
# CELERY_TASK_PUBLISH_RETRY = True
# CELERY_DISABLE_RATE_LIMITS = False

# CELERY_RESULT_BACKEND = "django-db"
# CELERY_CACHE_BACKEND = "default"

# Don't use pickle as serializer, json is much safer
# CELERY_TASK_SERIALIZER = "json"
# CELERY_ACCEPT_CONTENT = ["application/json"]

# CELERYD_HIJACK_ROOT_LOGGER = False
# CELERYD_PREFETCH_MULTIPLIER = 1
# CELERYD_MAX_TASKS_PER_CHILD = 1000

# DJANGO_CELERY_RESULTS_TASK_ID_MAX_LENGTH = 191

DRF_NESTED_MULTIPART_PARSER = {
	"separator": "bracket",	
    # "querydict": True,
}

# save logs in a file
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message} {filename} {lineno}",
            # 'datefmt' : "%d/%b/%Y %H:%M:%S"
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": {
        # 'null': {
        #     'level':'DEBUG',
        #     'class':'django.utils.log.NullHandler',
        # },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            # 'filters': ['require_debug_true'],
            "filename": LOG_PATH,
            "maxBytes": 1024 * 1024 * 1,  # 1MB
            # 'backupCount': 10,
            "formatter": "standard",
        },
        # 'console':{
        #     'level':'INFO',
        #     'class':'logging.StreamHandler',
        #     'formatter': 'standard'
        # },
    },
    "loggers": {
        "django": {"handlers": ["file"], "propagate": True},
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        #     'propagate': False,
        # },
        # 'MYAPP': {
        #     'handlers': ['console', 'logfile'],
        #     'level': 'DEBUG',
        # },
    },
}

WHITELIST_PATH = []

SHELL_PLUS_PRE_IMPORTS = (
    ('django.contrib.postgres.aggregates', '*'),
    'from django.db import models as db_models',
    'from core.utils import *',
    'from django.db import models'
)

twilio_account_sid='AC706f366060ffc42e59e3943b0854282d'
twilio_auth_token='1ec51087621c714c46092158e637607d'


CRONJOBS = [
    ('*/1 * * * *', f'alerts.cron.calling_alerts', f'>> {BASE_DIR.parent}/logs/cron.log 2>&1'),
]

