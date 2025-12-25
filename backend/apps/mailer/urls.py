from django.urls import path
from .views import MailerStatusView, MailerSendEmailView

urlpatterns = [
    path("email/status", MailerStatusView.as_view(), name="email_status"),
    path("email/messages/send", MailerSendEmailView.as_view(), name="email_send"),
]
