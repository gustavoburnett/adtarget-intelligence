"""Synthetic native identity; never enabled in application code."""
import time

CONFIG = {"redirect_uri": "http://localhost:8501/oauth2callback", "cookie_secret": "OFFLINE" * 8,
          "google": {"client_id": "OFFLINE_CLIENT", "client_secret": "OFFLINE_SECRET",
                     "server_metadata_url": "https://accounts.google.com/.well-known/openid-configuration"}}

class Identity(dict):
    @property
    def is_logged_in(self):
        return self.get("is_logged_in", False)


def identity(**changes):
    return Identity({"is_logged_in": True, "iss": "https://accounts.google.com",
                     "aud": "OFFLINE_CLIENT", "sub": "offline-employee",
                     "hd": "adtarget.com.br", "email_verified": True,
                     "exp": time.time() + 3600, **changes})
