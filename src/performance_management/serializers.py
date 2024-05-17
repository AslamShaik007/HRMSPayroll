from rest_framework import serializers
from performance_management.models import AppraisalSetName, AppraisalSetQuestions,AppraisalSendForm,NotificationDates,AppraisalFormSubmit
from django.db import transaction
from core.serializers import QuerysetFilterSerializer
from rest_framework import status
from directory.models import EmployeeWorkDetails, Employee
from company_profile.models import Departments
import datetime
from core.utils import (
    timezone_now,
)
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
import pandas as pd

class AppraisalSetQuestionsSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = AppraisalSetQuestions
        list_serializer_class = QuerysetFilterSerializer
        fields = [
            'id',
            'set_name',
            'is_active',
            'creation_date',
            'questions',
            'is_deleted'
        ]
        extra_kwargs = {
            "set_name": {"required":False}
        }

class AppraisalSetQuestionsDetailsSerializer(serializers.ModelSerializer):

    class Meta:
        model = AppraisalSetQuestions
        list_serializer_class = QuerysetFilterSerializer
        fields = [
            'id',
            'set_name',
            'is_active',
            'creation_date',
            'questions',
            'is_deleted'
        ]


class AppraisalSetNameSerializer(serializers.ModelSerializer):
    questions = AppraisalSetQuestionsSerializer(many=True, required=False, source='setname_questions')
    no_of_question = serializers.SerializerMethodField(read_only = True)
    author_name = serializers.SerializerMethodField(read_only = True)

    class Meta:
        model = AppraisalSetName
        fields = [
            'id',
            'company',
            'name',
            'author',
            'author_name',
            'set_number',
            'no_of_question',
            'is_active',
            'questions',
            'is_deleted',
            'created_at',
        ]


    def get_no_of_question(self, obj):
        ques_count = AppraisalSetQuestions.objects.filter(set_name__name = obj.name, set_name__company = obj.company, is_deleted = False).count()
        return ques_count


    def get_author_name(self, obj):
        return obj.author.name


    def validate(self, attrs):
        if self.instance:

            # day = timezone_now().date()
            # my = day.strftime('%m-%y')
            # filtering_obj = AppraisalSetName.objects.filter(company = attrs['company'])
            # for filtering_obj in filtering_obj:
            #     obj_created = filtering_obj.created_at.strftime('%m-%y')
            #     if obj_created == my and filtering_obj.name == attrs['name']:
            #         raise serializers.ValidationError({
            #             "status": status.HTTP_400_BAD_REQUEST,
            #             "response": "Set Name For Company Already Exists,Try Different Set Name"
            #         })
            return super().validate(attrs)


        obj = AppraisalSetQuestions.objects.filter(set_name__company_id = attrs['company'])
        for i in obj:
            now_date = timezone_now().date()
            present_date = now_date.strftime('%m-%y')
            strf_time = i.creation_date
            obj_date = strf_time.strftime('%m-%y')

            if present_date == obj_date and str(i.set_name.name).lower().strip() == str(attrs['name']).lower().strip():
                raise serializers.ValidationError({
                    "error": "The Given Set Name is Already Exists In Present Month"
                })
        return attrs


    def create_setname_question(self, validated_data, instance):
        AppraisalSetQuestions.objects.filter(set_name_id = instance.set_number).update(is_deleted=True)
        for data in validated_data:
            data["set_name"] = instance
            # AppraisalSetQuestions.objects.update_or_create(
            #     id=data.pop("id", None), defaults=data
            # )
            qs_id = data.get('id',None)
            if qs_id:
                AppraisalSetQuestions.objects.filter(id=qs_id).update(**data)
            else:
                AppraisalSetQuestions.objects.create(**data)
                

    # @transaction.atomic
    def create(self, validated_data):
        """
        Overwrite create method to cater for nested object save

        Aslam, 09.05.2023
        """
        sid = transaction.set_autocommit(autocommit=False)
        try:
            questions = validated_data.pop("setname_questions", [])
            setnames = AppraisalSetName.objects.create(**validated_data)
            # setnames.set_number = AppraisalSetName.objects.order_by().values_list('set_number').distinct().count()
            setnames.set_number = setnames.id
            setnames.save()
            self.create_setname_question(questions, setnames)
            transaction.commit()
        except Exception as e:
            transaction.rollback(sid)
            raise e
        return setnames


    # @transaction.atomic
    def update(self, instance, validated_data):
        """
        Overwrite update method

        Aslam, 10.05.2023
        """

        self.create_setname_question(
            validated_data.pop("setname_questions", []), instance
        )
        return super().update(instance, validated_data)



class AppraisalSetNameDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppraisalSetName
        fields = [
            "id",
            "name",
            "author",
            "set_number",
            "company",
            "is_active",
            'is_deleted'
        ]


class RetriveAllDepartmentsSerializer(serializers.ModelSerializer):
    """
    Retriving All Departments Names Serializer

    Aslam 23-05-2023
    """

    class Meta:
        model = Departments
        fields = [
            "id",
            "name"
        ]





class AppraisalSendFormSerializer(serializers.ModelSerializer):
    ques_ans = serializers.SerializerMethodField(required=False)
    employee_details = serializers.SerializerMethodField(required=False)

    class Meta:
        model = AppraisalSendForm
        fields = [
            "id",
            "employee",
            "set_id",
            "creation_date",
            "candidate_status",
            "Emp_suggestion",
            "manager_acknowledgement",
            "score",
            "monthly_score_status",
            "email_status",
            "is_revoked",
            "comment",
            "reason",
            "employee_details",
            "ques_ans",
        ]

    def get_employee_details(self, obj):
        return {
            'employee_name': obj.employee.first_name,
            'employee_number': obj.employee.work_details.employee_number,
            'department': obj.employee.work_details.department.name if obj.employee.work_details.department else "--"
        }
         

    def get_ques_ans(self, obj):
        month = timezone_now().month
        year = timezone_now().year
        fill = AppraisalFormSubmit.objects.filter(employee__id=obj.employee_id, sentform_date__month=month, sentform_date__year=year).select_related('question').annotate(
            id_question=F('question'),
            name_question = F('question__questions'),
        ).values(
            'id_question',
            'name_question',
            'answer',
            )
        return fill


class NotificationDateSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotificationDates
        fields = [
            "id",
            "notification_start_date",
            "notification_end_date",
            "reporting_manager_start_date",
            "reporting_manager_end_date",
            "employees_kra_deadline_date"
        ]


class AppraisalFormSubmitSerializer(serializers.ModelSerializer):
    ques_ans = serializers.JSONField(required = False)
    ques = serializers.SerializerMethodField(required = False)


    class Meta:
        model = AppraisalFormSubmit
        fields = (
            "id",
            "employee",
            "set_name",
            "question",
            "ques",
            "answer",
            "sentform_date",
            "candidate_status",
            "ques_ans",
        )
        extra_kwargs = {
            "question": {"required": False},
            "ques_ans": {"required": False}
        }

    def validate(self, attrs):
        if self.instance:    
            return super().validate(attrs)
        month = timezone_now().date().month
        year = timezone_now().date().year
        if qs := AppraisalFormSubmit.objects.filter(employee_id = attrs['employee'], set_name__name=attrs['set_name'],
                                                    candidate_status="SUBMITTED", sentform_date__month=month, sentform_date__year=year).exists():
            raise serializers.ValidationError({
                "error": "Already Submitted Form On Given Set Name For The Month"
            })
        return attrs


    def create(self, validated_data):
        results = []
        
        data_df = pd.DataFrame(validated_data['ques_ans'])
        data_df['employee']=validated_data['employee']
        data_df['employee']=validated_data['employee'].id
        data_df['set_name']=validated_data['set_name'].id
        results = AppraisalFormSubmit.objects.filter(employee=validated_data['employee'].id, set_name=validated_data['set_name'].id)
        data_df['data_existed'] = results.exists()
        data_df.apply(lambda obj: AppraisalFormSubmit.objects.filter(employee_id=validated_data['employee'].id, 
                                                                     set_name_id=validated_data['set_name'].id,
                                                                     question_id = obj['question']
                                                                     ).update(answer=obj['answer'],
                                                                              candidate_status=validated_data['candidate_status']) if obj['data_existed'] else AppraisalFormSubmit.objects.create(
            employee=validated_data['employee'],
            set_name=validated_data['set_name'],
            candidate_status=validated_data['candidate_status'],
            question_id=obj['question'],
            answer=obj['answer']
        ), axis=1)
        return  results


    def get_ques(self, obj):
        return obj.question.questions