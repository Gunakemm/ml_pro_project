import json

from locust import HttpUser, between, task

GOOD_PAYLOAD = {}
try:
    # Ищем good.json в текущей директории
    with open("good.json", encoding="utf-8") as f:
        GOOD_PAYLOAD = json.load(f)
except FileNotFoundError:
    print("Файл good.json не найден в текущей директории")


class ViralSongUser(HttpUser):

    wait_time = between(1, 3)

    @task(10)
    def health_check(self):
        self.client.get("/health")

    @task(20)
    def predict_song(self):
        headers = {"Content-Type": "application/json"}

        with self.client.post("/v1/predict", json=GOOD_PAYLOAD, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}: {response.text}")