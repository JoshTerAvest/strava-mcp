import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


class StravaClient:
    TOKEN_URL = "https://www.strava.com/oauth/token"
    API_BASE = "https://www.strava.com/api/v3"

    def __init__(self):
        self.client_id = os.getenv("STRAVA_CLIENT_ID")
        self.client_secret = os.getenv("STRAVA_CLIENT_SECRET")
        self.refresh_token = os.getenv("STRAVA_REFRESH_TOKEN")
        self.access_token = None
        self.expires_at = 0

    def _refresh_token(self):
        if time.time() < self.expires_at - 60:
            return
        resp = requests.post(
            self.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.expires_at = data["expires_at"]
        if data["refresh_token"] != self.refresh_token:
            self.refresh_token = data["refresh_token"]

    def _get(self, endpoint, params=None):
        self._refresh_token()
        resp = requests.get(
            f"{self.API_BASE}{endpoint}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

    def get_athlete(self):
        return self._get("/athlete")

    def get_athlete_stats(self, athlete_id):
        return self._get(f"/athletes/{athlete_id}/stats")

    def get_activities(self, per_page=10, **kwargs):
        params = {"per_page": per_page}
        params.update(kwargs)
        return self._get("/athlete/activities", params)

    def get_activity(self, activity_id):
        return self._get(f"/activities/{activity_id}")

    def get_activity_streams(
        self, activity_id, keys="heartrate,time,distance,altitude"
    ):
        return self._get(
            f"/activities/{activity_id}/streams",
            params={"keys": keys, "key_by_type": "true"},
        )

    def get_activity_laps(self, activity_id):
        return self._get(f"/activities/{activity_id}/laps")

    def get_activity_zones(self, activity_id):
        return self._get(f"/activities/{activity_id}/zones")

    def get_gear(self, gear_id):
        return self._get(f"/gear/{gear_id}")
