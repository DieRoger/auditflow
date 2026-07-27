"""Locust Performance Test — AuditFlow API

Usage: locust -f scripts/locustfile.py --host http://localhost:8000
"""

from locust import HttpUser, task, between


class AuditFlowUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers = {"Content-Type": "application/json"}

    @task(10)
    def health_check(self):
        self.client.get("/health")

    @task(5)
    def list_agents(self):
        self.client.get("/api/v1/agents")

    @task(3)
    def list_documents(self):
        self.client.get("/api/v1/documents?project_id=demo")

    @task(1)
    def execute_planner(self):
        self.client.post("/api/v1/agents/planner_agent/execute", json={
            "inputs": {"audit_area": "Revenue Recognition"},
        })
