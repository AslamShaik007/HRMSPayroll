from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import AbstractModel
from directory.models import Employee
from HRMSApp.models import CompanyDetails
from django.db.models import UniqueConstraint, CheckConstraint, Q
import decimal


class ReminderDates(AbstractModel):
    company = models.OneToOneField(
        CompanyDetails, related_name=_("payroll_reminder_date"), on_delete=models.CASCADE
    )
    esi_compliance_date = models.DateField(blank=True,null=True)

    def __str__(self):
        return str(self.company.id)    

class EpfSetup(AbstractModel):  # php    
    company = models.OneToOneField(
        CompanyDetails, related_name=_("epf_comp"), on_delete=models.CASCADE
    )
    epf_number = models.CharField(max_length=100, null=True, blank=True)
    employer_contribution = models.IntegerField(default=12)
    employee_contribution = models.IntegerField(default=12)    
    is_employer_contribution_in_ctc = models.BooleanField(default=True)    
    # tracker = FieldTracker()

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=['company', 'epf_number'], name="epf_table_index")]


class Esi(AbstractModel):  # php    
    company = models.OneToOneField(
        CompanyDetails, related_name=_("esi_comp"), on_delete=models.CASCADE
    )
    esi_no = models.CharField(max_length=100, null=True, blank=True)
    employee_contribution_pct = models.FloatField()
    employer_contribution_pct = models.FloatField()
    is_employer_contribution_in_ctc = models.BooleanField(default=True)        

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=['company', 'esi_no'], name="esi_table_index")]

class StatesTaxConfig(AbstractModel):
    state_choices = (("Andhra Pradesh","Andhra Pradesh"),
                     ("Arunachal Pradesh","Arunachal Pradesh"),
                     ("Assam","Assam"),
                     ("Bihar","Bihar"),
                     ("Chhattisgarh","Chhattisgarh"),
                     ("Goa","Goa"),
                     ("Gujarat","Gujarat"),
                     ("Haryana","Haryana"),
                     ("Himachal Pradesh","Himachal Pradesh"),
                     ("Jammu and Kashmir ","Jammu and Kashmir "),
                     ("Jharkhand","Jharkhand"),
                     ("Karnataka","Karnataka"),
                     ("Kerala","Kerala"),
                     ("Madhya Pradesh","Madhya Pradesh"),
                     ("Maharashtra","Maharashtra"),
                     ("Manipur","Manipur"),
                     ("Meghalaya","Meghalaya"),
                     ("Mizoram","Mizoram"),
                     ("Nagaland","Nagaland"),                     
                     ("Odisha","Odisha"),
                     ("Punjab","Punjab"),
                     ("Rajasthan","Rajasthan"),
                     ("Sikkim","Sikkim"),
                     ("Tamil Nadu","Tamil Nadu"),
                     ("Telangana","Telangana"),
                     ("Tripura","Tripura"),
                     ("Uttar Pradesh","Uttar Pradesh"),
                     ("Uttarakhand","Uttarakhand"),
                     ("West Bengal","West Bengal"),                     
                     ("Andaman and Nicobar Islands","Andaman and Nicobar Islands"),
                     ("Chandigarh","Chandigarh"),
                     ("Dadra and Nagar Haveli","Dadra and Nagar Haveli"),
                     ("Daman and Diu","Daman and Diu"),
                     ("Lakshadweep","Lakshadweep"),
                     ("NCT of Delhi","NCT of Delhi"),
                     ("Puducherry","Puducherry"))
    state = models.CharField(choices=state_choices,max_length=255, null=True, blank=True, db_index = True) 
    tax_config = models.JSONField(
        default=dict, blank=True, verbose_name="Professional tax config"
    )       
    
    def __str__(self):
            return str(self.state)
    
    class Meta:
        ordering = ("created_at",)

class ProfessionTax(AbstractModel):  # own
    state = models.ForeignKey(StatesTaxConfig, on_delete=models.CASCADE,null=True,blank=True)
    company = models.OneToOneField(
        CompanyDetails, related_name=_("pt_comp"), on_delete=models.CASCADE
    )    
    is_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=['company', 'state'], name="pt_table_index")]        


class PaySalaryComponents(AbstractModel):  # php
    """
    this class is used to store the company salary components
    """

    earning_choices = (
        ("Select Earning Type", "Select Earning Type"),
        ("Earning", "Earning"),
        ("Employee Deduction", "Employee Deduction"),
        ("Employer Deduction", "Employer Deduction"),
    )
    calculation_choices = ((0, ""), (1, "flat_amount"), (2, "pct_amount"))
    company = models.ForeignKey(
        CompanyDetails, related_name=_("pay_salary_comp"), on_delete=models.CASCADE, db_index=True
    )
    earning_type = models.CharField(
        max_length=50, choices=earning_choices, default="Select Earning Type", db_index = True
    )
    component_name = models.CharField(max_length=50, db_index=True)
    name_on_payslip = models.CharField(max_length=50)
    calculation_type = models.IntegerField(choices=calculation_choices, default=2)
    flat_amount = models.IntegerField(null=True, blank=True)
    pct_of_basic = models.FloatField(null=True, blank=True)  # it's percentage
    threshold_base_amount = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_part_of_salary_structure = models.BooleanField(default=False)
    is_taxable = models.BooleanField(default=False)
    is_prorated = models.BooleanField(default=False)
    is_part_of_flexible_plan = models.BooleanField(default=False)
    is_part_of_epf = models.BooleanField(default=False)
    is_part_of_esi = models.BooleanField(default=False)
    is_visible_on_payslip = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)

    # def clean(self):
    # def validate(self):
    # def save(self):
    #     if self.calculation_type == 0:
    #         self.pct_of_basic = 0
    #         self.flat_amount = 0
    #     elif self.calculation_type == 1:
    #         self.pct_of_basic = 0
    #         self.threshold_base_amount = 0
    #     else:  # which comes if selected as pct_amount
    #         self.threshold_base_amount = 0
    #         self.flat_amount = 0
    #     super(PaySalaryComponents, self).save(*args, **kwargs)

    class Meta:
        ordering = ("created_at",)



class EmployeeComplianceNumbers(AbstractModel):  # own
    INSURENCE_CHOICES = (
        ("YES","YES"),
        ("NO","NO"),
        ("ESI","ESI"),
        ("NEED_TO_CHECK","NEED_TO_CHECK"),

    )
    employee = models.OneToOneField(
        Employee,
        # related_name="emp_salary_details",
        related_name="emp_compliance_detail",
        on_delete=models.CASCADE,
    )
    # pan_num = models.CharField(max_length=50, unique=True, null=True, blank=True) 
    # aadhar_num = models.CharField(max_length=50, unique=True, null=True, blank=True) 
    pf_num = models.CharField(max_length=50, null=True, blank=True)
    uan_num = models.CharField(max_length=50, null=True, blank=True)
    esi_num = models.CharField(max_length=50, null=True, blank=True)
    nominee_name = models.CharField(max_length=50, null=True, blank=True)
    nominee_rel = models.CharField(max_length=50, null=True, blank=True)
    nominee_dob = models.DateField(
        verbose_name="nominee date of birth",
        null=True,
        blank=True,
    )
    health_insurence = models.CharField(max_length=16, choices=INSURENCE_CHOICES,null=True, blank=True)
    insurence_date = models.DateField(verbose_name="insurence Date", null=True, blank=True)
    insurence_file = models.FileField(upload_to="employee_documents/", null=True, blank=True)
    # tracker = FieldTracker()

    def __str__(self):
        return (
            str(self.id)
        )
    class Meta:
        indexes = [
            models.Index(fields=["employee", "pf_num", "uan_num", "esi_num", "nominee_name", "nominee_rel", "nominee_dob"], name="emp_compliance_table_index")
        ]
        
    def save(self, *args, **kwargs):        
        if self.insurence_file and 'https://bharatpayroll.s3.amazonaws.com/' not in self.insurence_file.url:
            file_key = f"{self.insurence_file.field.upload_to}{self.insurence_file.name}"
            s3_url = "https://bharatpayroll.s3.amazonaws.com/media/public/"+file_key
            self.insurence_file = s3_url   
                
        return super().save(*args, **kwargs)

class HealthEducationCess(AbstractModel):  # own
    health_education_name = models.CharField(max_length=50, db_index =True)
    health_education_cess = models.CharField(max_length=20)
    health_education_month_year = models.DateField()

    class Meta:
        ordering = (
            "health_education_month_year",
        )  # don't change ordering depended on signals

    def __str__(self):
        return (
            self.health_education_name
            + self.health_education_cess
            + str(self.health_education_month_year)
        )


class Regime(AbstractModel):  # own
    """
    this model is used to store the data of regime the range_tax is stored,
      in dict as {1000000: 0.30, 500000: 0.20, 250000: 0.05}
    """

    regime_name = models.CharField(max_length=50, db_index=True, unique=True)
    regime_month_year = models.DateField()
    salary_range_tax = models.JSONField(
        default=dict, blank=True, verbose_name="salary range tax"
    )

    def __str__(self):
        return self.regime_name + str(self.regime_month_year)

    class Meta:
        ordering = ("regime_month_year",)  # don't change ordering depended on signals


class PayrollLeaves(AbstractModel):
    class LeaveTypes(models.TextChoices):
        SICK_LEAVE = 'sick_leave', 'sick_leave'
        CASUAL_LEAVE = 'casual_leave', 'casual_leave'
        PRIVILEGE_LEAVE = 'privilege_leave', 'privilege_leave'

    leave_type = models.CharField(max_length=28, choices=LeaveTypes.choices, null=True, blank=True)
    outstanding_balance = models.DecimalField(default=0, max_digits=4, decimal_places=2)
    leaves_added = models.DecimalField(default=0, max_digits=4, decimal_places=2)
    leaves_availed = models.DecimalField(default=0, max_digits=4, decimal_places=2)
    current_balance = models.DecimalField(default=0, max_digits=4, decimal_places=2)

class PayrollInformation(AbstractModel):
    payroll_leaves = models.OneToOneField(PayrollLeaves, null=True, blank=True, on_delete=models.CASCADE)
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="emp_payroll_info"
    )
    month_year = models.DateField()

    month_days = models.PositiveIntegerField(default=0)
    working_days = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    paid_days = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    leaves = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    lop = models.DecimalField(max_digits=50, decimal_places=1, blank=True, null=True)
    days_present = models.DecimalField(max_digits=50, default=0, decimal_places=1, blank=True, null=True)
    holidays = models.DecimalField(max_digits=50, default=0, decimal_places=1, blank=True, null=True)
    weekly_offs = models.DecimalField(max_digits=50, default=0, decimal_places=1, blank=True, null=True)
    
    special_deductions = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    monthly_incentive = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    
    a_basic = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    a_others = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    arrears = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)

    overtime_pay = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    overtime_days = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    leaves_to_encash = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    leaves_encash_taxable_amount = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    leaves_encash_exemption_amount = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)

    salary_before_tds = models.DecimalField(max_digits=70, decimal_places=2, blank=True, null=True)
    
    designation = models.CharField(max_length=255,null=True,blank=True)
    department = models.CharField(max_length=255,null=True,blank=True)
    sub_department = models.CharField(max_length=255,null=True,blank=True)

    mode_of_payment = models.CharField(max_length=100,  null=True, blank=True, default = 'Bank Transfer') 
    bank_name = models.CharField(max_length=255,null=True,blank=True)
    account_number = models.CharField(max_length=255,null=True,blank=True)
    
    fixed_salary = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    variable_pay = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)

    monthly_ctc = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    yearly_ctc = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    earned_gross = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    e_basic = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    e_hra = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    e_conv = models.DecimalField(max_digits=60, decimal_places=2, blank=True, null=True)
    e_special_allow = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)

    s_basic = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    s_hra = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    s_conv = models.DecimalField(max_digits=60, decimal_places=2, blank=True, null=True)
    s_special_allow = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    s_gross = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    payable_gross = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)

    monthly_tds = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    tds_left = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    lop_deduction = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    other_deduction = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)    
   
    net_salary = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    t_basic = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    profession_tax = models.PositiveIntegerField(default=0)
    is_tds_fifty_percent = models.BooleanField(default=False)

    is_tds_percent_deducted = models.BooleanField(default=False)
    consider_tds_percent = models.PositiveIntegerField(default=0)

    pf_basic = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    employee_pf = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    employer_pf = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    employee_esi = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    employer_esi = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    edli_contribution = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    eps_contribution = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    total_epf_contribution = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    total_esi_contribution = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)

    total_employer_contribution = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    total_employee_contribution = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    
    staff_loan_deduction = models.DecimalField(max_digits=120,default=0, decimal_places=2, null=True, blank=True)
    advance_deduction = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)
    total_deduction = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)

    reimbursed_amount = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)

    net_pay = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)    
    total_earnings = models.DecimalField(max_digits=120, decimal_places=2, blank=True, null=True)    
    
    compensation_for_esi = models.DecimalField(max_digits=120, default=0, decimal_places=2, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)
    is_on_hold = models.BooleanField(default=False)
    other_additions = models.DecimalField(max_digits=120, default=0, decimal_places=2, null=True, blank=True)
    current_month_ctc = models.DecimalField(max_digits=120, default=0, decimal_places=2, null=True, blank=True)
     
    def __str__(self):
        return str(self.employee.id)+"--"+str(self.month_year)
    class Meta:
        ordering = ["-month_year",] #don't change ordering here
        constraints = [
            UniqueConstraint(fields=['employee', 'month_year'],name='unique_employee_payroll'),#validation as always an employee and lop_must_year must be unique
            # CheckConstraint(check=models.Q(salary_before_tds__gte=decimal.Decimal('0')), name='salary_before_tds_constraint'),
            # CheckConstraint(check=models.Q(monthly_tds__gte=decimal.Decimal('0')), name='monthly_tds_constraint'), # commenting presently
            # CheckConstraint(check=models.Q(tds_left__gte=decimal.Decimal('0')), name='tds_left_constraint'),
                        ]
        indexes = [
            models.Index(fields=["employee", "month_year", "is_processed"], name="payroll_info_table_index"),
        ]


class TaxDetails(AbstractModel):
    pan_number = models.CharField(max_length=50, blank=True, null=True)
    tan_number = models.CharField(max_length=50, blank=True, null=True)
    tds_circle_code = models.CharField(max_length=50, blank=True, null=True)    
    on_company = models.OneToOneField(CompanyDetails,on_delete=models.SET_NULL,null=True,blank=True)

    def __str__(self) -> str:
        return str(self.on_company)


class Reimbursement(AbstractModel):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="emp_reimbursement"
    )
    reimbursement_choices = (("Travel","Travel"),
                     ("Hotel_Accomodation","Hotel_Accomodation"),
                     ("Food","Food"),
                     ("Medical","Medical"),
                     ("Telephone","Telephone"),
                     ("Fuel","Fuel"),
                     ("Imprest","Imprest"),
                     ("Other","Other"))    
    type = models.CharField(choices=reimbursement_choices,max_length=255, null=True, blank=True)
    other_type = models.CharField(max_length=50, null=True, blank=True) 
    expense_date = models.DateField()    
    approval_date = models.DateField(null=True,blank=True)
    detail = models.CharField(max_length=255, null=True, blank=True) 
    employer_comment = models.CharField(max_length=255, null=True, blank=True) 
    support_file = models.FileField(
        upload_to="employee/reimburesement/",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(default=0,max_digits=8,decimal_places=2)
    approved_amount = models.DecimalField(default=0,max_digits=8,decimal_places=2)
    status_choices = (
                        ("Approved_Paid","Approved_Paid"),
                        ("Approved","Approved"),
                        ("Pending","Pending"),
                        ("Rejected","Rejected"))    
    status = models.CharField(choices=status_choices,max_length=255, null=True, blank=True) 

    def __str__(self) -> str:
            return str(self.employee.id)


class PayslipFields(AbstractModel):
    """
    this table stores all the payroll fields in the company
    """
    name = models.CharField(max_length=150)
    fields_list = models.JSONField(null=True, blank=True, default=dict) #
    company = models.OneToOneField(
        CompanyDetails, related_name="payslip_fields", on_delete=models.CASCADE)
 
    def _str_(self) -> str:
        return str(self.name)
    class Meta:
        indexes = [
            models.Index(fields=["name", "fields_list", "company"], name="payslip_fields_table_index")
        ]

class PayslipTemplates(AbstractModel):
    """
    this table stores all the payslip templates in the company
    """
    name = models.CharField(max_length=150)
    path = models.TextField(null=True, blank=True)
    company = models.ForeignKey(
        CompanyDetails, related_name="payslip_templates", on_delete=models.CASCADE)
   
    def _str_(self) -> str:
        return str(self.name)
    class Meta:
        indexes = [
            models.Index(fields=["name", "path", "company"], name="payslip_templates_table_index")
        ]

class PayslipTemplateFields(AbstractModel):
    """
    this table links templates and fields which uses in payslip. 
    """
    name = models.CharField(max_length=150)
    templates = models.ForeignKey(
        PayslipTemplates, related_name='templates', on_delete=models.CASCADE)
    fields = models.JSONField()
    company = models.ForeignKey(
        CompanyDetails, related_name="payslip_fields_templates", on_delete=models.CASCADE)
    is_selected = models.BooleanField(default=False)
 
    def _str_(self) -> str:
        return str(self.name)
    # Add Validation only one must be is_selected one for one company.
    class Meta:
        indexes = [
            models.Index(fields=["name", "templates", "fields", "company", "is_selected"], name="templates_fields_table_index")
        ]
        constraints = [
        UniqueConstraint(fields=['is_selected'], condition=Q(is_selected=True), name='template_fields_unique_is_selected')
         ]
class EPFEmployees(AbstractModel):
    """
    this table is used to store the emps for customized epf report
    """
    company = models.OneToOneField(CompanyDetails, related_name = "company_epf", on_delete=models.CASCADE)
    emps = models.ManyToManyField(Employee, related_name='epf_emps')
        
class EmployeePayrollOnHold(AbstractModel):
    """
    this class is used to store the employees who are on hold
    """
    # hold_status = (
    #     ("on_hold","on_hold"),
    #     ("on_release", "on_release")
    #             )    
    # status = models.CharField(choices=hold_status, max_length=255)
    #hold_from = models.Datefield()
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name = 'hold_employee')
    hold_created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name = 'created_hold_emp')
    hold_created_at = models.DateTimeField()
    hold_updated_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name = 'updated_hold_emp')
    hold_updated_at = models.DateTimeField()

class EsiResignationDetails(AbstractModel):
    """
    this class is used to get the esi resignation for resignation 
    """
    esi_resignation_statuses = (
        ('Left Service 2', '2'),
        ('Retired 3', '3'),
        ('Out of Coverage 4', '4'),
        ('Expired 5', '5'),
        ('Non Implemented area 6', '6'),
        ('Compliance by Immediate Employer 7', '7'),
        ('Suspension of work 8', '8'),
        ('Strike/Lockout 9', '9'),
        ('Retrenchment 10', '10'),
        ('No Work 11', '11'),
        ('Doesnt Belong To This Employer 12', '12'),
        ('Duplicate IP 13', '13'),
        )
    esi_resignation_status = models.CharField(choices = esi_resignation_statuses, max_length=255, null=True, blank=True)
    employee = models.OneToOneField(
        Employee,
        related_name="emp_esi_resignation",
        on_delete=models.CASCADE,
    )
