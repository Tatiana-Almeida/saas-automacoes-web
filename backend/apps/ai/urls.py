from django.urls import path

from .views import AiInferView, AiStatusView

urlpatterns = [
    path("ai/status", AiStatusView.as_view(), name="ai_status"),
    path("ai/infer", AiInferView.as_view(), name="ai_infer"),
]
