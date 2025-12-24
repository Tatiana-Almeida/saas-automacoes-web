from django.urls import path
from .views import me

urlpatterns = [
    path('api/users/me', me, name='users-me'),
]
