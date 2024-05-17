import datetime

from rest_framework import serializers

from .models import Events, Holidays
from django.db.models import Q
from core.utils import timezone_now

class CompanyHolidaysSerializer(serializers.ModelSerializer):
    """
    Company Holidays Serializer

    SURESH, 03.02.2023
    """

    class Meta:
        model = Holidays
        fields = (
            "id",
            "company",
            "holiday_name",
            "holiday_date",
            "description",
            "holiday_type",
            "is_deleted",
        )
    
    def validate(self, data):
        today = timezone_now().date()
        if data.get('holiday_date','') and data.get('holiday_date') < today:
            raise serializers.ValidationError(
                {
                    'message': "Holidays Cannot Be Added For Past Dates"
                }
            )  
        holiday_qs = Holidays.objects.filter(
            holiday_name__iexact = data.get('holiday_name'),
            holiday_date=data.get('holiday_date'),
            company_id=data.get('company').id if data.get('company') else None,
            is_deleted=False
        ).exclude(id=self._kwargs['context'].get('holiday_id'))
        if holiday_qs.exists():
            raise serializers.ValidationError(
                {
                    'message': "Holiday with this date Already Exists"
                }
            )  
        today = timezone_now().date()
        if holiday_id := self._kwargs['context'].get('holiday_id'):
            holiday_ins = Holidays.objects.get(id=holiday_id)
            holiday_date = holiday_ins.holiday_date
            if today >= holiday_date:
                raise serializers.ValidationError(
                    {
                        'message': "Holiday Already started Cant be Edit or deleted"
                    }
                )
        return data

class CompanyHolidaysDetailSerializer(serializers.ModelSerializer):
    """
    Company Holidays Serializer

    SURESH, 03.02.2023
    """

    class Meta:
        model = Holidays
        fields = (
            "id",
            "company",
            "holiday_name",
            "holiday_date",
            "description",
            "holiday_type",
            "is_deleted",
        )


# class HolidaysImportSerializer(serializers.Serializer):

#     holidays_file = serializers.FileField(required=False)

#     def create(self, validate_data):

#         request = self.context["request"]
#         file = request.FILES["holidays_file"]
#         df = pd.read_excel(file, keep_default_na=False, usecols="A:C")
#         optimized_data = [
#             record for record in df.to_dict(orient="record") if any(record.values())
#         ]
#         errors = []
#         serializer = None
#         print(optimized_data)
#         for data in optimized_data:
#             try:
#                 payload = {
#                     "company": request.POST["company"],
#                     "holiday_name": data.get("Name of Holiday"),
#                     "holiday_date": data.get("Date (DD/MM/YYYY)"),
#                     "holiday_type": data.get("Is Optional")
#                     if data.get("Is Optional", None)
#                     else 0,
#                 }

#                 serializer = CompanyHolidaysSerializer(data=payload)
#                 print(payload)
#                 if serializer.is_valid(raise_exception=True):
#                     serializer.save()
#             except Exception:
#                 errors.append({"error": "please give proper data!"})

#         if errors:
#             raise serializers.ValidationError(errors)
#         return serializer


class CompanyEventSerializer(serializers.ModelSerializer):
    """
    Company Event Serializer

    SURESH, 03.02.2023
    """

    class Meta:
        model = Events
        fields = (
            "id",
            "company",
            "visibility",
            "departments",
            "event_title",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "event_description",
            "is_deleted",
        )
    
    def validate(self, data):
        event_id = self.context.get('event_id','')
        exclude = Q()
        if event_id: exclude = Q(id = event_id)
        filters = {
            'event_title': data.get('event_title'),
            'company_id' : data.get('company').id,
            'is_deleted' : False,
            'start_date__lte' : data.get('end_date'),
            'end_date__gte' : data.get('start_date'),
        }
        if Events.objects.filter(**filters).exclude(exclude).exists():
            raise serializers.ValidationError(
                {
                    'message': "Event Already Exists"
                }
            )
        return data


class CompanyEventDetailSerializer(serializers.ModelSerializer):
    """
    Company Event Serializer

    SURESH, 03.02.2023
    """

    class Meta:
        model = Events
        fields = (
            "id",
            "company",
            "visibility",
            "departments",
            "event_title",
            "start_date",
            "start_time",
            "end_date",
            "end_time",
            "event_description",
            "is_deleted",
        )
