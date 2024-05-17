import base64
import calendar
import contextlib
import datetime
import importlib
import logging
import os
import random
import string
import time
from typing import Any, Optional, Union
import urllib.parse
import django
import requests

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.db.models import Q, CharField
from django.forms import ValidationError
from django.template import loader
from django.utils import timezone
from django.utils.encoding import force_str
from django.db import models as db_models
from django.db.models import Func
from HRMSApp.utils import Util
import magic
import pytz
from django.http import HttpResponse
# from winmagic import magic

# logger = logging.getLogger(__name__)
logger = logging.getLogger('django')

def get_user(email: str = None, phone: str = None, **kwargs):
    """
    Util method to get User object

    Args:
        email (_type_, str): _description_. Defaults to None.
        phone (_type_, str): _description_. Defaults to None.

    AJAY, 04.01.2023
    """
    UserModel = get_user_model()

    if email is None and phone is None:
        logger.warning("Both Email & Phone are None")
        return None

    if isinstance(email, list):
        email = email[0]

    if isinstance(phone, list):
        phone = phone[0]

    try:
        return UserModel.objects.get(
            Q(email=email) | Q(phone=phone, phone__isnull=False)
        )
    except UserModel.MultipleObjectsReturned:
        users = UserModel.objects.filter(
            Q(email=email) | Q(phone=phone, phone__isnull=False)
        )
        return users.latest()
    except UserModel.DoesNotExist:
        logger.error(f"User not found with << email: {email} or phone: {phone} >>")
        return None


def email_render_to_string(template_name, context=None, strip=False):
    """
    Render given template and context to string.

    If strip = True, replace \n and \r

    AJAY, 04.01.2023
    """

    message = loader.render_to_string(template_name=template_name, context=context)

    if strip:
        message = message.replace("\r", "").replace("\n", "")

    return message


def localize_dt(dt, tz=None):
    """
    Localize a datetime object

    If no tz name is supplied, it will default to whatever the settings
    is set to.

    If a datetime object with a timezone is supplied, the object will be
    converted to use the new timezone

    AJAY, 28.01.2023
    """
    if tz is None:
        tz = settings.TIME_ZONE
    tz_obj = pytz.timezone(tz)

    return dt.astimezone(tz_obj) if dt.tzinfo else tz_obj.localize(dt)


def timezone_now(tz=settings.TIME_ZONE):
    """
    timezone.now() function with localized timezone

    AJAY, 28.01.2023
    """
    now = timezone.now()
    return localize_dt(now, tz)


def strptime(input_string, mode="DATE", fmt=None, combine=None):
    """
    Converts a string to a datetime object, based on the default formats
    provided in the settings.py

    @output (mode="DATE"): datetime.date() object
    @output (mode="TIME"): datetime.time() object
    @output (mode="DATETIME"): datetime.datetime() object

    AJAY, 04.01.2023
    """
    if not input_string:
        raise ValueError("No input string given.")

    valid_modes = [
        "DATE",
        "TIME",
        "DATETIME",
    ]

    if mode not in valid_modes:
        raise ImproperlyConfigured(
            f"The strftime() input mode='{mode}' is not a "
            f"valid input. Please use DATE/TIME/DATETIME."
        )

    if combine and mode == "DATETIME":
        raise NotImplementedError(f"Unable to combine datetime with {combine}")

    output = None
    if not fmt:
        formats = getattr(settings, f"{mode}_INPUT_FORMATS", None)
        for fmt in formats:
            with contextlib.suppress(ValueError):
                output = datetime.datetime.strptime(input_string, fmt)
                break
    else:
        output = datetime.datetime.strptime(input_string, fmt)

    if not output:
        # Arbitrarily fail if there is no return
        raise ValueError(f"No valid date format found for {input_string }")

    if combine:
        if isinstance(combine, str):
            if combine.upper() == "MAX":
                combine = datetime.time.max
            elif combine.upper() == "MIN":
                combine = datetime.time.min
            else:
                raise NotImplementedError(
                    f'combine="{combine}" is not a valid argument for this function.'
                )
        output = datetime.datetime.combine(output, combine)

    if mode == "DATE":
        return output.date()

    return output.time() if mode == "TIME" else output


def strftime(dt_input, mode="DATE", tz=None, fmt=None):
    """
    Converts a datetime.datetime/date/time object to a presentable string.

    @output (mode="DATE"): 01 January 2016
    @output (mode="TIME"): 10:00:00 AM
    @output (mode="DATETIME"): 10:00:00 AM, 01 January 2016

    AJAY, 04.01.2023
    """
    valid_modes = [
        "DATE",
        "TIME",
        "DATETIME",
        "CUSTOM",
    ]
    logger.debug(f"locals = {locals()}")

    output = None
    if mode not in valid_modes:
        raise ImproperlyConfigured(
            f"The strftime() input mode='{mode}' is not a valid input. Please use DATE/TIME/DATETIME."
        )

    if mode == "DATE":
        if not isinstance(dt_input, (datetime.date, datetime.datetime)):
            raise ValueError(
                f"Please use a datetime.datetime or datetime.date input for mode={mode}"
            )

        date_fmt = fmt or settings.DATE_FORMAT
        output = dt_input.strftime(date_fmt)

    elif mode == "TIME":
        if not isinstance(dt_input, (datetime.time, datetime.datetime)):
            raise ValueError(
                f"Please use a datetime.datetime or datetime.time input for mode={mode}"
            )
        time_fmt = fmt or settings.TIME_FORMAT
        output = dt_input.strftime(time_fmt)

    elif mode == "DATETIME":
        if not isinstance(dt_input, datetime.datetime):
            raise ValueError(f"Please use a datetime.datetime input for mode={mode}")
        datetime_fmt = fmt or settings.DATETIME_FORMAT
        output = dt_input.strftime(datetime_fmt)

    elif mode == "CUSTOM":
        if fmt is None:
            raise ImproperlyConfigured(
                "This function requires a format to be included."
            )
        output = dt_input.strftime(fmt)

    return output


def load_class(string_path):
    """
    Loads a module and class from a string path.

    AJAY, 04.01.2023
    """
    class_data = string_path.split(".")
    if class_data[0] == "settings":
        return getattr(settings, class_data[-1], None)

    try:
        return importlib.import_module(string_path)
    except ImportError:
        module_path = ".".join(class_data[:-1])
        class_str = class_data[-1]

        module = importlib.import_module(module_path)
        # Finally, we retrieve the Class
        return getattr(module, class_str)


def get_classname(obj):
    """
    Returns class name of the obj

    AJAY, 28.01.2023
    """
    cls = type(obj)
    module = cls.__module__
    name = cls.__qualname__
    if module is not None and module != "__builtin__":
        name = f"{module}.{name}"
    return name


def generate_random_string(string_length=8):
    """
    Helper function to generate random alpha numeric string

    AJAY, 31.01.2023
    """
    letters_and_digits = string.ascii_letters + string.digits
    return "".join(random.choice(letters_and_digits) for _ in range(string_length))


def get_month_weeks(
    date_input: datetime, need_week_number_only: bool = False, combine: bool = False
) -> Union[Optional[int], Optional[dict]]:
    """
    It returns a dictionary of the month's days and their corresponding week numbers, or just the week
    number of the day passed in

    :param date_input: datetime - the date you want to get the week number for
    :type date_input: datetime
    :param need_week_number_only: bool = False, defaults to False
    :type need_week_number_only: bool (optional)
    :return: A dictionary of the month's days and their corresponding week number.

    AJAY, 30.03.2023
    """

    cal = calendar.monthcalendar(date_input.year, date_input.month)
    month_weeks = {}

    for week_num, week in enumerate(cal):
        for day in week:
            if day != 0:
                month_weeks[day] = week_num + 1
    if combine:
        return {month_weeks[date_input.day]: date_input}
    return month_weeks[date_input.day] if need_week_number_only else month_weeks


def hrs_to_mins(hours=0, minutes=0):
    """
    utility to convert hours to minutes

    AJAY, 27.03.2023
    """
    if not hours and not minutes:
        return 0

    if isinstance(hours, str):
        hours = int(hours)

    if isinstance(minutes, str):
        minutes = int(minutes)

    return (hours * 60) + minutes


def mins_to_hrs(minutes: int = 0):
    """
    utility to convert minutes to hours

    AJAY, 27.03.2023
    """
    hours, _minutes = divmod(minutes, 60)

    return f"{hours}:{_minutes}"


def get_formatted_time(dt_input: datetime.datetime, tz=settings.TIME_ZONE, format: str = "%I:%M %p") -> str:
    """
    This function takes a datetime object and returns a formatted string representing the time in
    12-hour format with AM/PM indicator.

    :param dt_input: The input datetime object that needs to be formatted
    :type dt_input: datetime.datetime
    :param format: The "format" parameter is a string that specifies the format in which the time should
    be displayed. It uses the same format codes as the strftime() method in Python's datetime module.
    The default format is "%I:%M %p", which displays the time in 12-hour format with AM/, defaults to
    %I:%M %p
    :type format: str (optional)
    :return: The function `get_formatted_time` is returning a string that represents the input datetime
    object in the specified format ("%I:%M %p"). The input datetime object is first localized using the
    `localize_dt` function (which is not shown in the code snippet), and then formatted using the
    `strftime` method.

    AJAY, 18.04.2023
    """
    return localize_dt(dt_input, tz=tz).strftime("%I:%M %p")


def b64_to_image(
    image_data: Any = None,
    instance: Any = None,
    file_name: str = None,
    use_ctime_as_prefix: bool = False,
) -> Any:
    if image_data is None:
        return

    format, imgstr = image_data.split(";base64,")
    ext = format.split("/")[-1]

    if not file_name:
        file_name = int(time.time())

    if use_ctime_as_prefix:
        file_name = f"{file_name}_{int(time.time())}"

    return ContentFile(base64.b64decode(imgstr), f"{file_name}.{ext}")


def get_ip_address(request):
    """
    This function retrieves the IP address of a user making a request to a web server.

    :param request: The `request` parameter is an object that represents an HTTP request made to a web
    server. It contains information about the request, such as the HTTP method used (GET, POST, etc.),
    the URL requested, any query parameters, headers, and more. In this case, the `request`
    :return: the IP address of the user making the request. If the request is coming through a proxy
    server, the function will extract the IP address from the `HTTP_X_FORWARDED_FOR` header. Otherwise,
    it will use the `REMOTE_ADDR` header to get the IP address. The final IP address is returned as a
    string.

    AJAY, 24.04.2023
    """
    user_ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
    if user_ip_address:
        ip = user_ip_address.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def validate_file_attachment(file):
    """
    Function to validate file extension based on settings

    AJAY, 04.05.2023
    """
    ext = os.path.splitext(file.name)[1]  # [0] returns path+filename
    valid_extensions = settings.ALLOWED_FILE_EXTENSIONS

    if ext.upper() not in valid_extensions:
        raise ValidationError(
            f'Please use a valid file format ({", ".join(settings.ALLOWED_FILE_EXTENSIONS).lower()})'
        )

    file_mime_type = magic.from_buffer(file.read(1024), mime=True)

    if file_mime_type not in settings.ALLOWED_MIME_TYPES:
        raise ValidationError("The file type is not supported")

    # another additional validation to check for filesize
    file_maximum_size = int(settings.FILE_UPLOAD_MAX_MEMORY_SIZE)
    if file.size > file_maximum_size:
        raise ValidationError(
            f"The maximum file size that can be uploaded is {round(file_maximum_size / 1048576)}MB"
        )


def get_month_pay_cycle_start_end_dates(start_from_day, end_of_day, today):
    if start_from_day < end_of_day:
        start_date = today.replace(day=start_from_day)
        end_date = today.replace(day=end_of_day)
        start_date = start_date.replace(month=today.month-1)
        end_date = end_date.replace(month=today.month-1)
        return start_date, end_date
    if today.day >= start_from_day:
        start_date = today.replace(month=today.month-1, day=start_from_day)
        end_date = today.replace(day=end_of_day)
        return start_date, end_date
    start_date = today.replace(month=today.month-2 if today.day < start_from_day else today.month-1, day=start_from_day)
    end_date = today.replace(month=today.month-1 if today.day < start_from_day else today.month, day=end_of_day)
    return start_date, end_date


def error_response(err, message=None, status=400):
    return {
        "status_code": status,
        "developer_msg": str(err),
        "message": message if message else "Something went wrong, Please try again later",
        "data": {}
    }


def success_response(result, msg, status_code=200):
    return {
        "status_code": status_code,
        "message": msg,
        "result": result
    }


class TimestampToIST(Func):
    """ Converts the db (UTC) timestamp value to IST equivalent timestamp
    """
    function = 'timezone'
    output_field = db_models.DateTimeField()

    def __init__(self, expressions, timezone=settings.TIME_ZONE, **extra):
        self.template = f"%(function)s('{pytz.timezone(timezone)}', %(expressions)s)"
        super().__init__(expressions, **extra)


class TimestampToStr(Func):
    """ Converts the timestamp to string using the given format
    """
    function = 'to_char'
    template = "%(function)s(%(expressions)s, 'HH12:MI AM')" 

class TimestampToStrDateTime(Func):
    """ Converts the timestamp to string using the given format
    """
    function = 'to_char'
    template = "%(function)s(%(expressions)s, 'DD-MM-YYYY HH12:MI AM')" 

class SplitPart(Func):
    function = 'SPLIT_PART'
    output_field = CharField()
    
    def __init__(self, expression, delimiter, position, **extra):
        super().__init__(expression, delimiter, position, **extra)

def excel_converter(data,file_name):
    response = HttpResponse(content_type="text/ms-excel")
    response[
        "Content-Disposition"
    ] = f'attachment; filename="{file_name}"'
    data.to_excel(response, index=False)
    return response

def search_filter_decode(search_filter=""):
    if search_filter is None:
        return ""
    return urllib.parse.unquote(search_filter).strip()


def sending_mails_to_employee(instance):
    emp_name = instance.user.username
    cmp_name = instance.company.company_name
    emp_email = instance.official_email
    emp_personal_email = instance.personal_email
    
    body = f'''
    Dear {emp_name},

    I hope you doing well. As your last day with {cmp_name} approaches, we would like to remind you of the importance of completing the exit interview and other associated formalities. 
    This process is a valuable opportunity for us to gather your feedback and insights, which will help us continually improve as an organization.

    Formalities and Return of Company Property:
    Additionally, we kindly request that you complete the following tasks before your last day:

    Return all company property, including but not limited to [list of items].
    Settle any outstanding financial matters, such as expense reimbursements or outstanding dues.
    Provide any necessary documentation or handover information to ensure a smooth transition for your colleagues.
    If you have any questions or require assistance with any of the above, please do not hesitate to reach out to the HR department. 
    We are here to help make this process as seamless as possible for you.

    We genuinely appreciate your contributions during your time at {cmp_name}, and we wish you all the best in your future endeavors. 
    Thank you for being a part of our team.

    Thanks & Regards,
    {cmp_name},
'''
    try:
        data={
            'subject':'Exit Interview and Formalities',
            'body':body,
            'to_email':[emp_email,emp_personal_email]
        }
        Util.send_email(data,multiple=True)
    except Exception as e:
        pass
    return None  

def get_terminations_date(data,final_day):
    wd = data
    sorted_data = dict(sorted(wd.items(), key=lambda item: [i.lower() for i in list(calendar.day_name)].index(item[0].lower())))
    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    day_name = final_day.strftime("%A").lower()
    current_day_index = day_names.index(day_name)
    test = True
    l = 0
    while test:
        if list(sorted_data.values())[current_day_index] == 0:
            current_day_index -= 1
            l+=1
        else:
            test=False
    
    desired_date= final_day - datetime.timedelta(days=l)
    return desired_date

def get_paycycle_dates(current_date,psc_from_date,psc_to_date):
    current_year = current_date.year
    current_month = current_date.month
    current_day = current_date.day
    next_month = current_month + 1
    up_next_month = current_month + 2
    year = current_year
    year2 = current_year
    if up_next_month > 12:
       up_next_month = up_next_month - 12 
       year = current_year+1
    if next_month > 12:
        next_month = next_month - 12 
        year2 = current_year+1
    
    if current_month == 1:
        previous_month = 12
        previous_year = current_year - 1
        if psc_from_date == 1:
            previous_month = current_month
            previous_year = current_year
            
    else:
        previous_month = current_month - 1
        previous_year = current_year
        if psc_from_date == 1:
            previous_month = current_month
            previous_year = current_year
    
    if current_day > psc_to_date:
        num_days = calendar.monthrange(year2, next_month)[1]
        if num_days < psc_to_date:
            psc_to_date = num_days
        pay_cycle_from_date = datetime.datetime(current_year, current_month, psc_from_date)
        pay_cycle_to_date = datetime.datetime(year2, next_month, psc_to_date) 
        current_payout_date = datetime.datetime(year, up_next_month, 1) 
    else:  
        num_days = calendar.monthrange(current_year, current_month)[1]
        if num_days < psc_to_date:
            psc_to_date = num_days
        pay_cycle_from_date = datetime.datetime(previous_year, previous_month, psc_from_date)
        pay_cycle_to_date = datetime.datetime(current_year, current_month, psc_to_date)
        current_payout_date = datetime.datetime(year2, next_month, 1)
    return pay_cycle_from_date,pay_cycle_to_date,current_payout_date

def get_updated_payload_data(payload_data,name_of_model):
    if name_of_model=="AuditorDetails":
        auditor_types = {1: "Internal", 2: "Statutory"}
        for data in payload_data:
            # Update auditor type based on the mapping 
            auditor_type_id = data.get("auditor_type_id")
            if auditor_type_id in auditor_types:
                data["auditor_type_id"] = auditor_types[auditor_type_id]
    if name_of_model=="BankDetails":
        bank_account_types = {1: "Current Account",2: "Savings Account",3: "Salary Account",4: "Fixed Deposit Account",5: "Recurring Deposit Account",6: "Non-Resident Indian Account",7: "Non-Resident Ordinary Account",8: "Non-Resident External Account",9: "Foreign Currency Non-Resident Account"}
        for data in payload_data:
            account_type_id = data.get("account_type_id")
            if account_type_id in bank_account_types:
                data["account_type_id"] = bank_account_types[account_type_id]
    if name_of_model=="StatutoryDetails":
        entity_types = {1: "Private Limited Company",2: "Public Limited Company",3: "Limited Liability Partnership",4: "Partnership",5: "Sole Proprietorship",6: "Nonprofit Organisation",7: "Society",8: "Trust",9: "Others"}
        for data in payload_data:
            entity_type_id = data.get("entity_type_id")
            if entity_type_id in entity_types:
                data["entity_type_id"] = entity_types[entity_type_id]
    if name_of_model=="EmployeeCertifications":
        course_types = {1: "Graduation",2: "Post Graduation",3: "Doctorate",4: "Diploma",5: "Pre University",6: "Certification",7: "Others"}
        for data in payload_data:
            course_type_id = data.get("course_type_id")
            if course_type_id in course_types:
                data["course_type_id"] = course_types[course_type_id]
    if name_of_model=="EmployeeEducationDetails":
        course_types = {1: "Full Time", 2: "Part Time", 3: "Correspondence", 4: "Certificate"}
        qualification_types = {1: "Graduation",2: "Post Graduation",3: "Doctorate",4: "Diploma",5: "Pre University",6: "Other Education",7: "Certification"}
        for data in payload_data:
            course_type_id = data.get("course_type_id")
            qualification_id = data.get("qualification_id")
            if course_type_id in course_types:
                data["course_type_id"] = course_types[course_type_id]
            if qualification_id in qualification_types:
                data["qualification_id"] = qualification_types[qualification_id]
    if name_of_model=="EmployeeDocuments":
        document_types = {1: "PAN Card",2: "Aadhaar Card",3: "Passport",4: "Driving Licence",5: "Voter ID",6: "Electricity Bill",7: "Phone Bill",8: "Bank Passbook",9: "Rental Agreement",10: "others"}
        for data in payload_data:
            document_type_id = data.get("document_type_id")
            if document_type_id in document_types:
                data["document_type_id"] = document_types[document_type_id]
    if name_of_model=="EmployeeWorkDetails":
        employee_types = {1: "Full Time", 2: "Part Time", 3: "Intern", 4: "On Contract", 5: "Others"}
        for data in payload_data:
            employee_type_id = data.get("employee_type_id")
            if employee_type_id in employee_types:
                data["employee_type_id"] = employee_types[employee_type_id]
    if name_of_model =="EmployeeReportingManager":
        manager_types = {1: "Primary", 2: "Secondary"}
        for data in payload_data:
            manager_type_id = data.get("manager_type_id")
            if manager_type_id in manager_types:
                data["manager_type_id"] = manager_types[manager_type_id]
    if name_of_model == "EmployeeFamilyDetails":
        relationship_types = {1: "Father", 2: "Mother", 3: "Husband", 4: "Wife", 5: "Son",6: "Daughter",7: "Brother",8: "Sister",9: "Friend"}
        for data in payload_data:
            relationship_id = data.get("relationship_id")
            if relationship_id in relationship_types:
                data["relationship_id"] = relationship_types[relationship_id]
    if name_of_model =="EmployeeSalaryDetails":
        bank_account_types = {1: "Current Account",2: "Savings Account",3: "Salary Account",4: "Fixed Deposit Account",5: "Recurring Deposit Account",6: "Non-Resident Indian Account",7: "Non-Resident Ordinary Account",8: "Non-Resident External Account",9: "Foreign Currency Non-Resident Account"}
        for data in payload_data:
            account_type_id = data.get("account_type_id")
            if account_type_id in bank_account_types:
                data["account_type_id"] = bank_account_types[account_type_id]
    if name_of_model == "LeavesHistory":
        status_types = {10: "Approved", 20: "Pending", 30: "Cancelled", 40: "Rejected",50: "Revoked"}
        for data in payload_data:
            status = data.get("status")
            if status in status_types:
                data["status"] = status_types[status]
    if name_of_model =="EmployeeEmergencyContact":
        relationship_types = {1: "Father", 2: "Mother", 3: "Husband", 4: "Wife", 5: "Son",6: "Daughter",7: "Brother",8: "Sister",9: "Friend"}
        for data in payload_data:
            relationship_id = data.get("relationship_id")
            if relationship_id in relationship_types:
                data["relationship_id"] = relationship_types[relationship_id]

    if name_of_model == "EmployeeCheckInOutDetails":
        for data in payload_data:
            data.pop('status', '')
            data.pop('work_duration', '')
            data.pop('break_duration', '')
            data.pop('breaks', '')
            data.pop('employee_selfie', '') 
            data.pop('employee_selfie_binary', '')
            data.pop('location', '')
            data.pop('distance', '')
            data.pop('action_status', '')
            data.pop('action', '')
            data.pop('action_reason', '')
            data.pop('approval_reason', '')
            data.pop('reject_reason', '')
            data.pop('action_reason', '')
            data.pop('extra_data')
            data.pop('overtime_hours', '')
            data.pop('compoff_added', '') 
            time_out = data.pop('time_out','')
            latest_time_in = data.pop('latest_time_in','')
            is_logged_out = data.pop('is_logged_out','')
            if is_logged_out:
                try:
                    time_out = datetime.datetime.strptime(str(time_out), "%Y-%m-%d %H:%M:%S.%f%z").strftime("%Y-%m-%d %I:%M:%S %p") 
                    time_in = datetime.datetime.strptime(str(data.get('time_in', '') ), "%Y-%m-%d %H:%M:%S.%f%z").strftime("%Y-%m-%d %I:%M:%S %p") 
                    latest_time_in = datetime.datetime.strptime(str(latest_time_in), "%Y-%m-%d %H:%M:%S.%f%z").strftime("%Y-%m-%d %I:%M:%S %p")
                except Exception as e:
                    pass
                data['time_in'] = time_in
                data['latest_time_in'] = latest_time_in
                data['time_out'] = time_out
                data.pop('date_of_checked_in', '') 
            else:
                try:
                    latest_time_in = datetime.datetime.strptime(str(latest_time_in), "%Y-%m-%d %H:%M:%S.%f%z").strftime("%Y-%m-%d %I:%M:%S %p")
                    time_in = datetime.datetime.strptime(str(data.get('time_in', '') ), "%Y-%m-%d %H:%M:%S.%f%z").strftime("%Y-%m-%d %I:%M:%S %p") 
                except Exception as e:
                    pass
                data['latest_time_in'] = latest_time_in
                data['time_in'] = time_in
                data.pop('date_of_checked_in', '') 
                data.pop('time_out', '') 
                
                 
    return payload_data

def get_domain(db_name, env, module_name):
    """ 
    if env == 'qa':
        domain = 'whytelglobal'
        if db_name == 'pss_whytelglobal_db':
            url = f'https://pss.{domain}.com/{module_name}'
        elif db_name == 'vitelglobal_whytelglobal_db':
            url = f'https://vitelglobal.{domain}.com/{module_name}'
        else:
            url = f'https://{domain}.com/{module_name}'
    elif env == 'prod':
        domain = 'indianhr'
        if db_name == 'pss_indianhr_db':
            url = f'https://pss.{domain}.in/{module_name}'
        elif db_name == 'vitelglobal_indianhr_db':
            url = f'https://vitelglobal.{domain}.in/{module_name}'
        elif db_name == 'varundigital_indianhr_db':
            url = f'https://varundigital.{domain}.in/{module_name}' 
        elif db_name == 'test_indianhr_db':
            url = f'https://test.{domain}.in/{module_name}'
    elif env == 'local':
        url = f'https://localhost/{module_name}'
    """
    
    url = ''
    try:
        database_name = (django.db.connections.databases['default']['NAME']).split('_')  #subdomain_domain_db
        sub_domain = database_name[0]
        domain = database_name[1]
        tg = 'com'
        if domain == 'indianhr':
            tg = 'in'
        if env == 'qa':
            url = f'https://{sub_domain}.{domain}.{tg}/{module_name}'
        elif env == 'prod':
            url = f'https://{sub_domain}.{domain}.{tg}/{module_name}'
        elif env == 'local':
            url = f'https://localhost/{module_name}'
    except Exception as e:
        pass
    return url



def get_ats_permission():
    key = False
    current_env = os.environ.get('DJANGO_SETTINGS_MODULE')
    database_name = (django.db.connections.databases['default']['NAME'])
    try:
        pss_sub_domains = ['pss','vgts','varundigital','vitelglobal']
        if any(env in current_env for env in ['dev', 'local']):
            key=False
        elif 'qa' in current_env:
            key=True
        else:
            database = database_name.split('_')  #subdomain_domain_db
            sub_domain = database[0]
            if any(sd == sub_domain for sd in pss_sub_domains):
                key=True
    except Exception as e:
        key = False
        logger.warning(f"Error in Getting the ATS Permissions in env:{current_env}, db:{database_name} at {timezone_now()}")
    return key

def post_department_ats(payload):
    try:
        url = "https://hrms.indianhr.in/ATS3/department.php"
        files=[]
        headers = {}
        ats_permission = get_ats_permission()
        if ats_permission:
            response = requests.request("POST", url, headers=headers, data=payload, files=files)
    except Exception as e:
        logger.warning(f"Found error in Adding depratments into ATS {timezone_now()}")
        
def update_department_ats(payload):  
    try:  
        url = "https://hrms.indianhr.in/ATS3/updatedepartment.php"
        files=[]
        headers = {}
        ats_permission = get_ats_permission()
        if ats_permission:
            response = requests.request("POST", url, headers=headers, data=payload, files=files)
    except Exception as e:
        logger.warning(f"Found error in Updating depratments into ATS {timezone_now()}")

def add_employee_ats(payload):
    try: 
        url = "https://hrms.indianhr.in/ATS3/employee.php"
        files=[]
        headers = {}
        ats_permission = get_ats_permission()
        if ats_permission:
            response = requests.request("POST", url, headers=headers, data=payload, files=files)
    except Exception as e:
        logger.warning(f"Found error in Add Employee into ATS {timezone_now()}")
        
def update_employee_ats(payload):
    try: 
        url = "https://hrms.indianhr.in/ATS3/updateemployee.php"
        files=[]
        headers = {}
        ats_permission = get_ats_permission()
        if ats_permission:
            response = requests.request("POST", url, headers=headers, data=payload, files=files)
    except Exception as e:
        print("came_here:",e)
        logger.warning(f"Found error in Update Employee into ATS {timezone_now()}")