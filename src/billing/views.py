import django
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model, authenticate, logout, login
from django.shortcuts import redirect
from django.db.models import Q, Value, F, CharField, Case, When, Value
from django.db.models.functions import Concat
from django.http import HttpResponse, JsonResponse
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.text import slugify
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework import status, permissions, authentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer
from .models import Billing, TransactionBankDetails, TransactionDetails, PlanDetail


class BillingAPIView(APIView):
    permission_classes = []
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    
    
    def get(self, request):
        transaction_qs = TransactionDetails.objects.filter().select_related('billing').annotate(
            plan_name=Case(
                When(plan_details='premium', then=Value('Premium')),
                When(plan_details='enterprise', then=Value('Enterprise')),
                When(plan_details='basic', then=Value('Basic')),
                default=Value(''),
                output_field=CharField()
            )
        ).values(
            'id', 'transaction_id', 'plan_name', 'billing__payment_status',
            'billing__payment_done_by__username', 'billing__amount',
            'billing__payment_updated_by'
        )
        return Response(
            {
                "request": request,
                "data": transaction_qs
            },
            template_name='billing/billings_view.html'
        )

    
    def post(self, request):
        data = request.data
        [
            PlanDetail.objects.get_or_create(
                plan_type=plan.name,
                price=25000 if plan.name == 'basic' else 50000 if plan.name == 'enterprise' else 100000,
                num_of_employees=2500 if plan.name == 'basic' else 5000 if plan.name == 'enterprise' else 10000
            ) for plan in PlanDetail.PlanType
        ]
        billing_obj = Billing.objects.create(
            amount=data.get('amount', 1000),
            payment_status=data['payment_status'],
            payment_done_by=get_user_model().objects.first()
        )
        transaction_bank_details_qs = TransactionBankDetails.objects.filter(
            bank_name=data['bank_name'], card_num=data['card_num'], ifsc=data['ifsc'], payment_type=data['payment_type'], billing_address=data['billing_address'],
            address_line1=data['address_line1'], address_line2=data['address_line2'], state=data['state'], country=data['country']
        )
        if not transaction_bank_details_qs.exists():
            transaction_bank_details_obj = TransactionBankDetails.objects.create(
                bank_name=data['bank_name'], card_num=data['card_num'], ifsc=data['ifsc'], payment_type=data['payment_type'], billing_address=data['billing_address'],
            address_line1=data['address_line1'], address_line2=data['address_line2'], state=data['state'], country=data['country']
            )
        else:
            transaction_bank_details_obj = transaction_bank_details_qs.first()
        transdetail_obj = TransactionDetails.objects.create(
            transaction_id=data['transaction_id'], billing=billing_obj,
            bankname=transaction_bank_details_obj, plan_details=data['plan']
        )
        return Response(
            'created successfully'
        )

    def put(self, request):
        data = request.data
        transaction_id = data['transaction_id']
        transaction_obj = get_object_or_404(TransactionDetails, transaction_id=transaction_id)
        billing_obj = transaction_obj.billing
        billing_obj.payment_updated_by = data['payment_updated_by']
        billing_obj.payment_status = data['payment_status']
        billing_obj.save()
        return Response(
            'billing updated successfully'
        )
