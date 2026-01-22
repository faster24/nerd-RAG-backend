import pytest
from fastapi.testclient import TestClient
from manage import app
from unittest.mock import patch, MagicMock

client = TestClient(app)


def test_admin_dashboard_access_granted():
    with patch('core.middleware.verify_firebase_token') as mock_verify:
        mock_verify.return_value = {"uid": "test", "custom_claims": {"role": "admin"}}
        response = client.get("/api/v1/auth/admin/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to admin dashboard"}


def test_admin_dashboard_access_denied_teacher():
    with patch('core.middleware.verify_firebase_token') as mock_verify:
        mock_verify.return_value = {"uid": "test", "custom_claims": {"role": "teacher"}}
        response = client.get("/api/v1/auth/admin/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]


def test_admin_dashboard_access_denied_student():
    with patch('core.middleware.verify_firebase_token') as mock_verify:
        mock_verify.return_value = {"uid": "test", "custom_claims": {"role": "student"}}
        response = client.get("/api/v1/auth/admin/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 403


def test_teacher_dashboard_access_granted_admin():
    with patch('core.middleware.verify_firebase_token') as mock_verify:
        mock_verify.return_value = {"uid": "test", "custom_claims": {"role": "admin"}}
        response = client.get("/api/v1/auth/teacher/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to teacher dashboard"}


def test_teacher_dashboard_access_granted_teacher():
    with patch('core.middleware.verify_firebase_token') as mock_verify:
        mock_verify.return_value = {"uid": "test", "custom_claims": {"role": "teacher"}}
        response = client.get("/api/v1/auth/teacher/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200


def test_teacher_dashboard_access_denied_student():
    with patch('core.middleware.verify_firebase_token') as mock_verify:
        mock_verify.return_value = {"uid": "test", "custom_claims": {"role": "student"}}
        response = client.get("/api/v1/auth/teacher/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 403


def test_student_dashboard_access_all_roles():
    for role in ["admin", "teacher", "student"]:
        with patch('core.middleware.verify_firebase_token') as mock_verify:
            mock_verify.return_value = {"uid": "test", "custom_claims": {"role": role}}
            response = client.get("/api/v1/auth/student/dashboard", headers={"Authorization": "Bearer fake_token"})
            assert response.status_code == 200
            assert response.json() == {"message": "Welcome to student dashboard"}


def test_get_current_user():
    with patch('core.middleware.verify_firebase_token') as mock_verify, \
         patch('firebase_admin.auth.get_user') as mock_get_user:
        mock_verify.return_value = {"uid": "test_uid", "custom_claims": {"role": "admin"}}

        mock_user = MagicMock()
        mock_user.uid = "test_uid"
        mock_user.email = "test@example.com"
        mock_user.email_verified = True
        mock_user.display_name = "Test User"
        mock_user.photo_url = None
        mock_user.provider_id = "password"
        mock_user.user_metadata.creation_timestamp = 1234567890
        mock_user.user_metadata.last_sign_in_timestamp = None

        mock_get_user.return_value = mock_user

        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "test_uid"
        assert data["email"] == "test@example.com"
        assert data["role"] == "admin"


def test_get_current_user_default_role():
    with patch('core.middleware.verify_firebase_token') as mock_verify, \
         patch('firebase_admin.auth.get_user') as mock_get_user:
        mock_verify.return_value = {"uid": "test_uid"}  # No custom_claims

        mock_user = MagicMock()
        mock_user.uid = "test_uid"
        mock_user.email = "test@example.com"
        mock_user.email_verified = True
        mock_user.display_name = "Test User"
        mock_user.photo_url = None
        mock_user.provider_id = "password"
        mock_user.user_metadata.creation_timestamp = 1234567890
        mock_user.user_metadata.last_sign_in_timestamp = None

        mock_get_user.return_value = mock_user

        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "student"  # Default role