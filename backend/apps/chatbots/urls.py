from django.urls import path
from .views import ChatbotsStatusView, ChatbotSendMessageView

urlpatterns = [
    path("chatbots/status", ChatbotsStatusView.as_view(), name="chatbots_status"),
    path(
        "chatbots/messages/send", ChatbotSendMessageView.as_view(), name="chatbots_send"
    ),
]
