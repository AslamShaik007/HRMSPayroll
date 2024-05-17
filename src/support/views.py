import requests

import django
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model, authenticate, logout, login
from django.shortcuts import redirect
from django.db.models import Q, Value, F, CharField
from django.db.models.functions import Concat
from django.http import HttpResponse, JsonResponse
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.text import slugify
from django.db import transaction

from rest_framework import status, permissions, authentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer

from .models import Tickect
from core.central_permissions import IsCentralOrAuthenticated

class TicketApiView(APIView):
    # permission_classes = [permissions.IsAuthenticated]
    permission_classes = (permissions.AllowAny, )
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]

    def get(self, request):
        print(request.headers)
        data = Tickect.objects.all().values()
        # return Response({ "request": request, "data":qs},template_name='ticket.html')
        # return Response({ 
        #                  "request": request,
        #                  "data":qs,
        #                  'activeFor':'create_ticket'
        #             },template_name='create_ticket.html'
        #         )
        
        if "ticketapi/create/" in request.path:
            templ = "create_ticket.html"
            activeFor = "create_ticket"
        elif "listing-tickets" in request.path:
            templ = "listing_tickets.html"
            activeFor = "listing_tickets"
        else:
            templ = "create_ticket.html"   
            activeFor = "create_ticket" 
            
        return Response(
            {
                "data": data,
                'activeFor':activeFor
            },
            template_name=templ
        )
    
    def post(self, request):
        data = request.data
        user = request.user
        title = data['title']
        ticket_obj = Tickect.objects.create(
            title=title, description=data.get('description'),
            raised_by={'id': user.id, 'name': user.employee_details.first().name},
            category=data['category']
        )
        url = 'http://54.210.248.129/support/tickets/'
        resp = requests.post(url, json={
            'ticket_id': ticket_obj.ticket_id,
            'title': ticket_obj.title,
            'description': ticket_obj.description,
            'organization': request.user.employee_details.first().company.company_name,
            'raised_by': ticket_obj.raised_by,
            'status': ticket_obj.status,
            'category': ticket_obj.category
        })
        
        # return redirect('support:ticketapi')
        return Response({
            "response": 'success',
            "msg":"",
            "title":"Success",
            "type":"success",
            "status":status.HTTP_200_OK
        })
    
    def put(self, request):
        data = request.data
        ticket_pk = data.get('id')
        obj = get_object_or_404(Tickect, id=ticket_pk)
        obj.update(**data)
        obj.save()
        return Response("Updated Successfully")

class CentralTicketUpdateAPIView(APIView):
    permission_classes = (permissions.AllowAny, )
    renderer_classes = [TemplateHTMLRenderer, JSONRenderer]
    
    def put(self, request):
        data = request.data
        ticket_id = data['ticket_id']
        ticket_obj = get_object_or_404(Tickect, ticket_id=ticket_id)
        ticket_obj.comments = data.get('comments')
        ticket_obj.status = data.get('status')
        ticket_obj.resolved_by = data.get('resolved_by')
        ticket_obj.save()
        # return Response("Updated Successfully")
        return Response({
            "response": 'success',
            "msg":"",
            "title":"Success",
            "type":"success",
            "status":status.HTTP_200_OK
        })