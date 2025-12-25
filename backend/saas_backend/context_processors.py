from django.conf import settings


def analytics(request):
    """Expose analytics configuration to templates."""
    return {
        "GA_TRACKING_ID": getattr(settings, "GA_TRACKING_ID", None),
    }
