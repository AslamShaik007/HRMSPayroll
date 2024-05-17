import logging
import os
import requests
import pyshorteners

environment = os.environ.get('APP_ENV', 'local')
logger = logging.getLogger('django')


class WhatsappMessage:
              
    @staticmethod    
    def whatsapp_message(data):
        url = 'https://db.vitelsms.com/whatsapp/templates/send_utility_template'
        header_text = data.get('subject')
        body_text1 = data.get('body_text1')
        body_text2 = data.get('body_text2')
        body_text3 = data.get('url')
        body_text4 = data.get('company_name')
        if isinstance(data.get('phone_number'), list):
            ml_numbers = ['91' + number for number in data.get('phone_number')]
            phone_number = ', '.join(ml_numbers)
        else:
            phone_number = '91'+ data.get('phone_number')
        #convert url to short url
        type_tiny = pyshorteners.Shortener()
        short_url = type_tiny.tinyurl.short(body_text3)
        payload = {
            'phone_numbers': phone_number,
            'template_name': 'default_template_hrms',
            'username': 'enquiry@bharatpayroll.com',
            'token_no': 'EAAKTIe6RYuMBAOMQ8pvOIlxj6LOjUYB8Fq0JaYPcnwq4eM6hfEwJAXL7bQZCDoopfZB1kvIRZCKcAFQ81z1z7LnRuMXqoFsfa8TANvLvzr89YbWvralvqZAtnodDPuUHRZCoDhSWbfd5OeAO7OACUlD9ECDOpqojTKodyFjlZBoeBfh6V3fNlI',
            'header_text': header_text,
            'body_text1': body_text1,
            'body_text2': body_text2,
            'body_text3': short_url,
            'body_text4': body_text4,
        }
        try:
            response = requests.post(url, data=payload)
            logger.info(f"Whatsapp Message Sent Successfully, Subject:{header_text}, Mobile:{phone_number}, response:{response.text}")
        except Exception as e:
            logger.warning(f"Error while sending Whatsapp notificatons: {e}")  
                

   