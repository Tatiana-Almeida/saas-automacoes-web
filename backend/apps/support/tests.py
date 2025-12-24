from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.support.models import SupportTicket


class SupportTicketAPITest(APITestCase):
    def test_create_ticket_anonymous(self):
        url = reverse('support-ticket-list')
        data = {'email': 'user@example.com', 'subject': 'Help', 'message': 'I need help'}
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupportTicket.objects.count(), 1)
