from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.core.management.base import BaseCommand, CommandError
from django.template.loader import render_to_string


class Command(BaseCommand):
    help = "Send a test email using current EMAIL_* settings"

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient email address")
        parser.add_argument("--subject", default="Test Email", help="Email subject")
        parser.add_argument(
            "--body", default="This is a test email.", help="Email body"
        )
        parser.add_argument(
            "--html",
            default=None,
            help="Optional HTML body (if omitted, a template will be used)",
        )

    def handle(self, *args, **options):
        to_email = options["to"]
        subject = options["subject"]
        body = options["body"]
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        if not from_email:
            raise CommandError("DEFAULT_FROM_EMAIL is not configured")

        html = options["html"]
        try:
            if html is None:
                context = {
                    "body": body,
                    "site_name": getattr(settings, "SITE_NAME", "SaaS"),
                }
                text_message = render_to_string("emails/test_email.txt", context)
                html_message = render_to_string("emails/test_email.html", context)
            else:
                text_message = body
                html_message = html
            msg = EmailMultiAlternatives(subject, text_message, from_email, [to_email])
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
        except Exception as e:
            # Fallback to plain text
            sent = send_mail(subject, body, from_email, [to_email], fail_silently=False)
            if sent == 0:
                raise CommandError(f"Email not sent: {e}")
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {to_email}"))
