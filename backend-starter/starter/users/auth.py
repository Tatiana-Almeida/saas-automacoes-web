import logging
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework import status


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    # Force email as the login field in the payload
    username_field = 'email'

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = {
            'id': self.user.id,
            'email': getattr(self.user, 'email', ''),
            'role': getattr(self.user, 'role', ''),
            'is_staff': getattr(self.user, 'is_staff', False),
        }
        return data


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        logger = logging.getLogger('security')
        try:
            response = super().post(request, *args, **kwargs)
            logger.info('login_succeeded', extra={
                'user': getattr(getattr(response, 'data', {}).get('user', {}), 'id', None) if hasattr(response, 'data') else None,
                'ip': request.META.get('REMOTE_ADDR'),
                'ua': request.META.get('HTTP_USER_AGENT'),
            })
            return response
        except Exception as exc:
            logger.warning('login_failed', extra={
                'email': request.data.get('email'),
                'ip': request.META.get('REMOTE_ADDR'),
                'ua': request.META.get('HTTP_USER_AGENT'),
                'error': str(exc),
            })
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
