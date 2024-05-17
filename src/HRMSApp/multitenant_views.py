import pandas as pd
import re
import datetime
import traceback
import psycopg2
import django
import logging
from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response

from core.utils import success_response, error_response

from company_profile.models import CompanyDetails
from .models import MultiTenantCompanies , Roles
import requests
import tldextract
from django.db.models import Q
from django.db import connection
logger = logging.getLogger('django')
"""
Created-By: Padmaraju
Created-At: 25-02-2024
UseCase: Views And Functions will be here For Multitenant.
"""

# def db_connection_master():
#     return psycopg2.connect(
#         dbname="master_db",
#         user=django.db.connections.databases['default']['USER'],
#         host=django.db.connections.databases['default']['HOST'],
#         password=django.db.connections.databases['default']['PASSWORD']
#     )

# def select_multitenant_companies(mul_id):
#     conn = db_connection_master()
#     sql_command = f"SELECT * FROM companies WHERE mul_key='{mul_id.strip()}';"
#     cursor = conn.cursor()
#     cursor.execute(sql_command)
#     data = cursor.fetchall()
#     column_names = [desc[0] for desc in cursor.description]
#     cursor.close()
#     conn.close()
#     df = pd.DataFrame(data, columns=column_names)
#     df.mul_key = df.mul_key.apply(lambda x: x.strip())
#     df.subdomain = df.subdomain.apply(lambda x: x.strip())
#     df.companyname = df.companyname.apply(lambda x: x.strip())
#     return df.to_dict('records')

class FetchMultitenantCompaniesAPIView(APIView):
    
    permission_classes = [permissions.IsAuthenticated,]
    
    def get(self, request):
        if not request.query_params.get("mul_key"):
            return Response(
                {
                    "status_code" : 400,
                    "message" : "multitenant id is required"
                },
                status=400
            )
        # if  MultiTenantCompanies.objects.using("master_db").filter(
        #     cmp_id = request.query_params.get("cmp_id"),
        #     is_primary = True
        # ).exists():
        data = MultiTenantCompanies.objects.using("master_db").filter(
            Q(mul_key = request.query_params.get("mul_key")),
            ~Q(cmp_id = request.query_params.get("cmp_id"))
        ).values("mul_key", "subdomain", 
                "is_primary", "is_multitenant",
                "companyname", "cmp_id"
        )
        return Response(
            data, status=status.HTTP_200_OK
        )
        # else:
        #     return Response(
        #         [], status=status.HTTP_200_OK
        #     )
        
        
class EnableMultiTenant(APIView):
    
    permission_classes = [permissions.IsAuthenticated,]
    
    def put(self, request,*args,**kwargs):
        pk = kwargs.get("pk")
        try:
            role = Roles.objects.get(pk=pk)
        except Roles.DoesNotExist:
            return Response(
                {
                    "status_code" : 400,
                    "message" : "Role with role_id %s is not found" % pk
                },
                status=400
            )
        if not role.is_active:
            return Response(
                {
                    "status_code" : 400,
                    "message" : "Role is Deactivated"
                },
                status=400
            )
        else:
            role.is_multitenant_role = True
            role.save()
            return Response(
                {
                    "status_code" : 200,
                    "message" : "Multitenant Updated Succesfully"
                },
                status=200
            )
            

            
class CreateMultitenantCompanyAPIView(APIView):
    
    permission_classes = [permissions.IsAuthenticated,]
    
    
    def extract_domain_and_subdomain(self, url):
        extracted_info = tldextract.extract(url)
        subdomain = extracted_info.subdomain
        domain = extracted_info.domain
        return subdomain, domain
    
    def generate_tenant_id(slef):
        existing_keys = list(MultiTenantCompanies.objects.using(
            "master_db"
        ).filter().values_list("mul_key", flat=True))
        if existing_keys:
            latest = int(existing_keys[-1])
            latest += 1
            while latest in existing_keys:
                latest += 1
            return latest
        else:
            return 1001
    
    def post(self, request):
        required_params = [
            "parent_company_id",
            "cmp_name" , "cmp_website", "corp_email","cont_person_email",
            "domain", "password",
            "contact_person" , "phone" , "location", "product",
            "category" , "subscription", "brand_name", "sub_domain","point_of_reach",
            "company_size", "license_count",
        ]
        for i in required_params:
            if request.data.get(i) is None:
                return Response(
                    {
                        "status_code" : 400,
                        "message" : "%s is required" % i
                    },
                    status=400
                )
        
        current_db_name = connection.settings_dict['NAME']
        current_subdomain = current_db_name.split("_")[0]
        cmp_details = CompanyDetails.objects.get(
                company__id = request.data.get("parent_company_id")
        )
        if not cmp_details.multitenant_key:
            mul_key = self.generate_tenant_id()
        else:
            mul_key = cmp_details.multitenant_key
        try:
            request.data._mutable = True
        except Exception:
            pass  
        request.data["multitenant_key"] = mul_key
        req = requests.post(
            url = "https://qaengine.indianhr.in/apiV1/add-tenant-customer-phase1/",
            data = request.data
        )
        logger.info(req.status_code)
        if req.status_code == 200:
            response_data = req.json()
            company_link = response_data.get(
                "redirection_link"
            )
            sub_domain,domain =  self.extract_domain_and_subdomain(company_link)
            MultiTenantCompanies.objects.using("master_db").create(
                mul_key = mul_key,
                subdomain = sub_domain,
                is_primary = False,
                is_multitenant = True,
                companyname = request.data.get("cmp_name"),
                cmp_id = response_data.get("companyUid")
            )
            existing = cmp_details.child_company_uids
            if not cmp_details.multitenant_key:
                cmp_details.multitenant_key = mul_key
            existing.append(
                response_data.get("companyUid")
            )
            cmp_details.child_company_uids = existing
            cmp_details.save()
            MultiTenantCompanies.objects.using("master_db").get_or_create(
                subdomain = current_subdomain,
                defaults= {
                    "mul_key" : mul_key,
                    "is_primary" :  True,
                    "is_multitenant" :  True,
                    "companyname" : cmp_details.company_name,
                    "cmp_id" : cmp_details.company_uid
                }
            )
            return Response(
                {
                    "status_code" :  200,
                    "message" : "Multi Tenant Company Created Successfully"
                },
                status=200
            )
        else:
            return Response(
                {
                    "status_code" :  400,
                    # "message" : "Failed to Create Multitenant, contact Technical Team"
                    "message" : req.text
                },
                status=400
            )