from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hashing():
    plain = "my-secret-password"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_tokens():
    subject = "user123"
    access_token = create_access_token(subject, extra_claims={"role": "admin"})
    assert isinstance(access_token, str)

    decoded = decode_token(access_token)
    assert decoded["sub"] == subject
    assert decoded["type"] == "access"
    assert decoded["role"] == "admin"

    refresh_token = create_refresh_token(subject)
    assert isinstance(refresh_token, str)

    decoded_refresh = decode_token(refresh_token)
    assert decoded_refresh["sub"] == subject
    assert decoded_refresh["type"] == "refresh"
