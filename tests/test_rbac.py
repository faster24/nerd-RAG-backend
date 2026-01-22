import pytest
from core.auth_dependencies import get_user_role, check_role_access, Role


def test_get_user_role_student():
    token = {"custom_claims": {"role": "student"}}
    assert get_user_role(token) == Role.STUDENT


def test_get_user_role_teacher():
    token = {"custom_claims": {"role": "teacher"}}
    assert get_user_role(token) == Role.TEACHER


def test_get_user_role_admin():
    token = {"custom_claims": {"role": "admin"}}
    assert get_user_role(token) == Role.ADMIN


def test_get_user_role_default():
    token = {}
    assert get_user_role(token) == Role.STUDENT


def test_get_user_role_invalid():
    token = {"custom_claims": {"role": "invalid"}}
    assert get_user_role(token) == Role.STUDENT


def test_check_role_access_admin():
    assert check_role_access(Role.ADMIN, Role.ADMIN)
    assert check_role_access(Role.ADMIN, Role.TEACHER)
    assert check_role_access(Role.ADMIN, Role.STUDENT)


def test_check_role_access_teacher():
    assert not check_role_access(Role.TEACHER, Role.ADMIN)
    assert check_role_access(Role.TEACHER, Role.TEACHER)
    assert check_role_access(Role.TEACHER, Role.STUDENT)


def test_check_role_access_student():
    assert not check_role_access(Role.STUDENT, Role.ADMIN)
    assert not check_role_access(Role.STUDENT, Role.TEACHER)
    assert check_role_access(Role.STUDENT, Role.STUDENT)