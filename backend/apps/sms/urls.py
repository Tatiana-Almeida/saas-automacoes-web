from django.urls import path

from .views import SmsSendMessageView, SmsStatusView

urlpatterns = [
    path("sms/status", SmsStatusView.as_view(), name="sms_status"),
    path("sms/messages/send", SmsSendMessageView.as_view(), name="sms_send"),
]
