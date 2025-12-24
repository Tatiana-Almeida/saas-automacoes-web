from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasPermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Tenant
from .serializers import TenantCreateSerializer, TenantActionSerializer, TenantPlanUpdateSerializer
from apps.auditing.models import AuditLog


class TenantCreateView(APIView):
    required_permission = 'manage_tenants'
    permission_classes = [IsAuthenticated, HasPermission]

    @extend_schema(
        request=TenantCreateSerializer,
        responses={
            201: None,
        },
        tags=['tenants'],
        description=(
            'Cria um tenant e emite o evento TenantCreated. '\
            'Consumidores do evento podem executar ações assíncronas (provisionamento, notificações).'
        ),
        examples=[
            OpenApiExample(
                'Exemplo de requisição',
                value={
                    'name': 'Acme Corp',
                    'schema_name': 'acme',
                    'plan': 'pro'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Exemplo de resposta (201)',
                value={
                    'id': 123,
                    'name': 'Acme Corp',
                    'schema_name': 'acme',
                    'plan': 'pro',
                    'is_active': True
                },
                response_only=True,
            ),
            OpenApiExample(
                'Evento emitido',
                description='Payload do evento TenantCreated enviado à fila',
                value={
                    'name': 'TenantCreated',
                    'payload': {
                        'tenant_id': 123,
                        'tenant_schema': 'acme',
                        'name': 'Acme Corp'
                    }
                },
                response_only=True,
            ),
        ],
    )
    @swagger_auto_schema(
        operation_description='Cria um tenant',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, example='Acme Corp'),
                'schema_name': openapi.Schema(type=openapi.TYPE_STRING, example='acme'),
                'domain': openapi.Schema(type=openapi.TYPE_STRING, example='acme.local'),
                'plan': openapi.Schema(type=openapi.TYPE_STRING, example='pro'),
            },
            required=['name','schema_name']
        ),
        responses={
            201: openapi.Response('Created', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                    'name': openapi.Schema(type=openapi.TYPE_STRING, example='Acme Corp'),
                    'schema_name': openapi.Schema(type=openapi.TYPE_STRING, example='acme'),
                    'plan': openapi.Schema(type=openapi.TYPE_STRING, example='pro'),
                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                }
            ))
        }
    )
    def post(self, request):
        serializer = TenantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()
        # Emit TenantCreated event
        try:
            from apps.events.events import emit_event, TENANT_CREATED
            emit_event(TENANT_CREATED, {
                'tenant_id': tenant.id,
                'tenant_schema': tenant.schema_name,
                'name': tenant.name,
            })
        except Exception:
            pass
        return Response({
            'id': tenant.id,
            'name': tenant.name,
            'schema_name': tenant.schema_name,
            'plan': tenant.plan,
            'is_active': tenant.is_active,
        }, status=status.HTTP_201_CREATED)


class TenantActionView(APIView):
    required_permission = 'manage_tenants'
    permission_classes = [IsAuthenticated, HasPermission]

    @extend_schema(
        request=TenantActionSerializer,
        responses={200: None},
        tags=['tenants'],
        description=(
            'Executa ação administrativa no tenant (suspender/reativar) e registra auditoria via AuditLog.'
        ),
        examples=[
            OpenApiExample(
                'Suspender tenant - requisição',
                value={'action': 'suspend'},
                request_only=True,
            ),
            OpenApiExample(
                'Suspender tenant - resposta (200)',
                value={'id': 123, 'is_active': False},
                response_only=True,
            ),
            OpenApiExample(
                'Reativar tenant - requisição',
                value={'action': 'reactivate'},
                request_only=True,
            ),
            OpenApiExample(
                'Reativar tenant - resposta (200)',
                value={'id': 123, 'is_active': True},
                response_only=True,
            ),
        ],
    )
    @swagger_auto_schema(
        operation_description='Suspende ou reativa um tenant',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'action': openapi.Schema(type=openapi.TYPE_STRING, enum=['suspend','reactivate'])
            },
            required=['action']
        ),
        responses={
            200: openapi.Response('OK', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False)
                }
            )),
            404: openapi.Response('Not Found')
        }
    )
    def post(self, request, tenant_id):
        # Resolve tenant record from public schema before updating
        from django.db import connection
        prev = getattr(connection, 'schema_name', None)
        try:
            try:
                connection.set_schema_to_public()
            except Exception:
                pass

            exists = Tenant.objects.filter(id=tenant_id).exists()
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            try:
                if prev:
                    connection.set_schema(prev)
                else:
                    connection.set_schema_to_public()
            except Exception:
                pass
            return Response({'detail': 'Tenant não encontrado'}, status=status.HTTP_404_NOT_FOUND)
        finally:
            try:
                if prev:
                    connection.set_schema(prev)
                else:
                    connection.set_schema_to_public()
            except Exception:
                pass

        serializer = TenantActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data['action']

        if action == 'suspend':
            tenant.is_active = True and False  # explicit for clarity
            tenant.is_active = False
            try:
                from django.db import connection
                prev = getattr(connection, 'schema_name', None)
                try:
                    connection.set_schema_to_public()
                except Exception:
                    pass
                tenant.save(update_fields=['is_active'])
            finally:
                try:
                    if prev:
                        connection.set_schema(prev)
                    else:
                        connection.set_schema_to_public()
                except Exception:
                    pass
            try:
                AuditLog.objects.create(
                    user=getattr(request, 'user', None),
                    path=request.path,
                    method=request.method,
                    source='view',
                    action='suspend_tenant',
                    status_code=200,
                    tenant_schema=getattr(tenant, 'schema_name', None),
                    tenant_id=getattr(tenant, 'id', None),
                    ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
                )
            except Exception:
                pass
        elif action == 'reactivate':
            tenant.is_active = True
            try:
                from django.db import connection
                prev = getattr(connection, 'schema_name', None)
                try:
                    connection.set_schema_to_public()
                except Exception:
                    pass
                tenant.save(update_fields=['is_active'])
            finally:
                try:
                    if prev:
                        connection.set_schema(prev)
                    else:
                        connection.set_schema_to_public()
                except Exception:
                    pass
            try:
                AuditLog.objects.create(
                    user=getattr(request, 'user', None),
                    path=request.path,
                    method=request.method,
                    source='view',
                    action='reactivate_tenant',
                    status_code=200,
                    tenant_schema=getattr(tenant, 'schema_name', None),
                    tenant_id=getattr(tenant, 'id', None),
                    ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
                )
            except Exception:
                pass

        return Response({
            'id': tenant.id,
            'is_active': tenant.is_active,
        })


class TenantPlanUpdateView(APIView):
    required_permission = 'manage_tenants'
    permission_classes = [IsAuthenticated, HasPermission]

    @extend_schema(
        request=TenantPlanUpdateSerializer,
        responses={200: None},
        tags=['tenants'],
        description=(
            'Atualiza o plano do tenant e emite o evento PlanUpgraded. '\
            'Os limites diários e taxas de throttling passam a respeitar o novo plano.'
        ),
        examples=[
            OpenApiExample(
                'Exemplo de requisição',
                value={'plan': 'enterprise'},
                request_only=True,
            ),
            OpenApiExample(
                'Exemplo de resposta (200)',
                value={
                    'id': 123,
                    'name': 'Acme Corp',
                    'schema_name': 'acme',
                    'plan': 'enterprise',
                    'plan_ref': 'enterprise'
                },
                response_only=True,
            ),
            OpenApiExample(
                'Evento emitido',
                description='Payload do evento PlanUpgraded enviado à fila',
                value={
                    'name': 'PlanUpgraded',
                    'payload': {
                        'tenant_id': 123,
                        'tenant_schema': 'acme',
                        'plan': 'enterprise'
                    }
                },
                response_only=True,
            ),
        ],
    )
    @swagger_auto_schema(
        operation_description='Atualiza o plano do tenant',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'plan': openapi.Schema(type=openapi.TYPE_STRING, example='enterprise')
            },
            required=['plan']
        ),
        responses={
            200: openapi.Response('OK', openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=123),
                    'name': openapi.Schema(type=openapi.TYPE_STRING, example='Acme Corp'),
                    'schema_name': openapi.Schema(type=openapi.TYPE_STRING, example='acme'),
                    'plan': openapi.Schema(type=openapi.TYPE_STRING, example='enterprise'),
                    'plan_ref': openapi.Schema(type=openapi.TYPE_STRING, example='enterprise')
                }
            )),
            400: openapi.Response('Bad Request'),
            404: openapi.Response('Not Found')
        }
    )
    def post(self, request, tenant_id):
        try:
            from django.db import connection
            prev = getattr(connection, 'schema_name', None)
            try:
                connection.set_schema_to_public()
            except Exception:
                pass
            try:
                tenant = Tenant.objects.get(id=tenant_id)
            finally:
                try:
                    if prev:
                        connection.set_schema(prev)
                    else:
                        connection.set_schema_to_public()
                except Exception:
                    pass
        except Tenant.DoesNotExist:
            return Response({'detail': 'Tenant não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        serializer = TenantPlanUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan_code = serializer.validated_data['plan']

        # Link tenant.plan and tenant.plan_ref
        from .models import Plan
        try:
            plan_obj = Plan.objects.get(code=plan_code)
        except Plan.DoesNotExist:
            return Response({'detail': 'Plano não encontrado'}, status=status.HTTP_400_BAD_REQUEST)

        tenant.plan = plan_code
        tenant.plan_ref = plan_obj
        # Ensure we save in the public schema (django-tenants requires saving
        # tenant model from public schema or from the tenant's own schema).
        try:
            from django.db import connection
            prev = getattr(connection, 'schema_name', None)
            try:
                connection.set_schema_to_public()
            except Exception:
                pass
            tenant.save(update_fields=['plan', 'plan_ref'])
        finally:
            try:
                if prev:
                    connection.set_schema(prev)
                else:
                    connection.set_schema_to_public()
            except Exception:
                pass

        try:
            AuditLog.objects.create(
                user=getattr(request, 'user', None),
                path=request.path,
                method=request.method,
                source='view',
                action='plan_change',
                status_code=200,
                tenant_schema=getattr(tenant, 'schema_name', None),
                tenant_id=getattr(tenant, 'id', None),
                ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR'),
            )
        except Exception:
            pass

        # Emit PlanUpgraded event
        try:
            from apps.events.events import emit_event, PLAN_UPGRADED
            emit_event(PLAN_UPGRADED, {
                'tenant_id': tenant.id,
                'tenant_schema': tenant.schema_name,
                'plan': plan_code,
            })
        except Exception:
            pass

        return Response({
            'id': tenant.id,
            'name': tenant.name,
            'schema_name': tenant.schema_name,
            'plan': tenant.plan,
            'plan_ref': plan_obj.code,
        })

    @extend_schema(
        summary="Tenant plan detail",
        tags=['tenants'],
        description=(
            'Retorna o plano efetivo do tenant e limites resolvidos. '\
            'Quando `plan_ref.daily_limits` estiver definido, tem precedência sobre as configurações globais.'
        ),
        examples=[
            OpenApiExample(
                'Exemplo de resposta (200)',
                value={
                    'id': 123,
                    'name': 'Acme Corp',
                    'schema_name': 'acme',
                    'plan': 'pro',
                    'plan_ref': 'pro',
                    'daily_limits': {
                        'emails_per_day': 10000,
                        'sms_per_day': 2000
                    },
                    'throttle_rates': {
                        'burst': '50/min',
                        'sustained': '1000/day'
                    }
                },
                response_only=True,
            )
        ],
    )
    def get(self, request, tenant_id):
        try:
            tenant = Tenant.objects.get(id=tenant_id)
        except Tenant.DoesNotExist:
            return Response({'detail': 'Tenant não encontrado'}, status=status.HTTP_404_NOT_FOUND)

        # Resolve plan code preferindo plan_ref
        plan_obj = getattr(tenant, 'plan_ref', None)
        plan_code = getattr(plan_obj, 'code', None) or getattr(tenant, 'plan', 'free')

        # Daily limits: prefer model-based overrides
        from django.conf import settings
        daily_limits = None
        try:
            dl = getattr(plan_obj, 'daily_limits', None)
            if isinstance(dl, dict):
                daily_limits = dl
        except Exception:
            daily_limits = None
        if daily_limits is None:
            daily_limits = getattr(settings, 'TENANT_PLAN_DAILY_LIMITS', {}).get(plan_code, {})

        throttle_rates = getattr(settings, 'TENANT_PLAN_THROTTLE_RATES', {}).get(plan_code, {})

        return Response({
            'id': tenant.id,
            'name': tenant.name,
            'schema_name': tenant.schema_name,
            'plan': plan_code,
            'plan_ref': getattr(plan_obj, 'code', None),
            'daily_limits': daily_limits,
            'throttle_rates': throttle_rates,
        })
