import pytest
from apps.auditing import tasks as audit_tasks
from django.test import override_settings


@pytest.mark.django_db
def test_build_headers_basic_auth(monkeypatch):
    with override_settings(
        ELASTICSEARCH_USERNAME="u",
        ELASTICSEARCH_PASSWORD="p",
        ELASTICSEARCH_API_KEY=None,
    ):
        headers = audit_tasks._build_es_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")


@pytest.mark.django_db
def test_build_headers_api_key(monkeypatch):
    with override_settings(
        ELASTICSEARCH_USERNAME=None,
        ELASTICSEARCH_PASSWORD=None,
        ELASTICSEARCH_API_KEY="abc123==",
    ):
        headers = audit_tasks._build_es_headers()
        assert headers["Authorization"] == "ApiKey abc123=="


@pytest.mark.django_db
def test_retry_on_failure_then_success(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, payload, headers=None):
        calls["n"] += 1
        # First attempt fails, second succeeds
        if calls["n"] == 1:
            return 503, "unavailable"
        return 200, '{"errors":false}'

    def fake_sleep(_):
        return None

    monkeypatch.setattr(audit_tasks, "_es_post_bulk", fake_post)
    monkeypatch.setattr(audit_tasks.time, "sleep", fake_sleep)

    with override_settings(
        AUDIT_EXPORT_ENABLED=True, ELASTICSEARCH_URL="http://localhost:9200"
    ):
        # Also need at least one log to export; we patch query to produce a fake log
        class Obj:
            def __init__(self):
                from django.utils import timezone

                self.id = 1
                self.user_id = None
                self.user = None
                self.path = "/x"
                self.method = "GET"
                self.source = "test"
                self.action = "request"
                self.status_code = 200
                self.tenant_schema = "t"
                self.tenant_id = 1
                self.ip_address = "127.0.0.1"
                self.created_at = timezone.now()

        # Patch queryset to return one object
        class QS(list):
            def order_by(self, *args, **kwargs):
                return self

            def __getitem__(self, sl):
                return self

        def fake_filter(**kwargs):
            return QS([Obj()])

        from apps.auditing import models as audit_models

        monkeypatch.setattr(
            audit_models.AuditLog.objects,
            "filter",
            staticmethod(lambda **kw: fake_filter(**kw)),
        )

        result = audit_tasks.export_audit_logs_to_elasticsearch(
            max_attempts=2, base_backoff_seconds=0.01
        )
        assert result.get("status") == "ok"
        assert calls["n"] == 2
