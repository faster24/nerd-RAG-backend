import firebase_admin
from firebase_admin import credentials, auth
import os
import logging

logger = logging.getLogger(__name__)


def initialize_firebase():
    try:
        if firebase_admin._apps:
            logger.info("Firebase app already initialized")
            return firebase_admin.get_app()

        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_file_dir)
        cred_path = os.path.join(project_root, 'firebase_credential.json')

        if not os.path.exists(cred_path):
            logger.warning(f"Firebase credentials file not found at: {cred_path}")
            logger.warning("Place firebase_credential.json in the project root to enable Firebase features.")
            return None

        logger.info(f"Loading Firebase credentials from: {cred_path}")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase initialized successfully with service account key")
        return firebase_admin.get_app()
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        logger.warning("Firebase features will be disabled. Check your firebase_credential.json file.")
        return None


def get_firebase_auth():
    return auth