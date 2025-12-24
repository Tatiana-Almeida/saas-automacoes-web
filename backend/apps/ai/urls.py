from django.urls import path
from .views import AiStatusView, AiInferView

urlpatterns = [
    path('ai/status', AiStatusView.as_view(), name='ai_status'),
    path('ai/infer', AiInferView.as_view(), name='ai_infer'),
]
