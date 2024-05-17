import os
import logging

logger = logging.getLogger('django')

APP_ENV = os.environ.get("APP_ENV", "local")

if APP_ENV == "dev":
    from .dev import *
elif APP_ENV == "qa":
    from .qa import *
elif APP_ENV == "prod":
    from .prod import *
else:
    from .local import *
os.environ['DJANGO_SETTINGS_MODULE'] = f'HRMSProject.settings.{APP_ENV}'

logger.critical(f'Initial Env {APP_ENV}')
