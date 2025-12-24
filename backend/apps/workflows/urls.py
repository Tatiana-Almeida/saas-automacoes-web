from django.urls import path
from .views import WorkflowsStatusView, WorkflowExecuteView

urlpatterns = [
    path('workflows/status', WorkflowsStatusView.as_view(), name='workflows_status'),
    path('workflows/execute', WorkflowExecuteView.as_view(), name='workflows_execute'),
]
