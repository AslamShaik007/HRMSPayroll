from django.db import models

from django.contrib.auth import get_user_model

User = get_user_model()

class PlanDetail(models.Model):
    class PlanType(models.TextChoices):
        HRMS = 'hrms','HRMS'  # hrms + payroll
        PAYROLL = 'payroll', 'PAYROLL'  # payroll
        INTEGRATED = 'integrated', 'INTEGRATED',  # hrms
    
    plan_type = models.CharField(max_length=28, choices=PlanType.choices)
    price = models.FloatField(default=0, null=True, blank=True)
    num_of_employees = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

    def __str__(self):
        return self.plan_type


class Billing(models.Model):
    class PaymentStatus(models.TextChoices):
        PAID = 'paid', 'Paid'
        PENDING = 'pending', 'Pending'
        DECLINED = 'declined', 'Declined'

    # class PaymentType(models.TextChoices):
    #     MONTHLY = 'monthly', 'Monthly'
    #     REFILL = 'refill', 'Refill'
    
    payment_status = models.CharField(max_length=20, choices = PaymentStatus.choices, default = PaymentStatus.PENDING)
    # payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
    paid_date = models.DateField(null=True, blank=True)
    payment_updated_by = models.JSONField(default=dict, null=True, blank=True) 
    payment_done_by = models.ForeignKey(User, on_delete=models.DO_NOTHING, null=True, blank=True)
    amount = models.FloatField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)


class TransactionDetails(models.Model):
    transaction_id = models.CharField(max_length=256)
    plan_details = models.CharField(max_length=256, null=True, blank=True)
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE)
    bankname = models.ForeignKey("TransactionBankDetails", on_delete=models.CASCADE)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)

class TransactionBankDetails(models.Model):
    class PaymentType(models.TextChoices):
        # UPI = "upi", "Upi"
        DEBITCARD = "debitcard", "DebitCard"
        # CREDITCARD = "creditcard", "CreditCard"
        # OFFLINE = "offline", "Offline"
        
    bank_name = models.CharField(max_length=256)
    card_num = models.CharField(max_length=256)
    ifsc = models.CharField(max_length=256)
    payment_type = models.CharField(max_length=20, choices = PaymentType.choices)
    billing_address = models.CharField(max_length=256, default="")
    address_line1 = models.CharField(max_length=256, default="")
    address_line2 = models.CharField(max_length=256, default="")
    state = models.CharField(max_length=256, default="")
    country = models.CharField(max_length=256, default="")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateField(auto_now=True)
