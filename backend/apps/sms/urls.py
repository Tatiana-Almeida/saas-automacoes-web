from django.urls import path
from .views import SmsStatusView, SmsSendMessageView

urlpatterns = [
    path('sms/status', SmsStatusView.as_view(), name='sms_status'),
    path('sms/messages/send', SmsSendMessageView.as_view(), name='sms_send'),
]
