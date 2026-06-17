"""
django_totp.email
=================

Email sending utilities for TOTP recovery: requesting a recovery link
when a user has lost access to their TOTP device, and confirming once
TOTP has been disabled on their account.
"""

from django.conf import settings as django_settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.template.context import make_context
from django.template.loader import get_template
from django.views.generic.base import ContextMixin

from . import email_utils

TOTP_RECOVERY_EMAIL_TEMPLATE = getattr(
    django_settings, "TOTP_RECOVERY_EMAIL_TEMPLATE", "email/totp_recovery.html"
)
TOTP_DISABLED_EMAIL_TEMPLATE = getattr(
    django_settings, "TOTP_DISABLED_EMAIL_TEMPLATE", "email/totp_disabled.html"
)

TOTP_RECOVERY_CONFIRM_URL = getattr(
    django_settings, "TOTP_RECOVERY_CONFIRM_URL", "/totp-recovery/{uid}/{token}"
)

DEFAULT_DOMAIN = getattr(django_settings, "DOMAIN", "localhost:3000")
DEFAULT_SITE_NAME = getattr(django_settings, "SITE_NAME", "localhost")
DEFAULT_PROTOCOL = getattr(django_settings, "PROTOCOL", "http")
DEFAULT_FROM_EMAIL = django_settings.DEFAULT_FROM_EMAIL


class BaseEmailMessage(mail.EmailMultiAlternatives, ContextMixin):
    """Renders subject/text/html blocks out of a single Django template."""

    _node_map = {
        "subject": "subject",
        "text_body": "body",
        "html_body": "html",
    }
    template_name = None

    def __init__(self, request=None, context=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.context = {} if context is None else context
        self.html = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        context = dict(ctx, **self.context)

        user = context.get("user") if context.get("user") else self.request.user

        context.update(
            {
                "domain": DEFAULT_DOMAIN,
                "protocol": DEFAULT_PROTOCOL,
                "site_name": DEFAULT_SITE_NAME,
                "user": user,
            }
        )
        return context

    def render(self):
        context = make_context(self.get_context_data(), request=self.request)
        template = get_template(self.template_name)
        with context.bind_template(template.template):
            for node in template.template.nodelist:
                self._process_node(node, context)
        self._attach_body()

    def send(self, to, fail_silently=False, **kwargs):
        self.render()

        self.to = to
        self.reply_to = kwargs.pop("reply_to", [])
        self.from_email = kwargs.pop("from_email", DEFAULT_FROM_EMAIL)
        self.request = None
        super().send(fail_silently=fail_silently)

    def _process_node(self, node, context):
        attr = self._node_map.get(getattr(node, "name", ""))
        if attr is not None:
            setattr(self, attr, node.render(context).strip())

    def _attach_body(self):
        if self.body and self.html:
            self.attach_alternative(self.html, "text/html")
        elif self.html:
            self.body = self.html
            self.content_subtype = "html"


class TotpRecoveryEmail(BaseEmailMessage):
    """
    Sent when a user has lost their TOTP device and requests recovery.
    """

    template_name = TOTP_RECOVERY_EMAIL_TEMPLATE

    def get_context_data(self):
        context = super().get_context_data()

        user = context.get("user")
        context["uid"] = email_utils.encode_uid(user.pk)
        context["token"] = default_token_generator.make_token(user)
        context["url"] = TOTP_RECOVERY_CONFIRM_URL.format(**context)
        return context


class TotpDisabledEmail(BaseEmailMessage):
    """Sent once TOTP has been disabled on a user's account."""

    template_name = TOTP_DISABLED_EMAIL_TEMPLATE
