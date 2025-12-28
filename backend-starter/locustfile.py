from locust import HttpUser, between, task


class SaaSUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def list_public_products(self):
        self.client.get("/api/products/public")

    @task(1)
    def health(self):
        self.client.get("/")


# To run:
# locust -f locustfile.py --host=http://localhost:8000
