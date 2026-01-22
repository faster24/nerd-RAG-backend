from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth as firebase_auth
from core.settings import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def verify_firebase_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = None,
) -> dict:
    try:
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authentication credentials provided",
            )

        try:
            import firebase_admin
            if not firebase_admin._apps:
                raise Exception("Not initialized")
            firebase_auth.get_user("test")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Firebase authentication is not configured",
            )

        token = credentials.credentials
        decoded_token = firebase_auth.verify_id_token(token)

        request.state.user = decoded_token
        return decoded_token
    except HTTPException:
        raise
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )


def setup_cors_middleware(app):
    origins = settings.allowed_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_middleware(app):
    setup_cors_middleware(app)
    logger.info("CORS middleware configured")