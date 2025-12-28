from django.core.paginator import Paginator
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView
from starter.api.views import TenantScopedViewSet

from ..models import Automation, AutomationLog, AutomationRunStatus
from ..tasks import run_automation_task
from .serializers import AutomationLogSerializer, AutomationSerializer


class AutomationViewSet(TenantScopedViewSet):
    serializer_class = AutomationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Automation.objects.all()
        user = self.request.user
        if not (user.is_staff or getattr(user, "is_superuser", False)):
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        automation = self.get_object()
        automation.activate()
        return Response(AutomationSerializer(automation).data)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        automation = self.get_object()
        automation.pause()
        return Response(AutomationSerializer(automation).data)

    @action(detail=True, methods=["post"])
    def trigger(self, request, pk=None):
        automation = self.get_object()
        if not automation.is_active:
            return Response(
                {"detail": "Automação está pausada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Start log as STARTED
        log = AutomationLog.objects.create(
            automation=automation,
            status=AutomationRunStatus.STARTED,
            started_at=timezone.now(),
        )
        # Call async task (can also be called synchronously in tests)
        run_automation_task.delay(automation.id, log.id)
        return Response({"detail": "Execução iniciada", "log_id": log.id})

    @action(detail=True, methods=["get"])
    def logs(self, request, pk=None):
        automation = self.get_object()
        logs = automation.logs.all()[:100]
        return Response(AutomationLogSerializer(logs, many=True).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="reports/summary",
        url_name="report-summary",
    )
    def report_summary(self, request):
        qs = self.get_queryset()
        total = qs.count()
        active = qs.filter(is_active=True).count()
        paused = qs.filter(is_active=False).count()
        # recent executions (last 24h)
        last_24h = timezone.now() - timezone.timedelta(hours=24)
        recent_logs = AutomationLog.objects.filter(
            automation__in=qs, created_at__gte=last_24h
        )
        succeeded = recent_logs.filter(status=AutomationRunStatus.SUCCEEDED).count()
        failed = recent_logs.filter(status=AutomationRunStatus.FAILED).count()
        return Response(
            {
                "total": total,
                "active": active,
                "paused": paused,
                "last_24h_logs": recent_logs.count(),
                "succeeded": succeeded,
                "failed": failed,
            }
        )


class AutomationDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "automations/dashboard.html"

    def get(self, request):
        qs = Automation.objects.filter(user=request.user).order_by("-updated_at")
        q = request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        t = request.query_params.get("type")
        if t:
            qs = qs.filter(type=t)
        active = request.query_params.get("active")
        if active == "true":
            qs = qs.filter(is_active=True)
        elif active == "false":
            qs = qs.filter(is_active=False)
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        return Response({"automations": page_obj.object_list, "page_obj": page_obj})
