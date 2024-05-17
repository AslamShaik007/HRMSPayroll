import traceback
import pymysql
import pandas as pd
import numpy as np
from os.path import expanduser
import logging
import datetime
from dateutil import parser


from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework import permissions

from django.db import models as db_models
from django.conf import settings

from core.utils import success_response, error_response, timezone_now, excel_converter, search_filter_decode, mins_to_hrs, localize_dt
from core.custom_paginations import CustomPagePagination

from attendance.models import EmployeeCheckInOutDetails
from directory.models import EmployeeWorkDetails

logger = logging.getLogger(__name__)



home = expanduser('~')
# mypkey = paramiko.RSAKey.from_private_key_file(home + pkeyfilepath)
# if you want to use ssh password use - ssh_password='your ssh password', bellow
sql_hostname = '127.0.0.1'
sql_username = 'root'
sql_password = 'Fp&cX9n$g86e&W4'
sql_main_database = 'qahrms'
sql_port = 3306
ssh_host = '38.143.106.38'
ssh_user = 'root'
ssh_port = 22
sql_ip = '1.1.1.1.1'

class BiometricAttandanceLogsAPIView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagePagination
    
    def convert_to_string(timestamp):
        if pd.notna(timestamp):  # Check if it's not NaT
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return ""  # Or any other string for NaT
    
    def system_in_out(self, obj):
        obj['in_outs'] = []
        for chhh in obj['checkin_checkout']:
            if len(obj['in_outs']) == 0:
                obj['in_outs'].append({'break_duration': "-", "work_duration": "-"})
                if chhh['direction'] == "in":
                    obj['in_outs'][0]['in'] = chhh["time"]
                    obj['in_outs'][0]['out'] = '-'
                if chhh['direction'] == "out":
                    obj['in_outs'][0]['out'] =  chhh["time"]
                    obj['in_outs'][0]['in'] = '-'
                    obj['in_outs'][0]['work_duration'] = '-'
            else:
                if chhh['direction'] == "out":
                    obj['in_outs'][-1]['out'] =  chhh["time"]
                    obj['in_outs'][-1]['work_duration'] = mins_to_hrs((datetime.datetime.strptime(chhh["time"], "%Y-%m-%d %H:%M") - datetime.datetime.strptime(obj['in_outs'][-1]['in'], "%Y-%m-%d %H:%M")).seconds // 60) if obj['in_outs'][-1]['in'] != '-' else '-'
                if chhh['direction'] == "in":
                    obj['in_outs'].append(
                        {
                            'break_duration': mins_to_hrs((datetime.datetime.strptime(chhh["time"], "%Y-%m-%d %H:%M") - datetime.datetime.strptime(obj['in_outs'][-1]['out'], "%Y-%m-%d %H:%M")).seconds // 60) if obj['in_outs'][-1]['out'] != '-' else '-',
                            "in": chhh["time"],
                            'out': "-", "work_duration": "-"
                        }
                    )
        return obj['in_outs']
    
    def calculate_work_duration(self, in_outs):
        total_time = datetime.timedelta()

        for time_data in in_outs:
            work_duration = time_data.get('work_duration')
            if work_duration and work_duration != '-':
                hours, minutes = map(int, work_duration.split(':'))
                time_delta = datetime.timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def calculate_break_duration(self,in_outs):
        total_time = datetime.timedelta()

        for time_data in in_outs:
            work_duration = time_data.get('break_duration')
            if work_duration and work_duration != '-':
                hours, minutes = map(int, work_duration.split(':'))
                time_delta = datetime.timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def convert_date_time(self,obj):
        date_time_obj = '-'
        try:
            date_time_obj = datetime.datetime.strptime(obj, '%Y-%m-%d %H:%M').strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj
    
    def get(self, request, *args, **kwargs):
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        end_date = (date + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        # try:
        #     current_db = settings.DATABASES['default']['NAME'].split('_')[0]
        # except:
        #     current_db = None
        # if current_db == 'pss':
        #     search_key = 'PSS'
        # elif current_db == 'vitelglobal':
        #     search_key = 'VG'
        # elif current_db == 'varundigital':
        #     search_key = 'PSS'
        # else:
        #     search_key = ''
        company_emp_ids = tuple(EmployeeWorkDetails.objects.filter(employee_status='Active',employee_number__isnull=False).values_list('employee_number', flat=True))
        try:
            if "start_date" not in params:
                return Response(
                            error_response("Start Date Required","Start Date Required"),
                            status=status.HTTP_400_BAD_REQUEST
                        )    
            if "employee_id" in params:
                emp_code = search_filter_decode(params.get("employee_id"))
                q_filters = (
                     db_models.Q(employee__user__username__icontains=emp_code) |
                     db_models.Q(employee__official_email__icontains=emp_code) |
                     db_models.Q(employee_number__icontains=emp_code)
                 )
                empl_ids = EmployeeWorkDetails.objects.filter(q_filters,employee_status='Active').values_list('employee_number',flat=True)
                if not empl_ids.exists():
                    return Response(
                        error_response("No Data Found For The Selected Dates", "No Data Found For The Selected Dates", 404),
                        status=status.HTTP_404_NOT_FOUND
                    ) 
                emp_ids = tuple(empl_ids)
                query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{start_date} 08:00:00' AND '{end_date} 07:59:59' AND empcode in {emp_ids};"
                if len(empl_ids) == 1:    
                    emp_code = empl_ids.first()
                    query = f"SELECT * FROM vg_attendance_logs WHERE empcode = '{emp_code}' AND logdatetime BETWEEN '{start_date} 08:00:00' AND '{end_date} 07:59:59';"
                elif len(empl_ids) > 1:
                    query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{start_date} 08:00:00' AND '{end_date} 07:59:59' AND empcode in {emp_ids};"
            else:
                query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{start_date} 08:00:00' AND '{end_date} 07:59:59' AND empcode in {company_emp_ids};"
            paginator = self.pagination_class()          
            if "is_export" in params:
                if not (start_date and end_date):
                    return Response(
                            error_response("Start Date and End Date Required","Start Date and End Date Required"),
                            status=status.HTTP_400_BAD_REQUEST
                        )
                if start_date > end_date:
                    return Response(
                            error_response("End Date should be greater than Start date", "End Date should be greater than Start date", 404),
                            status=status.HTTP_404_NOT_FOUND
                        )
                # if (datetime.datetime.strptime(end_date, "%Y-%m-%d") - datetime.datetime.strptime(start_date, "%Y-%m-%d")).days > 31:
                #     return Response(
                #             error_response("Start Date and End Date cant be more than a Month", 404),
                #             status=status.HTTP_404_NOT_FOUND
                #         )
                # query = f"SELECT * FROM vg_attendance_logs WHERE DATE(logdatetime) >= '{start_date}' AND DATE(logdatetime) <= '{end_date}' ORDER BY DATE(logdatetime) DESC;"
                conn = pymysql.connect(
                    host=ssh_host, user=sql_username,
                    passwd=sql_password, db=sql_main_database,
                    port=sql_port
                )
                data = pd.read_sql_query(query, conn) 
                df_data = pd.DataFrame(data,columns=['attendance_log', 'empcode', 'logdatetime', 'logdate', 'logtime',
                                                        'direction', 'WorkCode', 'port_out'])
                if df_data.empty:
                    return Response(
                        error_response("No Data Found For The Selected Dates", "No Data Found For The Selected Dates", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )
                df_data["logdatetime"]=pd.to_datetime(df_data['logdatetime']).dt.strftime('%Y-%m-%d %H:%M')
                df_sorted = df_data.sort_values(by='logdatetime')
                df_data = df_sorted.drop_duplicates(subset=['logdatetime', 'empcode'])
                df_data['checkin_checkout'] = df_data.apply(lambda obj : {"time": obj["logdatetime"], "direction": obj["direction"]}, axis=1)
                df_data['checkin_checkouts'] = df_data.apply(lambda obj : f'{obj["logdatetime"]} ----- {obj["direction"]}', axis=1)
                # df_data['in_direction'] = df_data['logdatetime'] + ' ----- ' + df_data['direction'].where(df_data['direction'] != 'out', '')
                # df_data['out_direction'] = df_data['logdatetime'] + ' ----- ' + df_data['direction'].where(df_data['direction'] != 'in', '')
                hrms_clockin_data = EmployeeCheckInOutDetails.objects.filter(date_of_checked_in__range = [start_date,end_date]).annotate(
                    employee_name =  db_models.F("employee__user__username"),
                    designation = db_models.F('employee__work_details__designation__name') 
                ).values("employee__work_details__employee_number","employee_name","date_of_checked_in",
                        "time_in","latest_time_in","time_out","work_duration","break_duration","breaks","extra_data",'designation')
                df_checkin_data = pd.DataFrame(hrms_clockin_data, 
                                            columns=["employee__work_details__employee_number","employee_name","date_of_checked_in","time_in",
                                                        "latest_time_in","time_out","work_duration","break_duration","breaks","extra_data","designation"])
                df_checkin_data.rename(columns={'employee__work_details__employee_number':'empcode'}, inplace=True)
                # df_checkin_data.fillna('',inplace=True)
                df_checkin_data.time_in = df_checkin_data.time_in.apply(lambda obj:obj.strftime('%Y-%m-%d %H:%M:%S') if obj is not None else obj)
                df_checkin_data.latest_time_in = df_checkin_data.latest_time_in.apply(lambda obj:obj.strftime('%Y-%m-%d %H:%M:%S') if obj is not None else obj)
                df_checkin_data.time_out = df_checkin_data.time_out.apply(lambda obj:obj.strftime('%Y-%m-%d %H:%M:%S') if obj is not None else obj)
                df_data['in_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="out" else None, axis=1)
                df_data['out_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="in" else None, axis=1)
                df_data['date'] = df_data.apply(lambda obj:
                            (datetime.datetime.strptime(obj['logdatetime'], '%Y-%m-%d %H:%M').date()).strftime('%d/%m/%Y') if obj['logdatetime'] and obj['logdatetime'] is not None else obj['logdatetime'],axis=1)
                # df_data = df_data.groupby(['date', 'empcode']).agg({
                #                     'checkin_checkout': list,
                #                     'checkin_checkouts': list
                #                 }).reset_index()
                
                df_data = df_data.groupby(['date', 'empcode']).agg({
                                                'logdatetime':list,
                                                'logdate':list,
                                                'checkin_checkout': list,
                                                'checkin_checkouts': list,
                                                'in_direction':list,
                                                'out_direction':list
                                                }).reset_index()
                # df_checkin_data.fillna(0,inplace=True)
                # df_data = df_data.groupby('empcode').agg({
                #                                     # 'logdatetime':list,
                #                                     # 'direction':list,
                #                                     'checkin_checkouts': list,
                #                                     'checkin_checkout': list,
                #                                     }).reset_index()
                df_data.rename(columns={'date':'date_of_checked_in'},inplace=True)
                # final_df = pd.merge(df_data, df_checkin_data, how="left", on='empcode') 
                final_df = pd.merge(df_data, df_checkin_data, on=['empcode', 'date_of_checked_in'], how='left')
                if not final_df.empty:
                    final_df['in_outs'] = final_df.apply(lambda obj: self.system_in_out(dict(obj)), axis=1)
                    final_df['biometric_work_duration'] = final_df.apply(lambda obj: self.calculate_work_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                    final_df['biometric_break_duration'] = final_df.apply(lambda obj: self.calculate_break_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                    
                    final_df['employee_name'] = final_df.empcode.apply(lambda x: EmployeeWorkDetails.objects.filter(
                                                                                    employee_number=x
                                                                                ).first().employee.user.username if EmployeeWorkDetails.objects.filter(employee_number=x) else x)
                    
                    final_df['bio_check_in_time'] = final_df.apply(lambda obj: self.convert_date_time(obj['in_direction'][0]) if obj['in_direction']  else '-', axis=1)
                    final_df['bio_check_out_time'] = final_df.apply(lambda obj: self.convert_date_time(obj['out_direction'][-1]) if obj['out_direction']  else '-', axis=1)
                    final_df['hrms_check_in_time'] = final_df.apply(lambda obj: self.convert_date_time(obj['time_in']) if obj['time_in'] else '-', axis=1)
                    final_df['hrms_check_out_time'] = final_df.apply(lambda obj: self.convert_date_time(obj['time_out']) if obj['time_out'] else '-', axis=1)
                    final_df['ip_address'] = final_df.apply(lambda obj: obj['extra_data'].get('punch_history')[-1].get('ip_address') if not isinstance(obj['extra_data'],float) and obj['extra_data'] else '-', axis=1)
                    final_df.rename(
                    columns={'date_of_checked_in':'Date Of Check In', 'empcode':'Emp Id', 'designation':'Designation', 'bio_check_in_time':'Biometric Check In Time',
                             'bio_check_out_time':'Biometric Check Out Time', 'hrms_check_in_time':'Web Check In Time', 'hrms_check_out_time':'Web Check Out Time',
                             'ip_address':'IP Address', 'employee_name':'Emp Name', 'biometric_work_duration':'Biometric Work Duration', 'biometric_break_duration':'Biometric Break Duration',
                             'work_duration':'HRMS Work Duration', 'break_duration':'HRMS Break Duration', 
                             
                             }
                    , inplace=True)
                    # final_df = final_df.drop(columns=['checkin_checkout','in_outs'])
                    final_df = final_df[['Date Of Check In', 'Emp Id', 'Emp Name', 'Designation', 'Biometric Check In Time', 'Biometric Check Out Time', 'Web Check In Time', 'Web Check Out Time',
                                         'Biometric Work Duration', 'Biometric Break Duration', 'HRMS Work Duration', 'HRMS Break Duration', 'IP Address']]

                conn.close()
                # final_df = final_df.drop_duplicates(['empcode'])
                file_name = f"export_biometric_records_{timezone_now().date()}.xlsx"
                return excel_converter(final_df,file_name)
            conn = pymysql.connect(host=ssh_host, user=sql_username,
                passwd=sql_password, db=sql_main_database,
                port=sql_port)
            data = pd.read_sql_query(query, conn) 
            df_data = pd.DataFrame(data,columns=['attendance_log', 'empcode', 'logdatetime', 'logdate', 'logtime',
                                                    'direction', 'WorkCode', 'port_out'])
            df_data["logdatetime"]=pd.to_datetime(df_data['logdatetime']).dt.strftime('%Y-%m-%d %H:%M')
            df_sorted = df_data.sort_values(by='logdatetime')
            df_data = df_sorted.drop_duplicates(subset=['logdatetime', 'empcode'])
            df_data['checkin_checkout'] = df_data.apply(lambda obj : {"time": obj["logdatetime"], "direction": obj["direction"]}, axis=1)
            df_data['in_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="out" else None, axis=1)
            df_data['out_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="in" else None, axis=1)
            # df_data['in_direction'] = df_data['logdatetime'] + ' ----- ' + df_data['direction'].where(df_data['direction'] != 'out', '')
            # df_data['out_direction'] = df_data['logdatetime'] + ' ----- ' + df_data['direction'].where(df_data['direction'] != 'in', '')
            hrms_clockin_data = EmployeeCheckInOutDetails.objects.filter(date_of_checked_in__range = [start_date,end_date]).annotate(
                employee_name =  db_models.F("employee__user__username"),
                selected_tz=db_models.F('employee__assignedattendancerules__attendance_rule__selected_time_zone'),
                designation = db_models.F('employee__work_details__designation__name') 
            ).values("employee__work_details__employee_number","employee_name","date_of_checked_in",
                    "time_in","latest_time_in","time_out","work_duration","break_duration","breaks","extra_data", "selected_tz", "designation")
            # if not hrms_clockin_data.exists():
            #     data_dict = []
            #     return Response(
            #         success_response(
            #                 data_dict, "Successfully fetched Employee Biometric data", 200
            #             ),
            #             status=status.HTTP_200_OK
            #         )
            df_checkin_data = pd.DataFrame(hrms_clockin_data, 
                                        columns=["employee__work_details__employee_number","employee_name","date_of_checked_in","time_in",
                                                    "latest_time_in","time_out","work_duration","break_duration","breaks","extra_data",  "selected_tz", "designation"])
            df_checkin_data.rename(columns={'employee__work_details__employee_number':'empcode'}, inplace=True)
            if not df_checkin_data.empty:
                df_checkin_data.selected_tz =  df_checkin_data.selected_tz.fillna(settings.TIME_ZONE)
                df_checkin_data = df_checkin_data.fillna(np.nan).replace([np.nan], [None])
                df_checkin_data['time_in'] = df_checkin_data.apply(lambda x: localize_dt(x['time_in'], x['selected_tz']) if x['time_in'] else '-', axis=1)
                df_checkin_data['time_out'] = df_checkin_data.apply(lambda x: localize_dt(x['time_out'], x['selected_tz']) if x['time_out'] else '-', axis=1)
            df_data = df_data.groupby(['empcode']).agg({#'attendance_log':list,
                                                'logdatetime':list,
                                                'logdate':list,
                                            #   'logtime':list,
                                                'direction':list,
                                            'checkin_checkout': list,
                                                'in_direction':list,
                                                'out_direction':list,
                                                }).reset_index()
            final_df = pd.merge(df_data, df_checkin_data, how="left", on='empcode') 
            final_df['employee_name'] = final_df.empcode.apply(lambda x: EmployeeWorkDetails.objects.filter(employee_number=x).first().employee.user.username if EmployeeWorkDetails.objects.filter(employee_number=x) else x)
            if not final_df.empty:
                final_df['in_outs'] = final_df.apply(lambda obj: self.system_in_out(dict(obj)), axis=1)
                final_df['total_work_duration'] = final_df.apply(lambda obj: self.calculate_work_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                final_df['total_break_duration'] = final_df.apply(lambda obj: self.calculate_break_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
            final_df = final_df.fillna("-")
            final_df = final_df.fillna(np.nan).replace([np.nan], [None])
            final_df = final_df.drop_duplicates(['empcode'])
            data_dict = final_df.to_dict('records')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(data_dict, request)
            op_output = paginator.get_paginated_response(page)
            # page = paginator.paginate_queryset(data_dict, request)
            conn.close()
            return Response(
            success_response(
                    op_output, "Successfully fetched Employee Biometric data", 200
                ),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            # Log the exception for debugging
            logger.error(f"An error occurred: {e}")
            return Response(
                    error_response("An error occurred.", f'{str(e)} - {traceback.format_exc()}'),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
class BiometricAttandanceLogsExportAPIView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CustomPagePagination
    
    def convert_to_string(timestamp):
        if pd.notna(timestamp):  # Check if it's not NaT
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return ""  # Or any other string for NaT
    
    def system_in_out(self, obj):
        obj['in_outs'] = []
        for chhh in obj['checkin_checkout']:
            if len(obj['in_outs']) == 0:
                obj['in_outs'].append({'break_duration': "-", "work_duration": "-"})
                if chhh['direction'] == "in":
                    obj['in_outs'][0]['in'] = chhh["time"]
                    obj['in_outs'][0]['out'] = '-'
                if chhh['direction'] == "out":
                    obj['in_outs'][0]['out'] =  chhh["time"]
                    obj['in_outs'][0]['in'] = '-'
                    obj['in_outs'][0]['work_duration'] = '-'
            else:
                if chhh['direction'] == "out":
                    obj['in_outs'][-1]['out'] =  chhh["time"]
                    obj['in_outs'][-1]['work_duration'] = mins_to_hrs((datetime.datetime.strptime(chhh["time"], "%Y-%m-%d %H:%M") - datetime.datetime.strptime(obj['in_outs'][-1]['in'], "%Y-%m-%d %H:%M")).seconds // 60) if obj['in_outs'][-1]['in'] != '-' else '-'
                if chhh['direction'] == "in":
                    obj['in_outs'].append(
                        {
                            'break_duration': mins_to_hrs((datetime.datetime.strptime(chhh["time"], "%Y-%m-%d %H:%M") - datetime.datetime.strptime(obj['in_outs'][-1]['out'], "%Y-%m-%d %H:%M")).seconds // 60) if obj['in_outs'][-1]['out'] != '-' else '-',
                            "in": chhh["time"],
                            'out': "-", "work_duration": "-"
                        }
                    )
        return obj['in_outs']
    
    def calculate_work_duration(self, in_outs):
        total_time = datetime.timedelta()

        for time_data in in_outs:
            work_duration = time_data.get('work_duration')
            if work_duration and work_duration != '-':
                hours, minutes = map(int, work_duration.split(':'))
                time_delta = datetime.timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def calculate_break_duration(self,in_outs):
        total_time = datetime.timedelta()

        for time_data in in_outs:
            work_duration = time_data.get('break_duration')
            if work_duration and work_duration != '-':
                hours, minutes = map(int, work_duration.split(':'))
                time_delta = datetime.timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def convert_date_time(self,date_obj):
        date_time_obj = '-'
        try:
            date_time_obj = datetime.datetime.strptime(date_obj, '%Y-%m-%d %H:%M').strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj
    
    def convert_hrms_date_time(self,date_obj):
        date_time_obj = '-'
        try:
            parsed_time = datetime.datetime.strptime(str(date_obj), '%Y-%m-%d %H:%M:%S.%f%z')
            date_time_obj = parsed_time.strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj  
     
    def get(self, request):
        
        params = request.query_params
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        
        company_emp_ids = tuple(EmployeeWorkDetails.objects.filter(employee_status='Active',employee_number__isnull=False).values_list('employee_number', flat=True))
        # start_date = parser.parse(start_date)
        # end_date = parser.parse(end_date)
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        if end_date < start_date:
            message = "To Date Should Be Greater Than The From Date"
            return Response(
                    error_response(message , message, 404),
                    status=status.HTTP_404_NOT_FOUND
                )  
        final_data_list = []
        if (end_date - start_date).days > 31:
            return Response(
                        error_response("Start Date and End Date cant be more than a Month", 404),
                        status=status.HTTP_404_NOT_FOUND
                        )
            
        empl_ids = []
        if "employee_id" in params:
            emp_code = search_filter_decode(params.get("employee_id"))
            q_filters = (
                    db_models.Q(employee_number__icontains=emp_code)
                )
            empl_ids = EmployeeWorkDetails.objects.filter(q_filters,employee_status='Active').values_list('employee_number',flat=True)
            if not empl_ids.exists():
                return Response(
                        error_response("No Data Found For The Selected Dates", "No Data Found For The Selected Dates", 404),
                        status=status.HTTP_404_NOT_FOUND
                )
                    
        for i in range((end_date-start_date).days + 1):
            st_date = str((start_date + datetime.timedelta(days=i)).date())
            ed_date = str((start_date + datetime.timedelta(days=i+1)).date())
            emp_ids = tuple(empl_ids)
            if empl_ids and len(empl_ids) == 1:
                emp_code = empl_ids.first()
                query = f"SELECT * FROM vg_attendance_logs WHERE empcode = '{emp_code}' AND logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59';"
            elif empl_ids and len(empl_ids) > 1:
                query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59' AND empcode in {emp_ids};"
            else:
                query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59' AND empcode in {company_emp_ids};"

            conn = pymysql.connect(host=ssh_host, user=sql_username,
                passwd=sql_password, db=sql_main_database,
                port=sql_port)
            data = pd.read_sql_query(query, conn) 
            df_data = pd.DataFrame(data,columns=['attendance_log', 'empcode', 'logdatetime', 'logdate', 'logtime',
                                                    'direction', 'WorkCode', 'port_out'])
            df_data["logdatetime"]=pd.to_datetime(df_data['logdatetime']).dt.strftime('%Y-%m-%d %H:%M')
            df_sorted = df_data.sort_values(by='logdatetime')
            df_data = df_sorted.drop_duplicates(subset=['logdatetime', 'empcode'])
            df_data['checkin_checkout'] = df_data.apply(lambda obj : {"time": obj["logdatetime"], "direction": obj["direction"]}, axis=1)
            df_data['in_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="out" else None, axis=1)
            df_data['out_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="in" else None, axis=1)
            hrms_clockin_data = EmployeeCheckInOutDetails.objects.filter(date_of_checked_in__range = [st_date,ed_date]).annotate(
                employee_name =  db_models.F("employee__user__username"),
                selected_tz=db_models.F('employee__assignedattendancerules__attendance_rule__selected_time_zone'),
                designation = db_models.F('employee__work_details__designation__name') 
            ).values("employee__work_details__employee_number","employee_name","date_of_checked_in",
                    "time_in","latest_time_in","time_out","work_duration","break_duration","breaks","extra_data", "selected_tz", "designation")
            df_checkin_data = pd.DataFrame(hrms_clockin_data, 
                                        columns=["employee__work_details__employee_number","employee_name","date_of_checked_in","time_in",
                                                    "latest_time_in","time_out","work_duration","break_duration","breaks","extra_data",  "selected_tz", "designation"])
            df_checkin_data.rename(columns={'employee__work_details__employee_number':'empcode'}, inplace=True)
            if not df_checkin_data.empty:
                df_checkin_data.selected_tz =  df_checkin_data.selected_tz.fillna(settings.TIME_ZONE)
                df_checkin_data = df_checkin_data.fillna(np.nan).replace([np.nan], [None])
                df_checkin_data['time_in'] = df_checkin_data.apply(lambda x: localize_dt(x['time_in'], x['selected_tz']) if x['time_in'] else '-', axis=1)
                df_checkin_data['time_out'] = df_checkin_data.apply(lambda x: localize_dt(x['time_out'], x['selected_tz']) if x['time_out'] else '-', axis=1)
            df_data = df_data.groupby(['empcode']).agg({
                                                'logdatetime':list,
                                                'logdate':list,
                                                'direction':list,
                                            'checkin_checkout': list,
                                                'in_direction':list,
                                                'out_direction':list,
                                                }).reset_index()
            final_df = pd.merge(df_data, df_checkin_data, how="left", on='empcode') 
            final_df['employee_name'] = final_df.empcode.apply(lambda x: EmployeeWorkDetails.objects.filter(employee_number=x).first().employee.user.username if EmployeeWorkDetails.objects.filter(employee_number=x) else x)
            if not final_df.empty:
                final_df['in_outs'] = final_df.apply(lambda obj: self.system_in_out(dict(obj)), axis=1)
                final_df['total_work_duration'] = final_df.apply(lambda obj: self.calculate_work_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                final_df['total_break_duration'] = final_df.apply(lambda obj: self.calculate_break_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                
                final_df['bio_check_in_time'] = final_df.apply(lambda obj: self.convert_date_time(obj['in_direction'][0]) if obj['in_direction']  else '-', axis=1)
                final_df['bio_check_out_time'] = final_df.apply(lambda obj: self.convert_date_time(obj['out_direction'][-1]) if obj['out_direction']  else '-', axis=1)
                final_df['hrms_check_in_time'] = final_df.apply(lambda obj: self.convert_hrms_date_time(obj['time_in']) if obj['time_in'] else '-', axis=1)
                final_df['hrms_check_out_time'] = final_df.apply(lambda obj: self.convert_hrms_date_time(obj['time_out']) if obj['time_out'] else '-', axis=1)
                final_df['ip_address'] = final_df.apply(lambda obj: obj['extra_data'].get('punch_history')[-1].get('ip_address') if not isinstance(obj['extra_data'],float) and obj['extra_data'] else '-', axis=1)
                final_df['date_of_checked_in'] = datetime.datetime.strptime(st_date, '%Y-%m-%d').strftime('%d-%m-%Y')
                final_df.rename(
                columns={'date_of_checked_in':'Date Of Check In', 'empcode':'Emp Id', 'designation':'Designation', 'bio_check_in_time':'Biometric Check In Time',
                            'bio_check_out_time':'Biometric Check Out Time', 'hrms_check_in_time':'HRMS Check In Time', 'hrms_check_out_time':'HRMS Check Out Time',
                            'ip_address':'IP Address', 'employee_name':'Emp Name', 'total_work_duration':'Biometric Work Duration', 'total_break_duration':'Biometric Break Duration',
                            'work_duration':'HRMS Work Duration', 'break_duration':'HRMS Break Duration', 
                            
                            }
                , inplace=True)
                final_df = final_df[['Date Of Check In', 'Emp Id', 'Emp Name', 'Designation', 'Biometric Check In Time', 'Biometric Check Out Time', 'HRMS Check In Time', 'HRMS Check Out Time',
                                         'Biometric Work Duration', 'Biometric Break Duration', 'HRMS Work Duration', 'HRMS Break Duration', 'IP Address']]
                final_df = final_df.drop_duplicates(['Emp Id'])
                data_dict = final_df.to_dict('records')
                final_data_list.extend(data_dict)
            
        if not final_data_list:
            return Response(
                    error_response("No Data Found For The Selected Dates", "No Data Found For The Selected Dates", 404),
                    status=status.HTTP_404_NOT_FOUND
                )  
        final_data_df =  pd.DataFrame(final_data_list,columns=['Date Of Check In', 'Emp Id', 'Emp Name', 'Designation', 'Biometric Check In Time', 'Biometric Check Out Time', 
                                                               'HRMS Check In Time', 'HRMS Check Out Time', 
                                                               'Biometric Work Duration', 'Biometric Break Duration', 'HRMS Work Duration', 'IP Address'])  
        final_data_df = final_data_df.fillna("-")
        final_data_df['Designation'] = final_data_df.apply(lambda obj:
            EmployeeWorkDetails.objects.filter(employee_number=obj['Emp Id']).values_list('designation__name',flat=True).first() if obj['Designation'] == '-' else obj['Designation'], axis=1)
        conn.close()
        file_name = f"export_biometric_records_{timezone_now().date()}.xlsx"
        return excel_converter(final_data_df,file_name)
    
class BiometricAttandanceLogsFiltersAPIView(APIView):
    
    # permission_classes = [permissions.IsAuthenticated]
    model = EmployeeCheckInOutDetails
    pagination_class = CustomPagePagination
    
    def convert_to_string(self,timestamp):
        if pd.notna(timestamp):  # Check if it's not NaT
            return timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return ""  # Or any other string for NaT
    
    def system_in_out(self, obj):
        obj['in_outs'] = []
        for chhh in obj['checkin_checkout']:
            if len(obj['in_outs']) == 0:
                obj['in_outs'].append({'break_duration': "-", "work_duration": "-"})
                if chhh['direction'] == "in":
                    obj['in_outs'][0]['in'] = chhh["time"]
                    obj['in_outs'][0]['out'] = '-'
                if chhh['direction'] == "out":
                    obj['in_outs'][0]['out'] =  chhh["time"]
                    obj['in_outs'][0]['in'] = '-'
                    obj['in_outs'][0]['work_duration'] = '-'
            else:
                if chhh['direction'] == "out":
                    obj['in_outs'][-1]['out'] =  chhh["time"]
                    obj['in_outs'][-1]['work_duration'] = mins_to_hrs((datetime.datetime.strptime(chhh["time"], "%Y-%m-%d %H:%M") - datetime.datetime.strptime(obj['in_outs'][-1]['in'], "%Y-%m-%d %H:%M")).seconds // 60) if obj['in_outs'][-1]['in'] != '-' else '-'
                if chhh['direction'] == "in":
                    obj['in_outs'].append(
                        {
                            'break_duration': mins_to_hrs((datetime.datetime.strptime(chhh["time"], "%Y-%m-%d %H:%M") - datetime.datetime.strptime(obj['in_outs'][-1]['out'], "%Y-%m-%d %H:%M")).seconds // 60) if obj['in_outs'][-1]['out'] != '-' else '-',
                            "in": chhh["time"],
                            'out': "-", "work_duration": "-"
                        }
                    )
        return obj['in_outs']
    
    def calculate_work_duration(self, in_outs):
        total_time = datetime.timedelta()

        for time_data in in_outs:
            work_duration = time_data.get('work_duration')
            if work_duration and work_duration != '-':
                hours, minutes = map(int, work_duration.split(':'))
                time_delta = datetime.timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def calculate_break_duration(self, in_outs):
        total_time = datetime.timedelta()

        for time_data in in_outs:
            work_duration = time_data.get('break_duration')
            if work_duration and work_duration != '-':
                hours, minutes = map(int, work_duration.split(':'))
                time_delta = datetime.timedelta(hours=hours, minutes=minutes)
                total_time += time_delta

        total_hours = total_time.seconds // 3600
        total_minutes = (total_time.seconds % 3600) // 60

        return f"{total_hours}:{total_minutes:02}"
    
    def convert_date_time(self, date_obj):
        date_time_obj = '-'
        try:
            date_time_obj = datetime.datetime.strptime(date_obj, '%Y-%m-%d %H:%M').strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj
    
    def convert_hrms_date_time(self, date_obj):
        date_time_obj = '-'
        try:
            parsed_time = datetime.datetime.strptime(str(date_obj), '%Y-%m-%d %H:%M:%S.%f%z')
            date_time_obj = parsed_time.strftime('%I:%M %p')
        except Exception as e:
            pass
        return date_time_obj  
     
    def get(self, request):
        try:
            params = request.query_params
            start_date = params.get("start_date")
            end_date = params.get("end_date")
            company_emp_ids = tuple(EmployeeWorkDetails.objects.filter(employee_status='Active',employee_number__isnull=False).values_list('employee_number', flat=True))
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
            if end_date < start_date:
                message = "To Date Should Be Greater Than The From Date"
                return Response(
                        error_response(message , message, 404),
                        status=status.HTTP_404_NOT_FOUND
                    )  
            emp_code = employee_ids = ''
            if "employee_id" in params:
                employee_ids = params.get("employee_id").split(',')
            if "search_key" in params:
                emp_code = search_filter_decode(params.get("search_key"))
            final_data_list = []
            for i in range((end_date-start_date).days + 1):
                st_date = str((start_date + datetime.timedelta(days=i)).date())
                ed_date = str((start_date + datetime.timedelta(days=i+1)).date())
                if emp_code:
                    q_filters = (
                        db_models.Q(employee__user__username__icontains=emp_code) |
                        db_models.Q(employee__official_email__icontains=emp_code) |
                        db_models.Q(employee_number__icontains=emp_code)
                    )
                    empl_ids = EmployeeWorkDetails.objects.filter(q_filters,employee_status='Active').values_list('employee_number',flat=True)
                    if not empl_ids.exists():
                        return Response(
                            error_response("No Data Found For The Selected Dates", "No Data Found For The Selected Dates", 404),
                            status=status.HTTP_404_NOT_FOUND
                        ) 
                    emp_ids = tuple(empl_ids)
                    query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59' AND empcode in {emp_ids};"
                    if len(empl_ids) == 1:    
                        emp_code = empl_ids.first()
                        query = f"SELECT * FROM vg_attendance_logs WHERE empcode = '{emp_code}' AND logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59';"
                elif employee_ids:
                    emp_ids = tuple(employee_ids)
                    query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59' AND empcode in {emp_ids};"
                    if len(emp_ids) == 1:    
                        emp_code = emp_ids[0]
                        query = f"SELECT * FROM vg_attendance_logs WHERE empcode = '{emp_code}' AND logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59';"
                else:
                    query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59' AND empcode in {company_emp_ids};"
                # query = f"SELECT * FROM vg_attendance_logs WHERE logdatetime BETWEEN '{st_date} 08:00:00' AND '{ed_date} 07:59:59' AND empcode in {company_emp_ids};"
                conn = pymysql.connect(host=ssh_host, user=sql_username,
                    passwd=sql_password, db=sql_main_database,
                    port=sql_port)
                data = pd.read_sql_query(query, conn) 
                df_data = pd.DataFrame(data,columns=['attendance_log', 'empcode', 'logdatetime', 'logdate', 'logtime',
                                                        'direction', 'WorkCode', 'port_out'])
                df_data["logdatetime"]=pd.to_datetime(df_data['logdatetime']).dt.strftime('%Y-%m-%d %H:%M')
                df_sorted = df_data.sort_values(by='logdatetime')
                df_data = df_sorted.drop_duplicates(subset=['logdatetime', 'empcode'])
                df_data['checkin_checkout'] = df_data.apply(lambda obj : {"time": obj["logdatetime"], "direction": obj["direction"]}, axis=1)
                df_data['in_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="out" else None, axis=1)
                df_data['out_direction'] = df_data.apply(lambda obj : f'{obj["logdatetime"]}' if obj["direction"]!="in" else None, axis=1)
                hrms_filter = db_models.Q(date_of_checked_in__range = [start_date,end_date])
                if emp_code:
                    hrms_filter &= db_models.Q(employee__work_details__employee_number__in=list(empl_ids))
                elif employee_ids:
                    hrms_filter &= db_models.Q(employee__work_details__employee_number__in=list(employee_ids))
                hrms_clockin_data = EmployeeCheckInOutDetails.objects.filter(hrms_filter).annotate(
                    employee_name =  db_models.F("employee__user__username"),
                    selected_tz=db_models.F('employee__assignedattendancerules__attendance_rule__selected_time_zone'),
                    designation = db_models.F('employee__work_details__designation__name') 
                ).values("employee__work_details__employee_number","employee_name","date_of_checked_in",
                        "time_in","latest_time_in","time_out","work_duration","break_duration","breaks","extra_data", "selected_tz", "designation")
                df_checkin_data = pd.DataFrame(hrms_clockin_data, 
                                            columns=["employee__work_details__employee_number","employee_name","date_of_checked_in","time_in",
                                                        "latest_time_in","time_out","work_duration","break_duration","breaks","extra_data",  "selected_tz", "designation"])
                df_checkin_data.rename(columns={'employee__work_details__employee_number':'empcode'}, inplace=True)
                if not df_checkin_data.empty:
                    df_checkin_data.selected_tz =  df_checkin_data.selected_tz.fillna(settings.TIME_ZONE)
                    df_checkin_data = df_checkin_data.fillna(np.nan).replace([np.nan], [None])
                    df_checkin_data['time_in'] = df_checkin_data.apply(lambda x: localize_dt(x['time_in'], x['selected_tz']) if x['time_in'] else '-', axis=1)
                    df_checkin_data['time_out'] = df_checkin_data.apply(lambda x: localize_dt(x['time_out'], x['selected_tz']) if x['time_out'] else '-', axis=1)
                df_data = df_data.groupby(['empcode']).agg({#'attendance_log':list,
                                                    'logdatetime':list,
                                                    'logdate':list,
                                                #   'logtime':list,
                                                    'direction':list,
                                                'checkin_checkout': list,
                                                    'in_direction':list,
                                                    'out_direction':list,
                                                    }).reset_index()
                final_df = pd.merge(df_data, df_checkin_data, how="left", on='empcode') 
                final_df['employee_name'] = final_df.empcode.apply(lambda x: EmployeeWorkDetails.objects.filter(employee_number=x).first().employee.user.username if EmployeeWorkDetails.objects.filter(employee_number=x) else x)
                if not final_df.empty:
                    final_df['in_outs'] = final_df.apply(lambda obj: self.system_in_out(dict(obj)), axis=1)
                    final_df['total_work_duration'] = final_df.apply(lambda obj: self.calculate_work_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                    final_df['total_break_duration'] = final_df.apply(lambda obj: self.calculate_break_duration(obj['in_outs']) if obj['in_outs'] else '-', axis=1)
                final_df = final_df.fillna("-")
                final_df = final_df.fillna(np.nan).replace([np.nan], [None])
                final_df = final_df.drop_duplicates(['empcode'])
                data_dict = final_df.to_dict('records')
                final_data_list.extend(data_dict)
            
            if not final_data_list:
                return Response(
                        error_response("No Data Found For The Selected Dates", "No Data Found For The Selected Dates", 404),
                        status=status.HTTP_404_NOT_FOUND
                    )  
            final_data_df =  pd.DataFrame(final_data_list,columns=['empcode','logdatetime','logdate','direction','checkin_checkout','in_direction','out_direction','employee_name',
                                                                   'date_of_checked_in','time_in','latest_time_in','time_out','work_duration','break_duration','breaks','extra_data',
                                                                   'selected_tz','designation','in_outs','total_work_duration','total_break_duration'])  
            final_data_df = final_data_df.fillna("-")   
            final_data_dict = final_data_df.to_dict('records')
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(final_data_dict, request)
            op_output = paginator.get_paginated_response(page)
            conn.close()
            return Response(
            success_response(
                    op_output, "Successfully fetched Employee Biometric data", 200
                ),
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return Response(
                    error_response("An error occurred.", f'{str(e)} - {traceback.format_exc()}'),
                    status=status.HTTP_400_BAD_REQUEST
                )