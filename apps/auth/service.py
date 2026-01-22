from firebase_admin import auth as firebase_auth
from core.firebase_client import firebase_auth_client
from core.firebase import get_firebase_auth, initialize_firebase
from apps.users.schemas import UserCreate, UserLogin
import firebase_admin
import logging

logger = logging.getLogger(__name__)


class AuthService:
    def _check_firebase_available(self):
        try:
            if not firebase_admin._apps:
                initialize_firebase()

            if not firebase_admin._apps:
                return False

            return True
        except Exception as e:
            logger.error(f"Firebase availability check failed: {str(e)}")
            return False

    async def register_user(self, user_data: UserCreate):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured. Please set up Firebase credentials.")

        try:
            result = await firebase_auth_client.sign_up_with_email_password(
                email=user_data.email, password=user_data.password
            )

            firebase_user = firebase_auth.get_user(result["localId"])

            if user_data.display_name:
                firebase_auth.update_user(
                    firebase_user.uid, display_name=user_data.display_name
                )

            logger.info(f"User registered successfully: {user_data.email}")
            return {"firebase_user": firebase_user, "tokens": result}

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            raise

    async def login_user(self, user_data: UserLogin):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured. Please set up Firebase credentials.")

        try:
            result = await firebase_auth_client.sign_in_with_email_password(
                email=user_data.email, password=user_data.password
            )

            firebase_user = firebase_auth.get_user(result["localId"])

            logger.info(f"User logged in successfully: {user_data.email}")
            return {"firebase_user": firebase_user, "tokens": result}

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise

    async def refresh_tokens(self, refresh_token: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            result = await firebase_auth_client.refresh_token(refresh_token)
            logger.info("Token refreshed successfully")
            return result
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise

    async def logout_user(self, uid: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            firebase_auth.revoke_refresh_tokens(uid)
            logger.info(f"User logged out successfully: {uid}")
            return True
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise

    async def send_password_reset(self, email: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            await firebase_auth_client.send_password_reset_email(email)
            logger.info(f"Password reset email sent to: {email}")
            return True
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            raise

    async def verify_password_reset_code(self, oob_code: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            result = await firebase_auth_client.verify_password_reset_code(oob_code)
            return result
        except Exception as e:
            logger.error(f"Verify reset code error: {str(e)}")
            raise

    async def confirm_password_reset(self, oob_code: str, new_password: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            await firebase_auth_client.confirm_password_reset(
                oob_code=oob_code, new_password=new_password
            )
            logger.info("Password reset confirmed successfully")
            return True
        except Exception as e:
            logger.error(f"Confirm password reset error: {str(e)}")
            raise

    async def get_user_by_uid(self, uid: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            user = firebase_auth.get_user(uid)
            return user
        except Exception as e:
            logger.error(f"Get user error: {str(e)}")
            raise

    async def set_user_role(self, uid: str, role: str):
        if not self._check_firebase_available():
            raise Exception("Firebase authentication is not configured.")

        try:
            firebase_auth.set_custom_user_claims(uid, {"role": role})
            logger.info(f"Role set for user {uid}: {role}")
            return True
        except Exception as e:
            logger.error(f"Set role error: {str(e)}")
            raise


auth_service = AuthService()