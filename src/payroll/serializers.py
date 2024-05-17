from rest_framework import serializers
from django.utils import timezone
from attendance.models import AttendanceRuleSettings, EmployeeMonthlyAttendanceRecords

from directory.models import (
    DocumentsTypes,
    Employee,
    EmployeeDocuments, 
    EmployeeSalaryDetails, 
    RelationshipTypes,
    EmployeeFamilyDetails,    
    EmployeeEmergencyContact,
    EmployeeWorkDetails
)
from company_profile.models import Departments, SubDepartments, Designations
from dateutil.relativedelta import relativedelta
from rest_framework.exceptions import ValidationError

from investment_declaration.models import InvestmentDeclaration
from HRMSApp.models import CompanyDetails,User
from leave.models import LeavesHistory
from django.db import transaction
from .models import *
from .utils import ctc_to_gross_per_year, get_payroll_month_year
from core.serializers import DynamicFieldsModelSerializer
from core.utils import timezone_now
from datetime import datetime
from datetime import date

from django.utils.text import slugify
from django.db.models import Sum


class CompanyNameImgSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDetails
        fields = ["id", "company_name", "company_image"]


class CompanyIdNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyDetails
        fields = ["id", "company_name"]


class StateNameTaxConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatesTaxConfig
        fields = ["id", "state","tax_config"]


class EpfSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpfSetup
        fields = (
            "id",
            "company",
            "epf_number",
            "employer_contribution",
            "employee_contribution",
            "is_employer_contribution_in_ctc",
        )


class EsiSerializer(serializers.ModelSerializer): 
    class Meta:
        model = Esi
        fields = (
            "id",
            "company",
            "esi_no",
            "employee_contribution_pct",
            "employer_contribution_pct",
            "is_employer_contribution_in_ctc",            
        )


class ProfessionTaxSerializer(serializers.ModelSerializer):    
    company = CompanyIdNameSerializer(read_only=True)    
    state = StateNameTaxConfigSerializer()
    class Meta:
        model = ProfessionTax
        fields = ("id", "company", "state", "is_enabled")

    def update(self, instance, validated_data):           
        instance.is_enabled = validated_data.get('isEnabled', instance.is_enabled)        
        instance.state = StatesTaxConfig.objects.get(state=validated_data.get('state').get('state'))
        instance.save()      
        return instance


class PaySalaryComponentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaySalaryComponents
        fields = (
            "id",
            "company",
            "earning_type",
            "component_name",
            "name_on_payslip",
            "calculation_type",
            "flat_amount",
            "pct_of_basic",
            "threshold_base_amount",
            "is_active",
            "is_part_of_salary_structure",
            "is_taxable",
            "is_prorated",
            "is_part_of_flexible_plan",
            "is_part_of_epf",
            "is_part_of_esi",
            "is_visible_on_payslip",
            "is_default",
        )

    def validate(self, attrs):
        "need to implement this validation model level"
        if attrs["calculation_type"] == 0:
            attrs["pct_of_basic"] = 0
            attrs["flat_amount"] = 0
        elif attrs["calculation_type"] == 1:
            attrs["pct_of_basic"] = 0
            attrs["threshold_base_amount"] = 0
        else:  # which comes if selected as pct_amount
            attrs["threshold_base_amount"] = 0
            attrs["flat_amount"] = 0
        return attrs


class RegimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regime
        fields = ["regime_name", "regime_month_year"]


class EmployeeBankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSalaryDetails
        fields = [
            "bank_name",
            "account_number",
            "ifsc_code",
            "branch_name",
            "account_type",
            "account_holder_name",
            "ctc"
        ]

class EmployeeSerializer(DynamicFieldsModelSerializer):

    company_name = serializers.SlugRelatedField(
        read_only=True, slug_field="company_name", source="company"
    )
    # department = serializers.SerializerMethodField()
    gross_per_month = serializers.SerializerMethodField()

    bank_details = serializers.SerializerMethodField()
    salary_details = serializers.SerializerMethodField()    
    lop_setup = serializers.SerializerMethodField()
    payslips = serializers.SerializerMethodField()

    # emp_number = serializers.SerializerMethodField()
    emp_number = serializers.ReadOnlyField()
    department = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "emp_number",
            "first_name",
            "middle_name",
            "last_name",
            "company_name",
            "department",
            "gross_per_month",
            "bank_details",
            "salary_details",            
            "lop_setup",
            "payslips",
        ]

                                                #USING ANNOTATE FOR SIMPLE METHOD FIELDS
    # def get_department(self, obj):
    #     try:
    #         if obj and obj.work_details and obj.work_details.department and obj.work_details.department.name:
    #             dept_obj = obj.work_details.department.name
    #         else:
    #             dept_obj = ""
    #         return str(dept_obj)
    #     except Exception as e:
    #         return str(e)
        
    # def get_emp_number(self, obj):
    #     try:
    #         if obj and obj.work_details and obj.work_details.employee_number:
    #             dept_obj = obj.work_details.employee_number
    #         else:
    #             dept_obj = ""
    #         return str(dept_obj)
    #     except Exception as e:
    #         return str(e)

    def get_gross_per_month(self, obj):
        try:
            # return round(ctc_to_gross_per_year(obj.salary_details.ctc) / 12)
            # EmployeeSalaryDetails
            # employer_pf = obj.company.epf_comp.is_employer_contribution_in_ctc        
            # employer_esi = obj.company.esi_comp.is_employer_contribution_in_ctc            
            employer_esi_pct = obj.company.esi_comp.employer_contribution_pct
            emp_ctc = obj.salary_details.ctc                        
            return round(ctc_to_gross_per_year(emp_ctc,employer_esi_pct)/12)
        except Exception as e:
            return {"error": str(e)}

    def get_bank_details(self, obj):
        try:            
            if (
                obj.salary_details.bank_name 
                and obj.salary_details.ifsc_code 
                and obj.salary_details.account_number
                and obj.salary_details.branch_name
            ):
                return {"status":"Complete","id":obj.salary_details.id}
            
            return {"status":"in-complete"}          
        except Exception as e:            
            return {"status":"in-complete"}

    def get_salary_details(self, obj):
        try:            
            
            if (obj.salary_details.ctc and (obj.salary_details.ctc > 0)) or (obj.salary_details.fixed_salary and (obj.salary_details.fixed_salary > 0)):
              
                return {"id": obj.salary_details.id,"status":"Complete"}
            return {"status":"in-complete"}
        except Exception as e:            
            return {"status":"in-complete"}
   

    def get_lop_setup(self, obj):        
        # leaves_month_year = get_month_year_for_payroll_to_run_by_company(obj.company.id)      
        leaves_month_year = get_payroll_month_year(obj.company)['payroll_month']  
        leaves_month_year = leaves_month_year - relativedelta(months=1)        
        # try:        
        emar_obj = EmployeeMonthlyAttendanceRecords.objects.filter(
            employee_id=obj.id,
            year = int(leaves_month_year.strftime('%Y')),
            month = int(leaves_month_year.strftime('%m'))
        )        
        if emar_obj.exists():
            if emar_obj[0].is_hr_updated:   
        # if emar_obj and emar_obj.is_hr_updated: 
                return {"status":True}
            else:
                return {"status":False}
        else:                                
            # emplop_inst = EmployeeLops.objects.get(employee=obj.id,lop_month_year=leaves_month_year.strftime('%Y-%m-01'))
            # return {"status":emplop_inst.is_final}                
            return {"status":False}


    def get_payslips(self, obj):
        """
        this will get after the payroll run
        """
        try:
            completed_month_year = obj.emp_payroll_info.filter(is_processed=True).order_by('-month_year')
            if completed_month_year:
                completed_month_year = completed_month_year.first().month_year
                month_year = completed_month_year.strftime('%Y-%m-01')
                month_year_str = completed_month_year.strftime('%B-%Y')                        
                
                payroll_inst = PayrollInformation.objects.get(employee__id=obj.id, month_year=month_year)        
                return "Last Generated - "+str(month_year_str) if payroll_inst.is_processed else "Not Processed"
            else:
                return "Not Generated"
        except Exception as e:     
            return str(e)

class HealthEducationCessSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthEducationCess
        fields = [
            "health_education_name",
            "health_education_cess",
            "health_education_month_year",
        ]

# class EmployeeLopsSerializer(serializers.ModelSerializer):
#     is_from = serializers.CharField(read_only=True)
#     class Meta:
#         model = EmployeeLops
#         fields = [
#             "id",
#             "employee",            
#             "lop_month_year",
#             "total_leaves_count",
#             "total_lop_count",
#             "leaves_encashed",
#             "is_from",
#         ]

#     def validate(self, attrs):
#         employee = attrs.get('employee')
#         lop_month_year = attrs.get('lop_month_year')

#         # Checks if a record already exists with the same employee and lop_month_year
#         if EmployeeLops.objects.filter(employee=employee, lop_month_year=lop_month_year).exists():
#             raise serializers.ValidationError({"error_msg":
#                 f"An entry fo this {employee} and {lop_month_year} combination already exists."
#             })

#         return attrs
    
class PayrollLeavesHistorySerializer(serializers.ModelSerializer):
    is_from = serializers.CharField()
    lop_count = serializers.FloatField()
    leaves_count = serializers.FloatField()

    class Meta:
        model = LeavesHistory
        fields = [                        
            "is_from",
            "lop_count",
            "leaves_count",
            "employee",
        ]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email',"phone","username",'is_active']

import requests, re
def validate_pan(pan_number):
    pattern = r'^[A-Z]{3}P[A-Z]{1}[0-9]{4}[A-Z]{1}$'
    match = re.match(pattern, pan_number)
    return match is not None

def validate_aadhaar(aadhaar_number):
    pattern = r'^[2-9]{1}[0-9]{11}$'
    match = re.match(pattern, aadhaar_number)
    return match is not None


class EmpComplianceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeComplianceNumbers
        fields = '__all__'
class EmployeeBulkImportSerializer(serializers.ModelSerializer):
    user = UserSerializer(write_only=True,required=False)
    # Required
    Emp_first_name = serializers.CharField(source="first_name")
    Official_Email =  serializers.EmailField(source="official_email")
    Mobile_no = serializers.CharField(source="phone")
    Gender = serializers.CharField(source="gender")
    Joining_date = serializers.DateField(source="date_of_join")
    Pan_number = serializers.CharField(required=True)
    Aadhaar_Number = serializers.CharField(required=True)
    ctc = serializers.DecimalField(required=True,max_digits=12,decimal_places=2)
    Department = serializers.CharField(required=True)
    
    # Not Required
    Emp_Middle__name  = serializers.CharField(source="middle_name",required=False,allow_null=True,allow_blank=True)
    Emp_Last_name  = serializers.CharField(source="last_name",required=False,allow_null=True,allow_blank=True)
    emp_image = serializers.FileField(source="employee_image", required=False)    
    Dob = serializers.DateField(source="date_of_birth",required=False,allow_null=True) #no allow_blank=True for datefield need to set it
    Marital_status = serializers.CharField(source="marital_status",required=False,allow_null=True,allow_blank=True)
    Married_date = serializers.DateField(source="anniversary_date",required=False,allow_null=True)
    Personal_email = serializers.EmailField(source="personal_email",required=False,allow_null=True,allow_blank=True)    
    alternate_mobile_no_ = serializers.CharField(source="alternate_phone",required=False,allow_null=True,allow_blank=True)
    Emp_father_name = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    Emp_mother_name = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    Emp_spouse_name = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    Emergency_contact_no = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    Sub_Department = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    Designation = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
 
    bank_name = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    ifsc_code = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    branch_name = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    account_number = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    
    pf_no = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    uan_no = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    emp_esi_no = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    nominee_name = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    nominee_relationship = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    nominee_dob = serializers.DateField(required=False,allow_null=True)    

    Regime_type = serializers.CharField(required=False,allow_null=True,allow_blank=True)    
    approved_amount = serializers.CharField(required=False,allow_null=True,allow_blank=True)    

    class Meta:
        model = Employee
        fields = [
            "Emp_first_name","Emp_Middle__name","Emp_Last_name","Dob","Marital_status","Married_date","Mobile_no",
            "Personal_email","Gender","Joining_date","Official_Email","alternate_mobile_no_","company","Emp_father_name",
            "Emp_mother_name","Emp_spouse_name","Pan_number","Aadhaar_Number","Emergency_contact_no","user","ctc"            
            ,"Department","Designation","Sub_Department","bank_name","ifsc_code","branch_name","account_number","Regime_type",
            "approved_amount","emp_image", "pf_no", "uan_no", "emp_esi_no", "nominee_name", "nominee_relationship", "nominee_dob",
        ]
    
    def validate(self,data):
        
        validations_list=[]
        
        if data['ifsc_code']:
            ifsc_valid = requests.get("https://ifsc.razorpay.com/"+str(data["ifsc_code"])).status_code
            if ifsc_valid!=200:
                validations_list.append("IFSC is not valid") 

        if data["Pan_number"] and not validate_pan(data["Pan_number"]): 
            validations_list.append("PAN is not valid") 

        if data["Aadhaar_Number"] and not validate_aadhaar(data["Aadhaar_Number"]): 
            validations_list.append("AADHAR is not valid") 
        
        data["user"]={"email":data["official_email"], "phone":data["phone"],"is_active":True,"username":data["official_email"]}
        user_data = UserSerializer(data = data["user"])
        if not user_data.is_valid():
             for key,val in user_data.errors.items():                                                                    
                if key == "non_field_errors":                                                             
                    validations_list += [err for err in val]
                else:                                        
                    validations_list.append(val)
            # validations_list.append(str(user_data.errors))
        
        if data['account_number']:
            if EmployeeSalaryDetails.objects.filter(account_number=data['account_number']).count() > 0:
                validations_list.append("Bank Account Number is Duplicate")

        if validations_list:
            raise ValidationError(validations_list)
    
        return data
    
    # @transaction.atomic
    def create(self,validated_data):
        # print("hello",validated_data)
        try:
            sid = transaction.set_autocommit(autocommit=False)
            user_data = UserSerializer(data=validated_data["user"])
            # print(user_data.is_valid())
            if user_data.is_valid():                
                user_obj=user_data.save()
            else:
                raise serializers.ValidationError(user_data.errors)
            validated_data["user"]=user_obj 

            #popping as these fields not present in Employee model
            Emp_father_name = validated_data.pop("Emp_father_name","")
            Emp_mother_name = validated_data.pop("Emp_mother_name","")
            Emp_spouse_name = validated_data.pop("Emp_spouse_name","")
            Pan_number = validated_data.pop("Pan_number","")
            Aadhaar_Number = validated_data.pop("Aadhaar_Number","")
            Emergency_contact_no = validated_data.pop("Emergency_contact_no","")
            ctc = validated_data.pop("ctc","")
            department = validated_data.pop("Department","")
            sub_department = validated_data.pop("Sub_Department","")
            designation = validated_data.pop("Designation","")
            
            bank_name = validated_data.pop("bank_name","")
            ifsc_code = validated_data.pop("ifsc_code","")
            account_number = validated_data.pop("account_number","")
            branch_name = validated_data.pop("branch_name","")            
            regime_type = validated_data.pop("Regime_type","")            
            
            approved_amount = validated_data.pop("approved_amount","")            
         
            validated_data["gender"] = validated_data["gender"].upper()
            
            compliance_data={'pf_num':validated_data.pop('pf_no', ""), 'uan_num':validated_data.pop('uan_no', ""), 'esi_num':validated_data.pop('emp_esi_no', ""), 'nominee_name':validated_data.pop('nominee_name', ""), 'nominee_rel':validated_data.pop('nominee_relationship', ""), 'nominee_dob':validated_data.pop('nominee_dob', None)}
            emp_obj = Employee.objects.create(**validated_data)
            compliance_data.update({"employee":emp_obj.id})
            emp_compliance_data = EmpComplianceSerializer(data=compliance_data)
            if emp_compliance_data.is_valid():
                compliance_obj = emp_compliance_data.save()
            else:
                raise serializers.ValidationError(emp_compliance_data.errors)
        
            emp_sal_det = EmployeeSalaryDetails.objects.create(employee=emp_obj)
            emp_sal_det.bank_name = bank_name
            emp_sal_det.ifsc_code = ifsc_code
            emp_sal_det.branch_name = branch_name
            emp_sal_det.account_number = account_number    
            # if bank_name:
            #     emp_sal_det.fund_transfer_type = 'FT' if 'ICICI' in bank_name.upper() else 'NEFT'

            if ctc:
                emp_sal_det.ctc=ctc
            emp_sal_det.save()                    

            regime_name = "new"
            regime_no = 20
            
            if regime_type == "old":
                regime_name = "old"
                regime_no = 10
            
            if regime_name == "new":
                approved_amount = 50000
            
            from_month_year = AttendanceRuleSettings.objects.get(company=validated_data.get("company"))
            month_payroll_start = from_month_year.attendance_paycycle_end_date.strftime('%m')        

            now = timezone.now()
            
            start_yr = now.year
            end_yr = now.year + 1
        
            if (int(month_payroll_start)-1) < 4:
                start_yr = now.year - 1 
                end_yr = now.year                    

            InvestmentDeclaration.objects.get_or_create(
                                                            employee=emp_obj,
                                                            final_approved_amount=approved_amount,
                                                            regime_type=regime_no,
                                                            start_year=start_yr,
                                                            end_year=end_yr
                                                        )            

            ewd_obj, created = EmployeeWorkDetails.objects.get_or_create(employee=emp_obj)
            ewd_obj.employee_status = "Active"
            if department:
                dep_obj, dep_created = Departments.objects.get_or_create(
                                                                        name=department,                                                                        
                                                                        company=validated_data.get("company")
                                                                        ) 
                ewd_obj.department = dep_obj
            if sub_department:
                sub_dep_obj, sub_dep_created = SubDepartments.objects.get_or_create(
                    name=sub_department, 
                    department =  dep_obj                                                                                          
                )              
                ewd_obj.sub_department = sub_dep_obj


            if designation:
                desig, desig_created = Designations.objects.get_or_create(
                                                                            name=designation,
                                                                            company=validated_data.get("company"),
                                                                            # sub_department=sub_dep_obj,
                                                                            # department=dep_obj,
                                                                            )                                  
                ewd_obj.designation = desig                                

            company_obj = CompanyDetails.objects.get(company_name=validated_data.get("company"))
            ewd_obj.employee_number = f"{slugify(company_obj.brand_name)}-{company_obj.employees.count()}"
            ewd_obj.save()

            if Emp_father_name:
                father_obj, created = RelationshipTypes.objects.get_or_create(relationship_type=10)
                EmployeeFamilyDetails.objects.create(employee = emp_obj, name=Emp_father_name,relationship=father_obj)
            
            if Emp_mother_name:
                mother_obj, created = RelationshipTypes.objects.get_or_create(relationship_type=20)
                EmployeeFamilyDetails.objects.create(employee = emp_obj, name=Emp_mother_name,relationship=mother_obj)
            
            if Emp_spouse_name:
                spouse_obj, created = RelationshipTypes.objects.get_or_create(relationship_type=40)
                EmployeeFamilyDetails.objects.create(employee = emp_obj, name=Emp_spouse_name,relationship=spouse_obj)
            
            if Pan_number:
                dep, _created = DocumentsTypes.objects.get_or_create(document_type = 10)
                
                # emp_doc, _created = EmployeeDocuments.objects.update_or_create(
                #     employee = emp_obj,
                #     document_type = dep,                
                # )
                emp_doc = EmployeeDocuments.objects.filter(employee = emp_obj).first()
                if not emp_doc:
                    emp_doc = EmployeeDocuments.objects.create(employee = emp_obj)
                emp_doc.document_type = dep
                emp_doc.document_number = Pan_number
                emp_doc.save()         
            
            if Aadhaar_Number:
                dep, _created = DocumentsTypes.objects.get_or_create(document_type = 20)
                # emp_doc, _created = EmployeeDocuments.objects.update_or_create(
                #     employee = emp_obj,
                #     document_type = dep,                
                # )
                emp_doc = EmployeeDocuments.objects.filter(employee = emp_obj).first()
                if not emp_doc:
                    emp_doc = EmployeeDocuments.objects.create(employee = emp_obj)
                emp_doc.document_type = dep
                emp_doc.document_number = Aadhaar_Number
                emp_doc.save()          
            
            if Emergency_contact_no:
                if emp_obj and emp_obj.employee_family_details.first() and emp_obj.employee_family_details.first().name:
                    contact_name = emp_obj.employee_family_details.first().name
                else:
                    contact_name =""

                if emp_obj and emp_obj.employee_family_details.first() and emp_obj.employee_family_details.first().relationship:
                    contact_relationship=emp_obj.employee_family_details.first().relationship
                else:
                    contact_relationship=None

                EmployeeEmergencyContact.objects.create(employee=emp_obj,name=contact_name, relationship=contact_relationship,phone_number=Emergency_contact_no)            
            transaction.commit()
            return emp_obj
        except Exception as e: 
            transaction.rollback(sid)           
            raise serializers.ValidationError({"ser_exception":str(e)})
    

class EmployeeBulkLopSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeMonthlyAttendanceRecords
        fields = ["employee","year","month","leaves_count","updated_hr_lop_count", "leaves_encash_count" ]
    
    def to_internal_value(self, data):
        return super().to_internal_value(data)

    def validate(self,attrs):
        employee = attrs.get('employee')   
        if attrs.get("updated_hr_lop_count") > attrs.get("leaves_count"):         
            raise serializers.ValidationError({"error_msg":
                f"LOP cannot be more than Leaves for {employee}"
            })
        return attrs

    @transaction.atomic
    def create(self,validated_data):
        print(validated_data)
        empl_obj, updated = EmployeeMonthlyAttendanceRecords.objects.update_or_create(
                                employee=validated_data.pop('employee'),
                                year = int(validated_data.pop('year')),
                                month = int(validated_data.pop('month'))-1,
                    )                          
        
        empl_obj.leaves_count = validated_data.pop('leaves_count')
        empl_obj.updated_hr_lop_count = validated_data.pop('updated_hr_lop_count')
        empl_obj.is_hr_updated = True
        empl_obj.leaves_encash_count = validated_data.pop('leaves_encash_count')
        empl_obj.save()        
        return {"success":"file updloaded"}



class TaxDetailsSerializer(serializers.ModelSerializer):
    on_company = serializers.PrimaryKeyRelatedField(queryset=CompanyDetails.objects.all())
    
    class Meta:
        model = TaxDetails
        fields ="__all__"
        


class DesignationSerializer(serializers.ModelSerializer):
    department_name = serializers.ReadOnlyField(source='department.name')
    department_id = serializers.ReadOnlyField(source='department.id')
    sub_department_id = serializers.ReadOnlyField(source='sub_department.id')
    sub_department_name = serializers.ReadOnlyField(source='sub_department.name')
    emp_count = serializers.CharField()
    class Meta:
        model = Designations
        fields = ['id','name','department_id','department_name','sub_department_id','sub_department_name','emp_count']


class EmployeesListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Employee
        fields=["id","name"]

# class EmployeeOTSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = EmployeeOT
#         fields = [
#             "id",
#             "employee",            
#             "ot_month_year",
#             "total_ot_count",
#             "created_from",
#             "updated_from",
#         ]
#     def validate(self, attrs):
#         employee = attrs.get('employee')
#         ot_month_year = attrs.get('ot_month_year')

#         # Checks if a record already exists with the same employee and lop_month_year
#         # if EmployeeOT.objects.filter(employee=employee, ot_month_year=ot_month_year).exists():
#         #     raise serializers.ValidationError({"error_msg":
#         #         f"An entry fo this {employee} and {ot_month_year} combination already exists."
#         #     })

#         return attrs
        
#     @transaction.atomic
#     def create(self,validated_data):        
#         empl_obj, updated = EmployeeOT.objects.update_or_create(employee=validated_data.pop('employee'),
#                                         ot_month_year=validated_data.pop('ot_month_year')
#                                         )
#         empl_obj.total_ot_count = validated_data.pop('total_ot_count')
#         # empl_obj.created_from = validated_data.pop('created_from')        
#         # empl_obj.updated_from = validated_data.pop('updated_from')
#         empl_obj.save()        
#         return {"success":"file updloaded"}
    

class EmployeeGratuitySerializer(serializers.ModelSerializer):
            
    class Meta:
        model = Employee
        fields = ["first_name", "middle_name", "last_name", "date_of_join"]    
    

    def custom_json_representation(self, obj):
        # Define a serializer method to create a custom JSON representation
        context = {
            'emp_id': obj.work_details.employee_number,
            'first_name': obj.first_name,
            'middle_name': obj.middle_name,
            'last_name': obj.last_name,
            'date_of_join': obj.date_of_join,            
        }

        # resignation_info.last_working_day
        try:
            emp_ctc= obj.salary_details.ctc if obj.salary_details.ctc >= 0 else 0
        except:
            emp_ctc = 0
            # return None
        
        gross_month=ctc_to_gross_per_year(emp_ctc)/12
        dearance_allowed_last_drawn = 0
        basic_amount = gross_month*(self.context.get("basic_amount_pct")/100)

        now=timezone_now()

        try:
            if obj.resignation_info:
                if obj.resignation_info.last_working_day:
                    context['last_working_day'] = obj.resignation_info.last_working_day            
                else:
                    context['last_working_day'] = obj.resignation_info.last_working_day            
            
            if now.month < 4:                   
                financial_year_start = now.year - 1                           
            else:                
                financial_year_start = now.year 

            resign_chk_data = datetime(financial_year_start, 4, 1).date()                        

            if context['last_working_day'] < resign_chk_data:                
                return None
            
            worked_duration = relativedelta(context['last_working_day'], obj.date_of_join)
            
        except:
            context['last_working_day'] = ""
            worked_duration = relativedelta(now.date(), obj.date_of_join)

        years_worked = worked_duration.years
        months_worked = worked_duration.months

        context["eligible_salary"] = round(basic_amount+dearance_allowed_last_drawn)
        context["years_worked"] = years_worked
        context["months_worked"] = months_worked
        
        if months_worked >= 6:
            years_worked+=years_worked+1
        half_months_salary = 15 #fixed
        days_in_month = 26 #fixed

        context['gratuity_amount'] = round(
            (((basic_amount+dearance_allowed_last_drawn)*years_worked*half_months_salary)/days_in_month)
            )

        return context

    def to_representation(self, instance):
        # Override the to_representation method to include the custom JSON data
        data = super().to_representation(instance)
        
        custom_data = self.custom_json_representation(instance)
        
        # Add the custom data to the serialized representation
      
        if custom_data:
            data.update(custom_data)
        
        return data


class EmployeeMissingInfoSerializer(serializers.ModelSerializer):
    missing_info = serializers.SerializerMethodField()
    employee_details = serializers.ReadOnlyField()
    class Meta:
        model  = Employee
        fields = ['employee_details', 'missing_info']
    
    def get_missing_info(self, obj):
        try:            
            missing_field = [None, '']
            field =   [field  for field,val in obj.__dict__.items() if val in missing_field]
            try:
                field_2 = [field for field,val in obj.salary_details.__dict__.items() if val in missing_field]
                field += field_2
            except:
                pass
            try:                
                field_2 = [field for field,val in obj.work_details.__dict__.items() if val in missing_field]
                field += field_2            
            except:
                pass
            if 'is_deleted' in field: field.remove('is_deleted')
            if 'pre_onboarding' in field: field.remove('pre_onboarding')            
            if 'updated_by_id' in field: field.remove('updated_by_id')
            if 'created_by_id' in field: field.remove('created_by_id')
            field = [i.replace('_id',"").replace("_"," ") for i in field]
            return set(field)
        except Exception as e:
            raise serializers.ValidationError({"ser_exception":str(e)})

class EmpTdsReportSerializerV2(serializers.ModelSerializer):
    monthly_tds = serializers.SerializerMethodField()
    # monthly_gross = serializers.SerializerMethodField()
    total_tds = serializers.SerializerMethodField()
    # total_gross = serializers.SerializerMethodField()
    all_payroll_objs = serializers.SerializerMethodField()

    dept_name = serializers.ReadOnlyField() 
    emp_name = serializers.ReadOnlyField()
    emp_number = serializers.ReadOnlyField()
    org_name = serializers.ReadOnlyField()
    pan = serializers.ReadOnlyField()
    year = serializers.ReadOnlyField()

    monthly_net_salary = serializers.SerializerMethodField()
    total_net_salary = serializers.SerializerMethodField()
    regime_type = serializers.SerializerMethodField()
    approved_amount = serializers.ReadOnlyField()
    idc_objs = serializers.SerializerMethodField()
    total_taxable_salary = serializers.SerializerMethodField()
    financial_year = serializers.ReadOnlyField()

    class Meta:
        model = Employee
        fields = [
            'all_payroll_objs', #keep this in top as it's referencing to montly_tds, monthly_gross, ..
            'id', 'dept_name', 'emp_name', 'emp_number', 'org_name', 'pan', 'year', 'idc_objs', 'monthly_tds',
            #   'monthly_gross', 'total_gross',
                'total_tds','monthly_net_salary', 'total_net_salary', 'regime_type', 'approved_amount', 'total_taxable_salary', 'financial_year']
    def get_all_payroll_objs(self, obj):
        # self.payroll_objs = PayrollInformation.objects.filter(employee = obj.id, month_year__year__gte = self.context['start_year'], month_year__year__lte = self.context['end_year'], is_processed=True)
        start_date = date(int(self.context['start_year']), 4, 1)
        end_date = date(int(self.context['end_year']), 3, 1)
        self.payroll_objs = obj.emp_payroll_info.filter(month_year__range=(start_date, end_date))
        
        self.inv_obj = obj.investmentdeclaration_set.filter(start_year=self.context['start_year'], end_year=self.context['end_year'])
        self.inv_previous_income = self.inv_previous_tds = 0
        if self.inv_obj.exists():
            self.inv_previous_income = self.inv_obj.first().income_from_previous_employer
            self.inv_previous_tds = self.inv_obj.first().tds_from_previous_employer
        return ""
    

    def get_idc_objs(self, obj):
        # idc_objs = {"f1": 0, "f2": 0, "f3": 0, "f4": 0, "f5": 0, "f6": 0, "f7": 0, "tdsFromPreviousEmployer": obj.salary_details.previous_tds, "incomeFromPreviousEmployer": obj.salary_details.previous_income}
        idc_objs = {"f1": 0, "f2": 0, "f3": 0, "f4": 0, "f5": 0, "f6": 0, "f7": 0, "tdsFromPreviousEmployer": self.inv_previous_tds, "incomeFromPreviousEmployer": self.inv_previous_income}
        investment_obj = obj.investmentdeclaration_set.filter(start_year=self.context['start_year'], end_year=self.context['end_year'])
        if not investment_obj.exists():
            return [idc_objs]
        f1 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'Standard declaration of 50000 under section 16')
        if f1.exists():
            idc_objs.update({"f1":f1.aggregate(Sum('approved_amount'))['approved_amount__sum']})
        f2 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'Deduction under section 80C')
        if f2.exists():
            idc_objs.update({"f2":f2.aggregate(Sum('approved_amount'))['approved_amount__sum']})
        f3 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'Deduction for medical premium under section 80D')
        if f3.exists():
            idc_objs.update({"f3":f3.aggregate(Sum('approved_amount'))['approved_amount__sum']})
        f4 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'Interest payable on Housing Loan max (2 Lakh)')
        if f4.exists():
            idc_objs.update({"f4":f4.aggregate(Sum('approved_amount'))['approved_amount__sum']})
        f5 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'HRA Allowances Exempt under Section 10(5), 10(13A), 10(14), 10(17)')
        if f5.exists():
            idc_objs.update({"f5":f5.aggregate(Sum('approved_amount'))['approved_amount__sum']})
        f6 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'LTA')
        if f6.exists():
            idc_objs.update({"f6":f6.aggregate(Sum('approved_amount'))['approved_amount__sum']})
        f7 = investment_obj.first().declaration_forms.filter(parentform_type__formtype = 'Any Other')
        if f7.exists():
            idc_objs.update({"f7":f7.aggregate(Sum('approved_amount'))['approved_amount__sum']})

        return [idc_objs]
    
    def get_monthly_tds(self, obj):
        tds_monthly = self.payroll_objs.values_list('month_year', 'monthly_tds')       
        tds_monthly = {str(item[0].strftime('%B'))+"-TDS": round(float(item[1]),2) if item[1] else 0 for item in tds_monthly}
        return tds_monthly
    
    # def get_monthly_gross(self, obj):
    #     gross_monthly = self.payroll_objs.values_list('month_year', 'earned_gross')
    #     gross_monthly = {str(item[0].strftime('%B'))+"-Gross": round(float(item[1]),2) if item[1] else 0 for item in gross_monthly}
    #     return gross_monthly
    
    def get_total_tds(self, obj):
        current_tds = round(float(self.payroll_objs.aggregate(Sum("monthly_tds"))['monthly_tds__sum']),2) if self.payroll_objs.aggregate(Sum("monthly_tds"))['monthly_tds__sum'] else 0
        prev_tds = self.inv_previous_tds
        total_tds = current_tds + float(prev_tds)
        return total_tds
    
    # def get_total_gross(self, obj):
    #     total_gross = round(float(self.payroll_objs.aggregate(Sum("earned_gross"))['earned_gross__sum']),2)  if self.payroll_objs.aggregate(Sum("earned_gross"))['earned_gross__sum'] else 0
    #     return total_gross

    def get_monthly_net_salary(self, obj):
        net_salary_monthly = self.payroll_objs.values_list('month_year', 'net_salary')
        net_salary_monthly = {str(item[0].strftime('%B'))+"-NetSalary": round(float(item[1]),2) if item[1] else 0 for item in net_salary_monthly}
        return  net_salary_monthly
    
    def get_total_net_salary(self, obj):
        self.total_net_salary = round(float(self.payroll_objs.aggregate(Sum("net_salary"))['net_salary__sum']),2)  if self.payroll_objs.aggregate(Sum("net_salary"))['net_salary__sum'] else 0
        
        self.total_income_total_net_salary = self.total_net_salary + float(self.inv_previous_income)
        return self.total_income_total_net_salary
    

    def get_total_taxable_salary(self, obj):
        return self.total_income_total_net_salary - eval(str(obj.approved_amount))

    def get_regime_type(self, obj):
        regime_type_lst = []
        old_inv_obj = obj.investmentdeclaration_set.filter(start_year__gte=self.context['start_year'], end_year__lte=self.context['end_year'], regime_type=InvestmentDeclaration.OLD_TAX_REGIME)
        new_inv_obj = obj.investmentdeclaration_set.filter(start_year__gte=self.context['start_year'], end_year__lte=self.context['end_year'], regime_type=InvestmentDeclaration.NEW_TAX_REGIME)
        if old_inv_obj.exists():
            regime_type_lst.append("Old")
        if new_inv_obj.exists():
            regime_type_lst.append("New")
        if len(regime_type_lst) == 0:
            regime_type_lst.append("NA")
        return regime_type_lst

class MissingEmployeeInfoSerializer(serializers.ModelSerializer):
    emp_id = serializers.SerializerMethodField()
    missing_info = serializers.SerializerMethodField()
    class Meta:
        model = Employee
        fields = ['first_name', 'middle_name', 'last_name', 'emp_id', 'missing_info']

    def get_emp_id(self, obj):
        if hasattr(obj, 'work_details') and hasattr(obj.work_details, 'employee_number'):
            return obj.work_details.employee_number
        else:
            return ""

    # def get_salary_details(self, obj):
    #     emp_salary_data = obj.salary_details.__dict__.items()
    #     keys_to_delete = {'id'}

    #     new_dict = {key: value for key, value in emp_salary_data if key not in keys_to_delete}
        
    #     # del new_dict['_state'] #need to remove the fields which are not required in the model

    #     missing_fields = [field for field,val in new_dict.items() if val in MissingEmployeeInfoSerializer.missing_field]
    #     return missing_fields

    # def get_lop(self, obj):
    #     try:
    #         leaves_month_year = get_month_year_for_payroll_to_run_by_company(obj.company.id)  

    #         # leaves_month_year = leaves_month_year - relativedelta(1)

    #         emar_obj = EmployeeMonthlyAttendanceRecords.objects.filter(
    #             employee_id=obj.id,
    #             year = int(leaves_month_year.strftime('%Y')),
    #             month = int(leaves_month_year.strftime('%m')),
    #             is_hr_updated=True
    #         )
    #         if emar_obj.exists(): 
    #             return ""
            
    #         # elif not emar_obj.exists():
    #         #     emplop_inst = EmployeeLops.objects.filter(employee=obj.id,lop_month_year=leaves_month_year.strftime('%Y-%m-01'), is_final = True)
    #         #     if not emplop_inst.exists(): return "lop not present"
    #         #     else: return ""
    #         else:
    #             return "some thing other came"
    #     except Exception as e: 
    #         raise serializers.ValidationError(str(e))
    def get_missing_info(self, obj):
        missing_context = []
        if not obj.date_of_join:
            missing_context.append('Date of Join')
        #department
        if not hasattr(obj, 'work_details') or not hasattr(obj.work_details, 'department') or not hasattr(obj.work_details.department, 'name'):
            missing_context.append("Department")
        if not hasattr(obj, 'work_details') or not hasattr(obj.work_details, 'designation') or not hasattr(obj.work_details.designation, 'name'):
            missing_context.append("Designation")
        #gender
        if not obj.gender:
            missing_context.append("Gender")
        #bank_details
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'account_holder_name'):
            missing_context.append("Account Holder Name")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'bank_name'):
            missing_context.append("Bank Name")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'account_number'):
           missing_context.append("Account Number")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'account_type'):
            missing_context.append("Account Type")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'ifsc_code'):
            missing_context.append("IFSC Code")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'branch_name'):
            missing_context.append("Branch Name")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'city'):
            missing_context.append("City")
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'fund_transfer_type'):
            missing_context.append("Fund Transfer Type")
        #salary details
        if not hasattr(obj, 'salary_details') or not hasattr(obj.salary_details, 'ctc'):
            missing_context.append("CTC")

        #lop # no need directly we can check in active employees page.
        # print(get_payroll_month_employee(obj, is_emp_obj=True))

        return missing_context
class EmployeeMonthlyAttendanceRecordsSerializer(serializers.ModelSerializer):
    employee = serializers.SlugRelatedField(
        slug_field='official_email', 
        queryset = Employee.objects.all(),
    )
    class Meta:
        model = EmployeeMonthlyAttendanceRecords
        fields = "__all__"
    
    def create(self, validated_data):
        employee = validated_data.pop('employee')
        date = datetime(validated_data.pop('year'), validated_data.pop('month'), 1).date() - relativedelta(months=1)

        validated_data['is_hr_updated'] = True    

        emp_obj, updated = EmployeeMonthlyAttendanceRecords.objects.update_or_create(
        employee = employee, year = date.year, month=date.month, defaults=validated_data)

        return emp_obj
    

class PayslipFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipFields
        fields = "__all__"

class PayslipTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PayslipTemplates
        fields = "__all__"

class PayslipTemplateFieldsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipTemplateFields
        fields = "__all__"
        depth = 1

    def validate(self, attrs):
        if attrs.get('is_selected'):
            payslip_template_field_id = self.initial_data.get('id')
            obj = PayslipTemplateFields.objects.exclude(id=payslip_template_field_id).filter(is_selected=True)
            if obj.exists():
                raise serializers.ValidationError(f"Already selected the {obj.first().name}")
        return attrs


    def create(self, validated_data):
        try:
            company_id = self.initial_data.get('company')
            templates_id = self.initial_data.get('templates')
            company_id = CompanyDetails.objects.get(id=company_id)
            templates_id = PayslipTemplates.objects.get(id=templates_id)
            validated_data['company'] = company_id
            validated_data['templates'] = templates_id
            return super().create(validated_data)
        except Exception as e:
            raise serializers.ValidationError(str(e))
    def update(self, instance, validated_data):
        try:
            self.initial_data.pop('id')
            company_id = self.initial_data.get('company')
            templates_id = self.initial_data.get('templates')
            if company_id:
                self.initial_data['company'] = CompanyDetails.objects.get(id=company_id)
            if templates_id:
                self.initial_data['templates'] = PayslipTemplates.objects.get(id=templates_id)
            for key, value in self.initial_data.items():  # Assuming new_data is the updated dictionary
                setattr(instance, key, value)  
            instance.save()
            return instance
        except Exception as e:
            raise serializers.ValidationError(str(e))
class EPFEmployeesSerializer(serializers.ModelSerializer):
    class Meta:
        model = EPFEmployees
        fields = '__all__'
        # depth = 1


class IciciBankReportSerializer(serializers.ModelSerializer):
    report_values = serializers.JSONField()
    class Meta:
        model = PayrollInformation
        fields = ['report_values']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        last_month = instance.month_year.strftime("%b%Y").upper()
        company_name = instance.employee.company.domain_name + " Salary "
        representation['report_values']['Credit_Narration'] = company_name + str(last_month)
        representation['report_values']['Date'] = instance.month_year + relativedelta(months=1)
        return representation

class EsiResignationSerializer(serializers.ModelSerializer):

    class Meta:
        model = EsiResignationDetails
        fields = '__all__'