import logging
import os
import re
import base64
import smtplib

from django.core.mail import EmailMessage, get_connection

from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice

from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

environment = os.environ.get('APP_ENV', 'local')
logger = logging.getLogger(__name__)


class Util:
    @staticmethod
    def send_email(data, multiple=False, is_content_html=False, xl_file=None, file_name='data.xlsx', pdf_file=None, pdf_file_name='my_pdf.pdf'): 
        to_email=[data["to_email"]] 
        if multiple:
            to_email=data["to_email"]   
        cc = data.get('cc',[])
        email = EmailMessage(
            subject=data["subject"],
            body=data["body"],
            from_email="noreply@bharatpayroll.com",
            to=to_email,
            cc=cc
        )
        if is_content_html:
            email.content_subtype = 'html'

        if xl_file is not None:
            email.attach(f'{file_name}', xl_file.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        if pdf_file is not None:
            if hasattr(pdf_file, 'read'):
                pdf_content = pdf_file.read()
                email.attach(f'{pdf_file_name}', pdf_content, 'application/pdf')
            else:
                email.attach(f'{pdf_file_name}', pdf_file.getvalue(), 'application/pdf')
        if environment == 'prod':
            email.send()
    def send_custom_email(data, multiple=False, is_content_html=False, xl_file=None, file_name='data.xlsx', pdf_file=None, pdf_file_name='my_pdf.pdf', pdf_bytes_obj=None): 
        from directory.models import CompanySMTPSetup
        
        to_email=[data["to_email"]] 
        if multiple:
            to_email=data["to_email"]   
        cc = data.get('cc',[])
        bcc = data.get('bcc',[])
            
        # Custom Email Connection Set Up
        email_creds = {
            "host":"mail.vitelglobal.com",
            "port":465,
            "username":'noreply',
            "password":'Uaw3XHa1xjlTyjIP',
            "use_tls":True,
            "fail_silently":True
        }
        from_email = "noreply@bharatpayroll.com"
        
        smtp = CompanySMTPSetup.objects.filter(company_id=1)
        if smtp.exists() and smtp.first().is_default:
            smtp_obj = smtp.first()
            email_creds = {
                    "host":smtp_obj.email_host,
                    "port":smtp_obj.email_port,
                    "username":smtp_obj.email_host_user,
                    "password":smtp_obj.email_host_password,
                    "use_tls":True,
                    "fail_silently":True
                }
            from_email = smtp_obj.from_email
        custom_connection = get_connection(**email_creds)    
        
        email = EmailMessage(
            subject=data["subject"],
            body=data["body"],
            from_email=from_email,
            to=to_email,
            cc=cc,
            bcc=bcc,
            connection=custom_connection
        )
        
        if is_content_html:
            email.content_subtype = 'html'

        if xl_file is not None:
            email.attach(f'{file_name}', xl_file.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
        if pdf_file is not None:
            if hasattr(pdf_file, 'read'):
                pdf_content = pdf_file.read()
                email.attach(f'{pdf_file_name}', pdf_content, 'application/pdf')
            else:
                email.attach(f'{pdf_file_name}', pdf_file.getvalue(), 'application/pdf')
        
        if pdf_bytes_obj:
            email.attach(pdf_file_name, pdf_bytes_obj)
                    
        if environment == 'prod':
            is_mail_sent = email.send()
            return bool(is_mail_sent)
    
    def ck_editor_email(data, multiple=False, pdf_file_name='my_pdf.pdf', pdf_bytes_obj=None, pdf_file=None): 
        try:
            from directory.models import CompanySMTPSetup
            # Custom Email Connection Set Up
            email_creds = {
                "host":"mail.vitelglobal.com",
                "port":465,
                "username":'noreply',
                "password":'Uaw3XHa1xjlTyjIP',
                "use_tls":True,
                "fail_silently":True
            }
            from_email = "noreply@bharatpayroll.com"
            
            smtp = CompanySMTPSetup.objects.filter(company_id=1)
            if smtp.exists() and smtp.first().is_default:
                smtp_obj = smtp.first()
                email_creds = {
                        "host":smtp_obj.email_host,
                        "port":smtp_obj.email_port,
                        "username":smtp_obj.email_host_user,
                        "password":smtp_obj.email_host_password,
                        "use_tls":True,
                        "fail_silently":True
                    }
                from_email = smtp_obj.from_email
                
            msg = MIMEMultipart('related')
            msg['Subject'] = data['subject'] 
            to_email=[data["to_email"]] 
            if multiple:
                to_email=data["to_email"] 
            cc_emails = data.get('cc',[])
            bcc_emails = data.get('bcc',[])
            all_recipients = to_email + cc_emails + bcc_emails
            
            #Attach HTML Content
            content = data['content']
            base64_data_list = extract_base64_from_img_src(content)
            new_img_srcs = ["cid:image{}".format(i) for i in range(1, len(base64_data_list) + 1)]
            modified_html_content, count_of_images = replace_figure_with_img(content, new_img_srcs)
            msg.attach(MIMEText(modified_html_content, 'html'))

            for i, base64_data in enumerate(base64_data_list):
                image_mime = MIMEImage(base64.b64decode(base64_data))
                image_mime.add_header('Content-ID', '<image{}>'.format(i + 1))
                msg.attach(image_mime)

            #Attach pdf bytes obj
            if pdf_bytes_obj:
                pdf_attachment = MIMEApplication(pdf_bytes_obj)
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_file_name)
                msg.attach(pdf_attachment)
            
            if pdf_file:
                pdf_attachment = MIMEApplication(pdf_file.read())
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=pdf_file_name)
                msg.attach(pdf_attachment)
            # Send the email via SMTP
            sent_data = []
            with smtplib.SMTP(email_creds['host'], email_creds['port']) as smtp_server:
                smtp_server.starttls()
                smtp_server.login(email_creds['username'], email_creds['password'])
                if environment == 'prod':
                    sent_data = smtp_server.sendmail(from_email, all_recipients, msg.as_string())
            return True, sent_data
        
        except Exception as e:
            return False, str(e)

class Mesg:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data["subject"],
            body=data["body"],
            from_email="enquiry@vitelglobal.in",
            to=[data["to_email"]],
        )
        if environment == 'prod':
            email.send()


def get_user_totp_device(user, confirmed=None):
    devices = devices_for_user(user, confirmed=confirmed)
    for device in devices:
        if isinstance(device, TOTPDevice):
            return device


def extract_base64_from_img_src(html_content):
    
    img_src_regex = re.compile(r'<img[^>]+src="data:image\/[^;]+;base64,([^"]+)"')
    matches = img_src_regex.findall(html_content)

    return matches
def replace_figure_with_img(html_content, new_img_srcs):
    
    soup = BeautifulSoup(html_content, 'html.parser')
    figure_tags = soup.find_all('figure')
    
    for i, figure_tag in enumerate(figure_tags):
        img_tag = figure_tag.find('img')
        if img_tag and i < len(new_img_srcs):
            new_img_tag = soup.new_tag('img', src=new_img_srcs[i])
            figure_tag.replace_with(new_img_tag)

    return str(soup), len(figure_tags) 
