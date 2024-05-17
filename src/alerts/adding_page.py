import sys
import os
import django
import logging

from django.db import models as db_models
from django.db import transaction
sys.path.append('./')

if  __name__ == "__main__":
    environment = sys.argv[1]
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'HRMSProject.settings.{environment}')
    django.setup()
    
def calling_func():
    print("Hiiii", sys.argv[1])

if  __name__ == "__main__":
    calling_func()