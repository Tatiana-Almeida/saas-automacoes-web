from rest_framework import viewsets, permissions
from .models import Automation
from .serializers import AutomationSerializer


class AutomationViewSet(viewsets.ModelViewSet):
    queryset = Automation.objects.all()
    serializer_class = AutomationSerializer
    permission_classes = [permissions.IsAuthenticated]
