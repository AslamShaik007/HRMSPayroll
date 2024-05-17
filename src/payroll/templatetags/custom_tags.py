from django import template
from num2words import num2words
from dateutil.relativedelta import relativedelta

register = template.Library()


def replace_num_words(value, arg):
    # print("value",value,"arg",arg)
    #https://pypi.org/project/num2words/
    if not value:
        return ""
    currency_words = num2words(value, to = 'cardinal', lang="en_IN")    
    return currency_words.replace('-',' ')

@register.filter
def int_to_str(value):
    """converts int to string"""
    return "`"+str(value)+" "

@register.filter
def get_next_month_name(date):
        
    return date + relativedelta(months=1) 

register.filter('replace_num_words', replace_num_words)

from django.template.defaultfilters import stringfilter


@register.filter(name='format_with_commas')
@stringfilter
def format_with_commas(value):
    try:
        value = float(value)
        formatted_value = '{:,.2f}'.format(value)
        return formatted_value
    except (TypeError, ValueError):
        return value

@register.filter
def null_as_na(value):
    na_lst = ["None", None, "null", ""]
    if value in na_lst:
        return "NA"
    return value