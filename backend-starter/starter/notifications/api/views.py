from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Sum, Count
from ..models import Notification, NotificationLog, NotificationStatus
from .serializers import NotificationSerializer, SendNotificationSerializer, NotificationLogSerializer
from starter.api.views import TenantScopedViewSet
from starter.api.permissions import IsAdminOrReadOnly
from ..tasks import send_notification_task, send_event_notification_task, generate_reports_task


class NotificationViewSet(TenantScopedViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.all()
        user = self.request.user
        if not (user.is_staff or getattr(user, 'is_superuser', False)):
            qs = qs.filter(user=user)
        return qs

    def perform_create(self, serializer):
        # creation via API is admin-only; enforce in permission or here
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrReadOnly])
    def send(self, request, pk=None):
        notif = self.get_object()
        send_notification_task.delay(notif.id)
        return Response({"detail": "Queued"})

    @action(detail=False, methods=['post'], url_path='send-manual', permission_classes=[IsAdminOrReadOnly])
    def send_manual(self, request):
        s = SendNotificationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=data['user_id'])
        notif = Notification.objects.create(user=user, channel=data['channel'], to=data['to'], title=data['title'], body=data.get('body',''), payload=data.get('payload',{}))
        send_notification_task.delay(notif.id)
        return Response(NotificationSerializer(notif).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        notif = self.get_object()
        logs = notif.logs.all()
        return Response(NotificationLogSerializer(logs, many=True).data)


class NotificationHistoryView(TenantScopedViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.all()
        user = self.request.user
        me = self.request.query_params.get('mine')
        uid = self.request.query_params.get('user_id')
        if me == 'true' or not (user.is_staff or getattr(user, 'is_superuser', False)):
            qs = qs.filter(user=user)
        elif uid:
            qs = qs.filter(user_id=uid)
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        return qs.order_by('-created_at')


class ReportsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.utils.dateparse import parse_datetime
        from starter.orders.models import Order, OrderStatus
        from starter.automations.models import AutomationLog, AutomationRunStatus
        from django.contrib.auth import get_user_model
        User = get_user_model()
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        start_dt = parse_datetime(start) if start else None
        end_dt = parse_datetime(end) if end else None

        # Revenue
        orders = Order.objects.filter(status=OrderStatus.PAID)
        if start_dt:
            orders = orders.filter(ordered_at__gte=start_dt)
        if end_dt:
            orders = orders.filter(ordered_at__lte=end_dt)
        revenue = orders.aggregate(total=Sum('total'))['total'] or 0

        # Automations
        logs = AutomationLog.objects.all()
        if start_dt:
            logs = logs.filter(created_at__gte=start_dt)
        if end_dt:
            logs = logs.filter(created_at__lte=end_dt)
        succeeded = logs.filter(status=AutomationRunStatus.SUCCEEDED).count()
        failed = logs.filter(status=AutomationRunStatus.FAILED).count()

        # Active users (rough proxy)
        active_users = User.objects.filter(is_active=True).count()

        # Notifications counts
        notifs = Notification.objects.all()
        if start_dt:
            notifs = notifs.filter(created_at__gte=start_dt)
        if end_dt:
            notifs = notifs.filter(created_at__lte=end_dt)
        sent_count = notifs.filter(status=NotificationStatus.SENT).count()
        failed_count = notifs.filter(status=NotificationStatus.FAILED).count()

        return Response({
            "revenue": str(revenue),
            "paid_orders": orders.count(),
            "automations": {"succeeded": succeeded, "failed": failed},
            "active_users": active_users,
            "notifications": {"sent": sent_count, "failed": failed_count},
        })

    def post(self, request):
        # Queue heavy report generation
        start = request.data.get('start')
        end = request.data.get('end')
        res = generate_reports_task.delay(start, end)
        return Response({"task_id": res.id})


class EventNotificationsView(APIView):
    permission_classes = [IsAdminOrReadOnly]

    def post(self, request):
        event = request.data.get('event')  # e.g., 'payment_succeeded'
        user_id = request.data.get('user_id')
        title = request.data.get('title') or f"Evento: {event}"
        body = request.data.get('body', '')
        channel = request.data.get('channel', 'email')
        payload = request.data.get('payload', {})
        if not event or not user_id:
            return Response({"detail": "event and user_id required"}, status=status.HTTP_400_BAD_REQUEST)
        task_id = send_event_notification_task.delay(event, user_id, title, body, channel, payload)
        return Response({"task_id": task_id.id, "detail": "Queued"}, status=status.HTTP_202_ACCEPTED)
