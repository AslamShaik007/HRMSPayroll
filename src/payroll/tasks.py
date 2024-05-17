from django.conf import settings

from django.core.mail import send_mail
from django.template.loader import get_template

from celery import shared_task

@shared_task
def send_notification_email(context):     
    try:
        txt_ = get_template("payroll/mail/temp1.txt").render(context)
        html_ = get_template("payroll/mail/temp1.html").render(context)
        subject = 'Notification'
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [context['email']]
        send_mail(
                    subject,
                    txt_,
                    from_email,
                    recipient_list,
                    html_message=html_,
                    fail_silently=False                
            )

        return 'success'
    except Exception as e:
        return str(e)