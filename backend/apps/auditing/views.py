from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasPermission
from rest_framework.generics import ListAPIView
from rest_framework.filters import OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework import status
from drf_spectacular.utils import extend_schema
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .models import AuditLog, AuditRetentionPolicy
from .serializers import AuditLogSerializer, AuditRetentionPolicySerializer


class AuditLogListView(ListAPIView):
    # Require explicit RBAC permission to view audit logs in APIs.
    required_permission = 'view_audit_logs'
    permission_classes = [IsAuthenticated, HasPermission]
    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.select_related('user').order_by('-created_at')
    filter_backends = [OrderingFilter]
    ordering_fields = ['created_at', 'method', 'path', 'user']
    ordering = ['-created_at']

    @swagger_auto_schema(
        operation_summary="List audit logs",
        manual_parameters=[
            openapi.Parameter('user_id', openapi.IN_QUERY, description='Filter by user id', type=openapi.TYPE_STRING),
            openapi.Parameter('method', openapi.IN_QUERY, description='HTTP method', type=openapi.TYPE_STRING),
            openapi.Parameter('source', openapi.IN_QUERY, description='Source system/service', type=openapi.TYPE_STRING),
            openapi.Parameter('action', openapi.IN_QUERY, description='Action name', type=openapi.TYPE_STRING),
            openapi.Parameter('tenant_schema', openapi.IN_QUERY, description='Tenant schema', type=openapi.TYPE_STRING),
            openapi.Parameter('status_code', openapi.IN_QUERY, description='HTTP status code', type=openapi.TYPE_INTEGER),
            openapi.Parameter('path_contains', openapi.IN_QUERY, description='Path contains substring', type=openapi.TYPE_STRING),
            openapi.Parameter('created_after', openapi.IN_QUERY, description='ISO datetime filter (gte)', type=openapi.TYPE_STRING),
            openapi.Parameter('created_before', openapi.IN_QUERY, description='ISO datetime filter (lte)', type=openapi.TYPE_STRING),
            openapi.Parameter('ordering', openapi.IN_QUERY, description='Ordering fields', type=openapi.TYPE_STRING),
        ],
        responses={200: AuditLogSerializer(many=True)},
        tags=['auditing']
    )
    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        method = self.request.query_params.get('method')
        source = self.request.query_params.get('source')
        action = self.request.query_params.get('action')
        tenant_schema = self.request.query_params.get('tenant_schema')
        status_code = self.request.query_params.get('status_code')
        path_contains = self.request.query_params.get('path_contains')
        created_after = self.request.query_params.get('created_after')
        created_before = self.request.query_params.get('created_before')

        if user_id:
            qs = qs.filter(user_id=user_id)
        if method:
            qs = qs.filter(method__iexact=method)
        if source:
            qs = qs.filter(source__iexact=source)
        if action:
            qs = qs.filter(action__iexact=action)
        if tenant_schema:
            qs = qs.filter(tenant_schema__iexact=tenant_schema)
        if status_code:
            try:
                qs = qs.filter(status_code=int(status_code))
            except Exception:
                pass
        if path_contains:
            qs = qs.filter(path__icontains=path_contains)
        if created_after:
            dt = parse_datetime(created_after)
            if dt:
                qs = qs.filter(created_at__gte=dt)
        if created_before:
            dt = parse_datetime(created_before)
            if dt:
                qs = qs.filter(created_at__lte=dt)
        return qs


class AuditRetentionPolicyListCreateView(APIView):
    required_permission = 'manage_auditing'
    permission_classes = [IsAuthenticated, HasPermission]

    @extend_schema(responses=AuditRetentionPolicySerializer, tags=['auditing'])
    @swagger_auto_schema(
        operation_summary="List retention policies",
        responses={200: AuditRetentionPolicySerializer(many=True)},
        tags=['auditing']
    )
    def get(self, request):
        qs = AuditRetentionPolicy.objects.all().order_by('tenant_schema')
        ser = AuditRetentionPolicySerializer(qs, many=True)
        return JsonResponse(ser.data, safe=False)

    @extend_schema(request=AuditRetentionPolicySerializer, responses=AuditRetentionPolicySerializer, tags=['auditing'])
    @swagger_auto_schema(
        operation_summary="Create retention policy",
        request_body=AuditRetentionPolicySerializer,
        responses={201: AuditRetentionPolicySerializer},
        tags=['auditing']
    )
    def post(self, request):
        ser = AuditRetentionPolicySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return JsonResponse(AuditRetentionPolicySerializer(obj).data, status=201)


class AuditRetentionPolicyDetailView(APIView):
    required_permission = 'manage_auditing'
    permission_classes = [IsAuthenticated, HasPermission]

    @extend_schema(request=AuditRetentionPolicySerializer, responses=AuditRetentionPolicySerializer, tags=['auditing'])
    @swagger_auto_schema(
        operation_summary="Update retention policy",
        request_body=AuditRetentionPolicySerializer,
        responses={200: AuditRetentionPolicySerializer, 404: 'Policy not found'},
        tags=['auditing']
    )
    def put(self, request, policy_id):
        try:
            obj = AuditRetentionPolicy.objects.get(id=policy_id)
        except AuditRetentionPolicy.DoesNotExist:
            return Response({'detail': 'Policy not found'}, status=status.HTTP_404_NOT_FOUND)
        ser = AuditRetentionPolicySerializer(instance=obj, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return JsonResponse(AuditRetentionPolicySerializer(obj).data)

    @extend_schema(responses={204: None}, tags=['auditing'])
    @swagger_auto_schema(
        operation_summary="Delete retention policy",
        responses={204: 'Deleted', 404: 'Policy not found'},
        tags=['auditing']
    )
    def delete(self, request, policy_id):
        try:
            obj = AuditRetentionPolicy.objects.get(id=policy_id)
        except AuditRetentionPolicy.DoesNotExist:
            return Response({'detail': 'Policy not found'}, status=status.HTTP_404_NOT_FOUND)
        obj.delete()
        return JsonResponse({}, status=204)
