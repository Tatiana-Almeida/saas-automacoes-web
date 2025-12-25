def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        # X-Forwarded-For may contain multiple IPs, client is first
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
