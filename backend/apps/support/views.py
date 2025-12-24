from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import SupportTicket
from .serializers import SupportTicketSerializer, SupportTicketCreateSerializer, SupportTicketResponseSerializer


class SupportCreatePermission(permissions.AllowAny):
    pass


class SupportViewSet(viewsets.ModelViewSet):
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'create':
            return SupportTicketCreateSerializer
        if self.action in ('respond', 'partial_update'):
            return SupportTicketResponseSerializer
        return SupportTicketSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        ticket = self.get_object()
        serializer = SupportTicketResponseSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SupportTicketSerializer(ticket).data)
