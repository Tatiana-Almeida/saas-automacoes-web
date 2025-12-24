import pytest
from django.test import override_settings
from apps.auditing.tasks import export_audit_logs_to_elasticsearch


@pytest.mark.django_db
def test_export_task_disabled_returns_disabled():
    with override_settings(AUDIT_EXPORT_ENABLED=False, ELASTICSEARCH_URL='http://localhost:9200'):
        result = export_audit_logs_to_elasticsearch()
        assert result.get('status') == 'disabled'
