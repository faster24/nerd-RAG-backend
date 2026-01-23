import pytest
from fastapi.testclient import TestClient
from manage import app
from unittest.mock import patch, MagicMock
from core.middleware import verify_firebase_token

client = TestClient(app)


def test_admin_dashboard_access_granted():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": "admin"}}
    try:
        response = client.get("/api/v1/auth/admin/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to admin dashboard"}
    finally:
        app.dependency_overrides = {}


def test_admin_dashboard_access_denied_teacher():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": "teacher"}}
    try:
        response = client.get("/api/v1/auth/admin/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    finally:
        app.dependency_overrides = {}


def test_admin_dashboard_access_denied_student():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": "student"}}
    try:
        response = client.get("/api/v1/auth/admin/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}


def test_teacher_dashboard_access_granted_admin():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": "admin"}}
    try:
        response = client.get("/api/v1/auth/teacher/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to teacher dashboard"}
    finally:
        app.dependency_overrides = {}


def test_teacher_dashboard_access_granted_teacher():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": "teacher"}}
    try:
        response = client.get("/api/v1/auth/teacher/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200
    finally:
        app.dependency_overrides = {}


def test_teacher_dashboard_access_denied_student():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": "student"}}
    try:
        response = client.get("/api/v1/auth/teacher/dashboard", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}


def test_student_dashboard_access_all_roles():
    for role in ["admin", "teacher", "student"]:
        app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test", "custom_claims": {"role": role}}
        try:
            response = client.get("/api/v1/auth/student/dashboard", headers={"Authorization": "Bearer fake_token"})
            assert response.status_code == 200
            assert response.json() == {"message": "Welcome to student dashboard"}
        finally:
            app.dependency_overrides = {}


def test_get_current_user():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test_uid", "custom_claims": {"role": "admin"}}
    
    with patch('firebase_admin.auth.get_user') as mock_get_user:
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

        try:
            response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake_token"})
            assert response.status_code == 200
            data = response.json()
            assert data["uid"] == "test_uid"
            assert data["email"] == "test@example.com"
            assert data["role"] == "admin"
        finally:
            app.dependency_overrides = {}


def test_get_current_user_default_role():
    app.dependency_overrides[verify_firebase_token] = lambda: {"uid": "test_uid"}
    
    with patch('firebase_admin.auth.get_user') as mock_get_user:
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

        try:
            response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer fake_token"})
            assert response.status_code == 200
            data = response.json()
            assert data["role"] == "student"  # Default role
        finally:
            app.dependency_overrides = {}