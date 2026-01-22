import httpx
from typing import Dict, Any, Optional
from core.settings import settings
import logging

logger = logging.getLogger(__name__)


class FirebaseAuthClient:
    def __init__(self):
        self.api_key = settings.firebase_api_key
        self.base_url = f"https://identitytoolkit.googleapis.com/v1/accounts"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def sign_up_with_email_password(
        self, email: str, password: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}:signUp?key={self.api_key}"
        data = {"email": email, "password": password, "returnSecureToken": True}
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def sign_in_with_email_password(
        self, email: str, password: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}:signInWithPassword?key={self.api_key}"
        data = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
        response = await self.client.post(url, data=data)
        response.raise_for_status()
        return response.json()

    async def send_password_reset_email(self, email: str) -> Dict[str, Any]:
        url = f"{self.base_url}:sendOobCode?key={self.api_key}"
        data = {"requestType": "PASSWORD_RESET", "email": email}
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def verify_password_reset_code(
        self, oob_code: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}:resetPassword?key={self.api_key}"
        data = {"oobCode": oob_code}
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    async def confirm_password_reset(
        self, oob_code: str, new_password: str
    ) -> Dict[str, Any]:
        url = f"{self.base_url}:resetPassword?key={self.api_key}"
        data = {"oobCode": oob_code, "newPassword": new_password}
        response = await self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()


firebase_auth_client = FirebaseAuthClient()