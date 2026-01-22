from pydantic import BaseModel


class User(BaseModel):
    uid: str
    email: str
    email_verified: bool
    display_name: str | None = None
    photo_url: str | None = None
    provider_id: str
    created_at: str
    last_sign_in_at: str | None = None
    role: str | None = None

    @classmethod
    def from_firebase_user(cls, firebase_user, role=None):
        return cls(
            uid=firebase_user.uid,
            email=firebase_user.email,
            email_verified=firebase_user.email_verified,
            display_name=firebase_user.display_name,
            photo_url=firebase_user.photo_url,
            provider_id=firebase_user.provider_id,
            created_at=str(firebase_user.user_metadata.creation_timestamp),
            last_sign_in_at=str(firebase_user.user_metadata.last_sign_in_timestamp)
            if firebase_user.user_metadata.last_sign_in_timestamp
            else None,
            role=role,
        )