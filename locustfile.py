
from locust import HttpUser, task, between, events
import time

class MallUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(5)
    def shop(self):
        self.client.get("/shop", name="/shop")

    @task(3)
    def health(self):
        self.client.get("/api/health", name="/api/health")

    @task(1)
    def product(self):
        self.client.get("/shop/p/sticker-box", name="/shop/p/[slug]")
