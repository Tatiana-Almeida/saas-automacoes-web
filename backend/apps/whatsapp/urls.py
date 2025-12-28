from django.urls import path

from .views import WhatsappSendMessageView, WhatsappStatusView

urlpatterns = [
    path("whatsapp/status", WhatsappStatusView.as_view(), name="whatsapp_status"),
    path(
        "whatsapp/messages/send",
        WhatsappSendMessageView.as_view(),
        name="whatsapp_send",
    ),
]
