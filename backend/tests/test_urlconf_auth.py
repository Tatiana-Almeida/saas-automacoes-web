from django.urls import resolve


def test_auth_token_url_resolves():
    match = resolve("/api/v1/auth/token")
    # Ensure the named route exists and points to our token view
    assert match.view_name == "token_obtain_pair"
