from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-secure-$p=9m6)dmeczf)axogo(qtl5jve8!0lbxr9l!*jdu&1ho)44ksas"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Allow traffic from all IPs
ALLOWED_HOSTS = ["*"]



###############################################################################
# DB SETTINGS
###############################################################################

# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {

    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'indianhrms_db',
        'USER': 'root',
        'PASSWORD': 'cjKMN554pRLnKhd3dbYcvGVDpHZ6B2TA7',
        'HOST': 'localhost',
        'PORT': 5432,
    }
}


###############################################################################
# REST FRAMEWORK SETTINGS
###############################################################################


WHITELIST_PATH = []



###############################################################################
# EMAIL CONFIGURATION
###############################################################################

# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "mail.vitelglobal.in"
# EMAIL_HOST = "mail.bharatpayroll.com"
# EMAIL_PORT = 587
# EMAIL_HOST_USER = "enquiry@vitelglobal.in"
# EMAIL_HOST_PASSWORD = "Hy8c&Zcj5$wU"
# EMAIL_HOST_USER = "noreply@bharatpayroll.com"
# EMAIL_HOST_PASSWORD = "Uaw3XHa1xjlTyjIP"
# EMAIL_USE_TLS = True
# DEFAULT_FROM_EMAIL = "noreply@bharatpayroll.com"



EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "mail.vitelglobal.com"
EMAIL_PORT = 465
EMAIL_HOST_USER = "noreply"
EMAIL_HOST_PASSWORD = "Uaw3XHa1xjlTyjIP"
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = "noreply@bharatpayroll.com"


# EMAIL_BACKEND = "post_office.EmailBackend"
# EMAIL_HOST = "mail.vitelglobal.in"
# EMAIL_HOST_USER = "enquiry@vitelglobal.in"
# EMAIL_HOST_PASSWORD = "Hy8c&Zcj5$wU"
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# DEFAULT_REPLY_TO = None
# DEFAULT_FROM_EMAIL = "enquiry@vitelglobal.in"


###############################################################################
# GOOGLE CAPTCHA SETTINGS
###############################################################################

RECAPTCHA_PUBLIC_KEY = "6LcsKHcmAAAAACPCsu9hufJrRq9e4cMS9LdhVan0"
RECAPTCHA_PRIVATE_KEY = "6LcsKHcmAAAAAMODgd0sXg7sy_X4H1saALPa7APw"

RECAPTCHA_REUIRED_SCORE = 0.85


###############################################################################
# CORS CONFIGURATION
###############################################################################

# Allow CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://38.143.106.249:3000",
    "http://38.143.106.249",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://38.143.106.249:3000",
    "http://38.143.106.249",
]


CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_WHITELIST = []

###############################################################################
# Session Security Settings
###############################################################################

SESSION_SECURITY_ENABLED = False
SESSION_SECURITY_WARN_AFTER = 1770  # Warning 30 seconds before auto logout
SESSION_SECURITY_EXPIRE_AFTER = 1800  # 30 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True  # while move in to production change it to True
# SESSION_COOKIE_DOMAIN = None


##############################################################################
# CACHES SETTINGS
##############################################################################


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "hrms_cache",
        "KEY_FUNCTION": "HRMSProject.settings.prod.make_key",
        "TIMEOUT": DEFAULT_CACHE_TIMEOUT,
    }
}


###############################################################################
# CELERY SETTINGS
###############################################################################

# CELERY_BROKER_URL = "localhost"


# # Sensible settings for celery
# CELERY_ALWAYS_EAGER = False
# CELERY_ACKS_LATE = True
# CELERY_TASK_PUBLISH_RETRY = True
# CELERY_DISABLE_RATE_LIMITS = False
