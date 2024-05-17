from dateutil.relativedelta import relativedelta
from django.shortcuts import render, redirect
from django.utils import timezone
from attendance.models import AttendanceRuleSettings

from directory.models import DocumentsTypes, Employee, EmployeeAddressDetails, EmployeeDocumentationWork, EmployeeDocuments, EmployeeFamilyDetails, EmployeeReportingManager, EmployeeResignationDetails, EmployeeSalaryDetails, EmployeeWorkDetails, ManagerType, RelationshipTypes

from company_profile.models import Departments, Designations

from payroll.salary_compute_utils import get_all_salary_details
# from payroll.tasks import send_notification_email
from .models import ( EmployeeComplianceNumbers,
                     PayrollInformation, StatesTaxConfig)
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.db.models import Q
import weasyprint

from django.http import HttpResponse

import logging, datetime, calendar

logger = logging.getLogger("django")



##############################
# Web Views // Added by keshav Agarwal 10th may 2023
###########################


def epfDetails(request):
    # logger.warn("in t Received request from ")
    # logger.info("in g Received request from ")
    if request.session.get("cmp_id", None):

        return render(request, "payroll/epf_details.html")


def epfDetailsEdit(request, epfId):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/epf_details_edit.html", {"epfId": epfId})


def esiDetails(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/esi_details.html")


def esiDetailsEdit(request, esiId):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/esi_details_edit.html", {"esiId": esiId})


def profTaxes(request):
    if request.session.get("cmp_id", None):              
        return render(request, "payroll/professional_taxes.html",{"states":StatesTaxConfig.objects.first()})


def profTaxesEdit(request, ptId):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/professional_taxes_edit.html", {"ptId": ptId,"states":StatesTaxConfig.objects.first()})


def salComponent(request):    
    if request.session.get("cmp_id", None):
        return render(request, "payroll/salary_component.html")


def salComponentEdit(request, sal_comp_id):
    if request.session.get("cmp_id", None):
        return render(
            request, "payroll/salary_component_edit.html", {"sal_comp_id": sal_comp_id}
        )


def singleSalComponent(request, sal_comp_id):
    if request.session.get("cmp_id", None):
        return render(
            request, "payroll/salary_component_view.html", {"sal_comp_id": sal_comp_id}
        )


def salComponentAdd(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/salary_component_add.html")


def activeEmployees(request):
    if request.session.get("cmp_id", None):        

        return render(request, "payroll/employees/active_employees.html")


def employeeSalary(request, id):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/employees/employee_salary.html", {"emp_id": id})


def employeeSalaryEdit(request, id):
    if request.session.get("cmp_id", None):
        return render(
            request, "payroll/employees/employee_salary_edit.html", {"emp_id": id}
        )


def esiComplianceReport(request):
    if request.session.get("cmp_id", None):        
        completed_month_year = list(PayrollInformation.objects.filter(employee__company__id=request.session.get("cmp_id"),is_processed=True).values_list('month_year', flat=True).order_by('month_year').distinct())        

        return render(request, "payroll/reports/ESI_compliance_report.html",{"completed_month_year":completed_month_year,"cmp_id":request.session.get("cmp_id")})


def employeeBankDetail(request, id):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/employees/employee_bank.html", {"id": id})

def employeeBankDetailEdit(request, id):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/employees/employee_bank_edit.html", {"id": id})


def employeeLopDetail(request, id):
    if request.session.get("cmp_id", None):
        
        # leaves_month_year = get_month_year_for_payroll_to_run_by_company(request.session.get("cmp_id"))
        leaves_month_year = ...#not using this html rendering
        return render(
            request, "payroll/employees/employee_lop_edit.html", {"emp_id": id,"lop_date":leaves_month_year}
        )


def runPayroll(request):
    if request.session.get("cmp_id", None):

        if request.method == "POST":
            emp_id = request.POST['emp_id']
            dept_id = request.POST['dept_id']
            month_year = request.POST['month_year']
            
            payroll_id = request.POST.get('payroll_id')
            txp = request.POST.get('txp')
            if emp_id:
                emp_id = [emp_id]
            
            if dept_id:
                dept_id = [dept_id]
            
            details_dict = get_all_salary_details(request.session.get("cmp_id"), emp_id, dept_id, month_year,payroll_id,txp)    

            if details_dict['error']:
                details = None 
            else:
                details = details_dict['details']

            return render(
                request, "payroll/employees/create_pay_run.html", {"payroll": details,"emp_id":emp_id,"dept_id":dept_id,"month_year":month_year}
            )
        else:
            from_month_year = AttendanceRuleSettings.objects.get(company__id=request.session.get("cmp_id"))
            completed_month_year = list(PayrollInformation.objects.filter(employee__company__id=request.session.get("cmp_id"),is_processed=True).values_list('month_year', flat=True).order_by('month_year').distinct())        

            month_list = []
            # print("655 - ",completed_month_year)
            if completed_month_year:
                month_list.append((completed_month_year[-1] + relativedelta(months=1)).strftime('%b-%Y'))
            else:
                from_month_year = AttendanceRuleSettings.objects.get(company__id=request.session.get("cmp_id"))    
                payroll_months = from_month_year.attendance_paycycle_end_date - relativedelta(months=1)                
                month_list.append((payroll_months + relativedelta(months=1)).strftime('%b-%Y'))
                # now = timezone.now()
                # current_month = now.month - 1
                # cur_year = now.year
                # if current_month == 0:
                #     current_month = 12                
                #     cur_year = now.year - 1
                    
                # from_month_year = from_month_year.attendance_paycycle_end_date.strftime('%m')        

                # for j in range(int(from_month_year)-1,int(current_month)):
                #     month_list.append(calendar.month_abbr[j]+"-"+str(cur_year))
                
                # for i in completed_month_year:            
                #     cc_month = calendar.month_abbr[int(i.strftime('%m'))]+"-"+str(cur_year)
                #     if cc_month in month_list:
                #         month_list.remove(cc_month)        

            dep_obj = Departments.objects.filter(company_id=request.session.get("cmp_id"))
            emp_obj = Employee.objects.filter((Q(payroll_status=True) | Q(payroll_status__isnull=True)),company__id=request.session.get("cmp_id"))

            # if not month_list:
            #     month_list.append(calendar.month_abbr[int(current_month)]+"-"+str(cur_year))
            context = {
                "month_list":month_list[0],
                "dep_obj":dep_obj,
                "emp_obj":emp_obj
            }

            return render(request, "payroll/employees/run_payroll.html",context)


def rollbackPayroll(request):
    if request.session.get("cmp_id", None):
        if request.method=="POST":         
            # Api- Exist             
            PayrollInformation.objects.filter(id__in=request.POST.getlist('pay_id[]')).delete()
        return redirect('/qxbox/payroll/active-employees/')




def payrollMaster(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/payroll_master.html")


def organizationView(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/view.html")
    
def DashboardView(request, company_id=None, token=None):
    if company_id and token:
        request.session["cmp_id"] = company_id   
      
        return render(request, "payroll/organization/dashboard.html", {"company_id":company_id,"token": token})
    


def paySchedule(request):
    if request.session.get("cmp_id", None):
        # if request.method=="POST":            
        return render(request, "payroll/organization/pay_schedule.html")


def payScheduleEdit(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/pay_schedule_edit.html")


def taxDetails(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/tax_details.html")


def departments(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/departments.html")
 
def designations(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/designations.html")
 

def reimbursement_employee(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/reimbursement/employee.html")
 

def employeePayslips(request, emp_id):
    if request.session.get("cmp_id", None):
        # API - getListofPayslipsForEmployeeApi
        payroll_obj = PayrollInformation.objects.filter(employee__id=emp_id,is_processed=True)
        return render(
            request, "payroll/employees/payroll_history.html", {"payroll_obj": payroll_obj}
        )


def complianceGovtReport(request):
    if request.session.get("cmp_id", None):  
        # Api existed - get_payroll_completed_month_year_list
        completed_month_year = list(PayrollInformation.objects.filter(employee__company__id=request.session.get("cmp_id"),is_processed=True).values_list('month_year', flat=True).order_by('month_year').distinct())        

        return render(request, "payroll/reports/uan_govt_report.html",{"completed_month_year":completed_month_year,"cmp_id":request.session.get("cmp_id")})



@csrf_exempt# using aman for demo only later we will implement by sending emp_id and other details by encryption
def employeePayslipsDetail(request):
    if request.method=="POST":
        emp_id = request.POST['emp_id']
        month_year = request.POST['month_year']
        is_download = eval(request.POST.get("is_download","False"))
        payroll_obj = PayrollInformation.objects.get(
            employee__id=emp_id,
            month_year=month_year
        )
        
        emp_no = ""

        try:
            ewd = EmployeeWorkDetails.objects.get(employee__id=emp_id)
            emp_no = str(ewd.employee_number)
        except:
            emp_no = ""

        ars_obj = AttendanceRuleSettings.objects.get(company__id=payroll_obj.employee.company.id)
        
        pay_day = ars_obj.attendance_input_cycle_to
        pay_day_end = (payroll_obj.month_year).replace(day=pay_day)
        pay_day_start = pay_day_end - relativedelta(months=1) 
        pay_day_start = pay_day_start + relativedelta(days=1)

        if is_download == True:
            html_string = render_to_string("payroll/employees/employee_payslip2.html", {"details": payroll_obj,"pay_day_start":pay_day_start,"pay_day_end":pay_day_end})                                
            # pdf_file = "hi"
            pdf_file = weasyprint.HTML(string=html_string,base_url=request.build_absolute_uri()).write_pdf()
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="Payslip_'+emp_no+'_'+str(payroll_obj.month_year.month)+'_'+str(payroll_obj.month_year.year)+'.pdf"'
            response.write(pdf_file)
            return response

        return render(
            request, "payroll/employees/employee_payslip2.html", {"details": payroll_obj,"pay_day_start":pay_day_start,"pay_day_end":pay_day_end}
        )
    return redirect('/qxbox/payroll/active-employees/')


# By Uday Shankar Start
           
def manageEmployees(request):
    if request.session.get("cmp_id", None):

        return render(request, "payroll/employees/manage_employee_list.html")        

def importLeaveEmployees(request):
    if request.session.get("cmp_id", None):
       
        return render(request, "payroll/employees/leave_lop.html")


def importOvertimeEmployees(request):
    if request.session.get("cmp_id", None):
      
        return render(request, "payroll/employees/import_overtime.html")        



def importVariablePayEmployees(request):
    if request.session.get("cmp_id", None):
      
        return render(request, "payroll/employees/import_variable_pay.html")        


def profileViewEmployees(request,emp_id):
    if request.session.get("cmp_id", None):
        emp_obj = Employee.objects.get(id=emp_id)
        
        context = {
            "emp_obj":emp_obj,
            "keys_updated":set([])
        }
        return render(request, "payroll/employees/profile_View.html",context)        

def profileEditEmployees(request,emp_id):
    if request.session.get("cmp_id", None):
        emp_obj = Employee.objects.get(id=emp_id)

        desig_list = Designations.objects.filter(company=emp_obj.company).values("id","name")
        dept_list = Departments.objects.filter(company=emp_obj.company).values("id","name")
        employee_list = Employee.objects.filter(company=emp_obj.company,payroll_status=True).exclude(id=emp_id).values("id","first_name","middle_name","last_name")
        
        if request.method == "POST":                
            try:        
                # print(request.POST['emp_first_name'],len(request.POST['emp_first_name']))
                emp_obj.first_name      = request.POST['emp_first_name']
                emp_obj.middle_name     = request.POST['emp_middle_name']
                emp_obj.last_name       = request.POST['emp_last_name']

                try:
                    emp_obj.employee_image  = request.FILES['employee_image']
                except:
                    pass
                emp_obj.phone           = request.POST['mobile_no']
                emp_obj.date_of_join    = request.POST['joining_date']
                emp_obj.gender          = request.POST['gender']
                # emp_obj.blood_group     = request.POST['emp_first_name']
                emp_obj.marital_status  = request.POST['marital_status']
                if request.POST['married_date']:
                    emp_obj.anniversary_date = request.POST['married_date']
                emp_obj.personal_email  = request.POST['personal_email']
                emp_obj.official_email  = request.POST['official_email']
                emp_obj.alternate_phone = request.POST['alternate_mobile_no']

                if request.POST['payroll_on_of'] == "1":
                    emp_obj.payroll_status = True
                else:
                    emp_obj.payroll_status = False
                
                # print(request.POST['is_active'])

                # if request.POST['is_active'] == "1":
                    # emp_obj.user.is_active = True
                    # User.objects.filter(id=emp_obj.user.id).update(is_active=True)
                # else:
                    # User.objects.filter(id=emp_obj.user.id).update(is_active=False)

                    # emp_obj.user__is_active = False

                # print(request.POST['dept_id'],Departments.objects.get(id=request.POST['dept_id']))
                                
                emp_obj.save()
                work_obj, _created = EmployeeWorkDetails.objects.get_or_create(employee=emp_obj)
                work_obj.department = Departments.objects.get(id=request.POST['dept_id'])
                work_obj.designation =  Designations.objects.get(id=request.POST['designation_id'])
                work_obj.employee_status = request.POST['is_active']
                work_obj.save()
                
                if request.POST.get('manager_id'):           
                    mtobj, _created = ManagerType.objects.get_or_create(manager_type=10)
                    try:
                        emp_rep_manager = EmployeeReportingManager.objects.get(
                                                                    manager_type= mtobj,
                                                                      employee=emp_obj,
                                                                      is_deleted=False
                        )
                        emp_rep_manager.manager_id=request.POST.get('manager_id')
                        emp_rep_manager.save()
                    except:
                        emp_rep_manager = EmployeeReportingManager.objects.create(
                                                                    manager_type= mtobj,
                                                                      employee=emp_obj,
                                                                      manager_id=request.POST.get('manager_id')
                        )
                

                emp_salary_obj, _created = EmployeeSalaryDetails.objects.get_or_create(employee=emp_obj)

                emp_salary_obj.ctc                  = float(request.POST['ctc'])
                emp_salary_obj.account_number       = request.POST['bank_ac_number']
                emp_salary_obj.bank_name            = request.POST['bank_name']
                emp_salary_obj.branch_name          = request.POST['bank_branch']            
                emp_salary_obj.ifsc_code            = request.POST['bank_ifsc_code']
                # if request.POST['bank_name']:
                #     emp_salary_obj.fund_transfer_type = 'FT' if 'ICICI' in request.POST['bank_name'].upper() else 'NEFT'               
                emp_salary_obj.save()

                try:
                    emp_add_obj = EmployeeAddressDetails.objects.get(employee=emp_obj)
                    
                    emp_add_obj.current_address_line1 = request.POST['curr_street']
                    emp_add_obj.current_address_line2 = request.POST['curr_street1']
                    emp_add_obj.current_state = request.POST['curr_state']
                    emp_add_obj.current_city = request.POST['curr_city']
                    emp_add_obj.current_pincode = request.POST['curr_pincode']
                    emp_add_obj.permanent_address_line1 = request.POST['per_street']
                    emp_add_obj.permanent_address_line2 = request.POST['per_street1']
                    emp_add_obj.permanent_state = request.POST['per_state']
                    emp_add_obj.permanent_city = request.POST['per_city']
                    emp_add_obj.permanent_pincode = request.POST['per_pincode']
                    emp_add_obj.permanent_same_as_current_address = True if (request.POST.get('address_type_id') and (request.POST.get('address_type_id') == "1")) else False                                                                     
                    emp_add_obj.save()
                except:
                    EmployeeAddressDetails.objects.create(
                        employee=emp_obj,
                        current_address_line1 = request.POST['curr_street'],
                        current_address_line2 = request.POST['curr_street1'],
                        current_state = request.POST['curr_state'],
                        current_city = request.POST['curr_city'],
                        current_pincode = request.POST['curr_pincode'],
                        permanent_address_line1 = request.POST['per_street'],
                        permanent_address_line2 = request.POST['per_street1'],
                        permanent_state = request.POST['per_state'],
                        permanent_city = request.POST['per_city'],
                        permanent_pincode = request.POST['per_pincode'],
                        permanent_same_as_current_address = True if (request.POST.get('address_type_id') and request.POST.get('address_type_id') == "1") else False                                                                     
                    )
                print("1110 - ",request.POST['per_street1'])
                
                # emp_add_obj.save()

                mother_rel, _created = RelationshipTypes.objects.get_or_create(relationship_type = 20)
                emp_fam_obj,_created = EmployeeFamilyDetails.objects.get_or_create(
                    employee = emp_obj,
                    relationship = mother_rel
                    )
                emp_fam_obj.name = request.POST['emp_mother_name']
                emp_fam_obj.save()

                father_rel, _created = RelationshipTypes.objects.get_or_create(relationship_type = 10)
                emp_fam_obj,_created = EmployeeFamilyDetails.objects.get_or_create(
                    employee = emp_obj,
                    relationship = father_rel
                    )
                emp_fam_obj.name = request.POST['emp_father_name']
                emp_fam_obj.save()
                                    
                dep, _created = DocumentsTypes.objects.get_or_create(document_type = 10)
                
                # emp_doc, _created = EmployeeDocuments.objects.update_or_create(
                #     employee = emp_obj,
                #     document_type = dep,                
                # )
                emp_doc = EmployeeDocuments.objects.filter(employee = emp_obj).first()
                if not emp_doc:
                    emp_doc = EmployeeDocuments.objects.create(employee = emp_obj)
                emp_doc.document_type = dep    
                emp_doc.document_number = request.POST['pan_number']
                try:
                    emp_doc.select_file = request.FILES['pan_doc']
                except:
                    pass
                emp_doc.save()

                dep, _created = DocumentsTypes.objects.get_or_create(document_type = 20)
                # emp_doc, _created = EmployeeDocuments.objects.update_or_create(
                #     employee = emp_obj,
                #     document_type = dep,                
                # )
                emp_doc = EmployeeDocuments.objects.filter(employee = emp_obj).first()
                if not emp_doc:
                    emp_doc = EmployeeDocuments.objects.create(employee = emp_obj)
                emp_doc.document_type = dep 
                emp_doc.document_number = request.POST['anumber']
                try:
                    emp_doc.select_file = request.FILES['aadhar_doc']
                except:
                    pass
                emp_doc.save()
                emp_salary_admin, _created = EmployeeComplianceNumbers.objects.get_or_create(employee=emp_obj)                
                # print(emp_salary_admin, _created)
                if request.POST['pf_no']:
                    emp_salary_admin.pf_num = request.POST['pf_no']
                if request.POST['uan_no']:            
                    emp_salary_admin.uan_num = request.POST['uan_no']
                if request.POST['emp_esi_no']:
                    emp_salary_admin.esi_num = request.POST['emp_esi_no']
                emp_salary_admin.nominee_name = request.POST['nominee_name']
                emp_salary_admin.nominee_rel = request.POST['nominee_relationship']
                emp_salary_admin.nominee_dob = request.POST['nominee_dob'] if request.POST['nominee_dob'] else None
                try:
                    emp_salary_admin.save()
                except:
                    pass

                resignation_date = request.POST.get('resignation_date')
                notice_period = request.POST.get('notice_period')
                comments = request.POST.get('comments')
                termination_date = request.POST.get('termination_date')
                
                emp_resignation_obj, _resign_created = EmployeeResignationDetails.objects.get_or_create(employee=emp_obj)
                if resignation_date:
                    emp_resignation_obj.resignation_date = resignation_date
                if notice_period:
                    emp_resignation_obj.notice_period = int(notice_period)
                if comments:
                    emp_resignation_obj.comments = comments
                if termination_date:
                    emp_resignation_obj.termination_date = termination_date
                if resignation_date and notice_period:
                    emp_resignation_obj.last_working_day = resignation_date + datetime.timedelta(days=int(notice_period))
                emp_resignation_obj.save()

                emp_doc_work = list(EmployeeDocumentationWork.objects.filter().values_list('id',flat=True))

                attachment_titles = request.POST.getlist('attachment_titles')
                attachment_files = request.FILES.getlist('attachment_files')                
                count_file = 0
                for attach_files in attachment_files:                                    
                    EmployeeDocumentationWork.objects.get_or_create(employee = emp_obj,
                                                                document_title = attachment_titles[count_file],
                                                                select_file = attach_files
                                                                )    
                    count_file += 1            
                
                existing_attachment_ids = request.POST.getlist('attachment_id')
                
                
                if len(existing_attachment_ids) > 0:
                    existing_attachment_file = request.POST.getlist('attachment_files_id')                    
                    ids_to_remove = [x for x in emp_doc_work if str(x) not in existing_attachment_ids]                    
                    EmployeeDocumentationWork.objects.filter(id__in=ids_to_remove).delete()
                    
                    count_exst_file = 0
                    for ea_ids in existing_attachment_ids:
                        if existing_attachment_file[count_exst_file]:
                            EmployeeDocumentationWork.objects.filter(id=ea_ids).update(
                                select_file = existing_attachment_file[count_exst_file]
                            )
                        count_exst_file += 1


                # return redirect('profile_edit_employees', emp_id=emp_obj.id)
                return redirect('manage_employees_view')
            except Exception as e:
                print(e)
                # return
            
        context = {
            "emp_obj":emp_obj,
            "desig_list":desig_list,
            "dept_list":dept_list,
            "employee_list":employee_list
        }

        return render(request, "payroll/employees/profile_Edit.html",context)

def profileAddEmployees(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/employees/profile_Add.html")

def importDataEmployees(request):
    if request.session.get("cmp_id", None):
      
        return render(request, "payroll/employees/Emp_ImportData.html")


def taxDetailsEdit(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/tax_details_Edit.html")

def organizationSetupEdit(request):
    if request.session.get("cmp_id", None):
        return render(request, "payroll/organization/organizationSetupEdit.html",{"states":StatesTaxConfig.objects.first()})


def repHoldSalary(request):
    if request.session.get("cmp_id", None):
        
        return render(request, "payroll/reports/Reports_hold_status.html")    

def repPayrollOverview(request):
    if request.session.get("cmp_id", None):
        
        return render(request, "payroll/reports/Reports_employeeSalaryStatement.html")
    
def repEpfSummary(request):
    if request.session.get("cmp_id", None):
       
        return render(request, "payroll/reports/Reports_viewEpfSummary.html")
    

def repEsiSummary(request):
    if request.session.get("cmp_id", None):
       
        return render(request, "payroll/reports/Reports_viewEsiSummary.html")  


def repPtSlab(request):
    if request.session.get("cmp_id", None):
       
        return render(request, "payroll/reports/Reports_viewPtSlab.html")  


def repPtSummary(request):
    if request.session.get("cmp_id", None):
        
        return render(request, "payroll/reports/Reports_viewPtSummary.html")    


def repEmpReports(request):    
    if request.session.get("cmp_id", None):
        
        return render(request, "payroll/reports/Reports_employee_details.html")


def repGratutyReports(request):    
    if request.session.get("cmp_id", None):
        
        return render(request, "payroll/reports/Reports_gratuty.html")


def repAuditReport(request):
    if request.session.get("cmp_id", None):
       
        return render(request, "payroll/reports/Reports_view_auditReport.html")    


def repMissingInfoReport(request):
    if request.session.get("cmp_id", None):
     
        return render(request, "payroll/reports/Reports_view_missingInfo.html")    


def repSalaryInfoReport(request):
    if request.session.get("cmp_id", None):        
       
        return render(request, "payroll/reports/Reports_view_salaryReport.html")    


# def repMonthlyTDSReport(request):
#     if request.session.get("cmp_id", None):
#         of_date = request.GET.get("of_date")        
        
#         query_filters = Q(is_deleted=False) & Q(is_processed=True)
#         query_filters &= Q(employee__company__id=request.session.get("cmp_id"))
        
#         if of_date:
#             query_filters &= Q(month_year=of_date)

#         all_emp_obj = PayrollInformation.objects.filter(query_filters).values('month_year').annotate(total=Sum('monthly_tds')).order_by('-month_year')
        
#         context = {
#             "salary_inst":all_emp_obj,        
#         }
#         return render(request, "payroll/reports/Reports_view_tdsReport.html",context)    


def repAllMonthTDSReport(request):
    if request.session.get("cmp_id", None):       
       
        return render(request, "payroll/reports/Reports_all_month_tds.html")
    

def repVarianceReport(request):
    if request.session.get("cmp_id", None):
      
        now = timezone.now()        
        
        context = {            
            "prev_yr": now.year - 1
        }
        return render(request, "payroll/reports/Reports_view_varianceReport.html",context)    


def repLogReport(request):
    if request.session.get("cmp_id", None):
       
        return render(request, "payroll/reports/Reports_view_logReport.html")    


def savingDeclarationForms(request):    
    if request.session.get("cmp_id", None):
        return render(request, "payroll/saving_declaration/saving_declaration_forms.html")

def savingUserSubmittedForms(request,id):    
    if request.session.get("cmp_id", None):
        return render(request, "payroll/saving_declaration/user_submitted_forms.html",{"id":id})

def savingApproveEmpForms(request):    
    if request.session.get("cmp_id", None):
        return render(request, "payroll/saving_declaration/approve_employee_form.html")
    
def savingAllEmpForms(request):    
    if request.session.get("cmp_id", None):
        return render(request, "payroll/saving_declaration/submitted_employee_forms.html")

def savingDeclarationSetup(request):    
    if request.session.get("cmp_id", None):
        return render(request, "payroll/saving_declaration/declaration_setup.html")


def leaveReportsView(request):
    if request.session.get("cmp_id", None):
        return render(request,"payroll/reports/Reports_view_leaveReport.html")