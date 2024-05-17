from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-$p=9m6)dmeczf)axogo(qtl5jve8!0lbxr9l!*jdu&1ho)44ks"
print("Development")

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
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "HOST": "localhost",
        "NAME": "indianhrms_db",
        "USER": "root",
        "PASSWORD": "Vitel@321",
        "PORT": 5432,
    }
}


DB_PREFIX = "tbl_"

###############################################################################
# REST FRAMEWORK SETTINGS
###############################################################################


ADMIN_DEFAULT_PASSWORD = "pss@2023!"
ADMIN_URL_PATH = "pss-hrms-admin"
ADMIN_SHOW = False


# Allow CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://38.143.106.215:3000",
    "http://38.143.106.215",
]
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://38.143.106.215:3000",
    "http://38.143.106.215",
]

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = False
CORS_ORIGIN_WHITELIST = []
CORS_URLS_REGEX = r"^/api/.*$"


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "hrms_cache",
        "KEY_FUNCTION": "HRMSProject.settings.base.make_key",
        "TIMEOUT": DEFAULT_CACHE_TIMEOUT,
    }
}
