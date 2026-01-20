import pytest

from validator import EmailValidator


@pytest.fixture()
def validator() -> EmailValidator:
    return EmailValidator()


@pytest.mark.parametrize(
    "email",
    [
        "user@gmail.com",
        "first.last@outlook.com",
        "test123@yahoo.com",
        "name+tag@hotmail.com",
        "person@icloud.com",
        "user@qq.com",
        "example@163.com",
        "sample@126.com",
        "hello@sina.com",
        "foo@foxmail.com",
        "User@GMAIL.COM",
    ],
)
def test_valid_emails(validator: EmailValidator, email: str) -> None:
    is_valid, error = validator.validate(email)
    assert is_valid is True
    assert error == ""


@pytest.mark.parametrize(
    "email",
    [
        "plainaddress",
        "missing-at-symbol.com",
        "user@",
        "@domain.com",
        "user@domain",
        "user@domain.c",
        "user domain@gmail.com",
        "user@@gmail.com",
    ],
)
def test_invalid_format_emails(validator: EmailValidator, email: str) -> None:
    is_valid, error = validator.validate(email)
    assert is_valid is False
    assert error == "Invalid email format."


@pytest.mark.parametrize(
    "email",
    [
        "user@aol.com",
        "test@proton.me",
        "person@example.org",
    ],
)
def test_unsupported_domain_emails(validator: EmailValidator, email: str) -> None:
    is_valid, error = validator.validate(email)
    assert is_valid is False
    assert error == "Email domain is not supported."


@pytest.mark.parametrize(
    "email",
    [
        "",
        "   ",
        None,
    ],
)
def test_edge_cases(validator: EmailValidator, email: object) -> None:
    is_valid, error = validator.validate(email)  # type: ignore[arg-type]
    assert is_valid is False
    assert error == "Invalid email format."
