from django.template import Template, Context
from django.core.mail import send_mail
from .models import NotificationTemplate

class NotificationService:

    @staticmethod
    def send(event_name: str, ctx: dict, to_email: str):
        try:
            template = NotificationTemplate.objects.get(event_name=event_name)
        except NotificationTemplate.DoesNotExist:
            print("Template not found:", event_name)
            return False

        # Render email contents dynamically
        subject = Template(template.subject).render(Context(ctx))
        body = Template(template.body).render(Context(ctx))

        send_mail(
            subject,
            body,
            "no-reply@synchroni.in",  # sender email
            [to_email],
            fail_silently=False
        )
        return True
