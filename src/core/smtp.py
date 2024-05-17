import logging

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest
from django.template import Context, Template
from django.template.loader import render_to_string

from post_office import mail


logger = logging.getLogger(__name__)


def send_email(
    recipients,
    subject,
    template_name=None,
    template=None,
    from_email=None,
    cc_emails=[],
    bcc_emails=[],
    message=None,
    raw_message=None,
    reply_to="",
    headers={},
    attachments=[],
    scheduled_time=None,
    backend="",
    render_on_delivery=False,
    **context,
):
    """
    The base function for sending an E-mail.

    AJAY, 04.01.2023
    """
    if not isinstance(recipients, list) and not isinstance(recipients, tuple):
        recipients = [recipients]

    if "site" not in context:
        context["site"] = Site.objects.get_current()

    if "core_host_url" not in context:
        scheme = HttpRequest().scheme
        core_url = scheme + "://" + Site.objects.get_current().domain
        context["core_host_url"] = core_url

    if template_name is None and template is None and message is None:
        raise ImproperlyConfigured(
            "`send_email` function requires either template, template_name "
            "or message argument."
        )

    # Settling the from_email argument if it doesnt exist
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    # Handling the Reply-To header
    if hasattr(settings, "EMAIL_SETTINGS"):
        reply_to = settings.EMAIL_SETTINGS.get(backend, {}).get("REPLY_TO", None)
    else:
        reply_to = settings.DEFAULT_REPLY_TO
        logger.debug("Reply to retrieved from settings: {}".format(reply_to))
    if reply_to:
        headers.update({"Reply-To": reply_to})
        logger.debug("Updated kwargs: {}".format(headers))

    # Monkey patch
    if bcc_emails == ["None"] or not bcc_emails:
        bcc_emails = []
    if cc_emails == ["None"] or not cc_emails:
        cc_emails = []

    # If the message is none, assume there is a template and context
    # to generate this E-mail from
    if message is None:
        if template_name:
            message = render_to_string(template_name, context)
        elif template:
            template = Template(template)
            message = template.render(context=Context(context))

    if raw_message is None:
        raw_message = message

    email = mail.send(
        recipients,
        from_email,
        subject=subject,
        message=message,
        html_message=message,
        template=template,
        language="language",
        cc=cc_emails,
        bcc=bcc_emails,
        attachments=attachments,
        context=context,
        headers=headers,
        scheduled_time=scheduled_time,
        backend=backend,
        render_on_delivery=render_on_delivery,
    )

    return email
