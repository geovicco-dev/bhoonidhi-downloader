"""Email OTP is a second login step, not a failure.

VALIDATE_LOGIN can return ``MSG: Login OTP has been mailed...`` with a
``pending_token`` and no JWT. The portal's own login.html then calls
VERIFY_OTP. Tests mock the portal so they run offline.
"""

from __future__ import annotations

import json
from urllib.parse import unquote

import pytest

from bhoonidhi_downloader.core.auth import command as cmd
from bhoonidhi_downloader.core.auth.client import AuthManager
from bhoonidhi_downloader.exceptions import BhoonidhiAuthError, BhoonidhiValidationError
from bhoonidhi_downloader.schemas import SessionSchema
from bhoonidhi_downloader.sdk.client import BhoonidhiClient

OTP_MAILED = (
    "Login OTP has been mailed to your registered email id (txxxxfb@gmail.com). "
    "Please check the spam/junk folders to ensure it is not missed."
)
PENDING = "pending-token-abc+/=xyz"
JWT = "header.payload.sig"


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def _am() -> AuthManager:
    return AuthManager(cfg=SessionSchema(username="demo-user", password="secret"))


def _results(msg="", jwt="", **extra):
    row = {"MSG": msg, "JWT": jwt, "USERID": "U1", "USEREMAIL": "u@example.com"}
    row.update(extra)
    return {"Results": [row]}


def test_password_only_login_still_works(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        assert payload["action"] == "VALIDATE_LOGIN"
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    session = _am().login()
    assert session.jwt == JWT
    assert session.username == "demo-user"
    assert session.userId == "U1"


def test_otp_mailed_without_code_is_actionable_error_not_raw_failure(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        return _FakeResponse(_results(msg=OTP_MAILED, jwt="", pending_token=PENDING))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    with pytest.raises(BhoonidhiAuthError, match="enter the 6-digit"):
        _am().login()


def test_otp_prompt_completes_verify(monkeypatch):
    calls: list[dict] = []

    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        calls.append(payload)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        assert action == "VERIFY_OTP"
        assert unquote(payload["otp"]) == "654321"
        assert unquote(payload["selProds"]) == PENDING
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return "654321"

    session = _am().login(otp_prompt=prompt)
    assert session.jwt == JWT
    assert prompts == [OTP_MAILED]
    assert len(calls) == 2


def test_otp_kwarg_skips_prompt(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    session = _am().login(otp="111222", otp_prompt=lambda m: pytest.fail("prompted"))
    assert session.jwt == JWT


def test_otp_must_be_six_digits(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        return _FakeResponse(_results(msg=OTP_MAILED, jwt="", pending_token=PENDING))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    with pytest.raises(BhoonidhiValidationError, match="6 digits"):
        _am().login(otp="12ab")


def test_verify_otp_http_417(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(status_code=417, text="Invalid session")

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    with pytest.raises(BhoonidhiAuthError, match="Invalid session"):
        _am().login(otp="123456")


def test_verify_otp_rejected_without_jwt(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(_results(msg="Incorrect OTP", jwt=""))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    with pytest.raises(BhoonidhiAuthError, match="Incorrect OTP"):
        _am().login(otp="123456")


def test_missing_pending_token(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        return _FakeResponse(_results(msg=OTP_MAILED, jwt=""))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    with pytest.raises(BhoonidhiAuthError, match="pending_token"):
        _am().login(otp="123456")


def test_http_400_still_fails(monkeypatch):
    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post",
        lambda *a, **k: _FakeResponse(status_code=400, text="bad"),
    )
    with pytest.raises(BhoonidhiAuthError, match="Status code: 400"):
        _am().login()


def test_empty_results(monkeypatch):
    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post",
        lambda *a, **k: _FakeResponse({"Results": []}),
    )
    with pytest.raises(BhoonidhiAuthError, match="empty response"):
        _am().login()


def test_other_msg_without_jwt_still_fails(monkeypatch):
    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post",
        lambda *a, **k: _FakeResponse(_results(msg="Invalid credentials", jwt="")),
    )
    with pytest.raises(BhoonidhiAuthError, match="Invalid credentials"):
        _am().login()


def test_run_login_validates_session_after_otp(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_SESSION":
            return _FakeResponse(_results(jwt=JWT, msg="NEW"))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    session = cmd.run_login("demo-user", "secret", save=False, otp="999888")
    assert session.jwt == JWT


def test_sdk_login_forwards_otp(monkeypatch):
    seen: dict[str, str | None] = {}

    def fake_run_login(username, password, save=True, *, otp=None, otp_prompt=None):
        seen["otp"] = otp
        return SessionSchema(username=username, jwt=JWT)

    monkeypatch.setattr(cmd, "run_login", fake_run_login)
    # Patch the alias the SDK imported
    import bhoonidhi_downloader.sdk.client as sdk_client

    monkeypatch.setattr(sdk_client._auth, "run_login", fake_run_login)
    client = BhoonidhiClient()
    client.login("demo-user", "secret", otp="121212")
    assert seen["otp"] == "121212"
    assert client.is_authenticated


# --------------------------------------------------------------------------
# otp_prompt retries: a wrong or malformed code re-prompts against the same
# pending_token, up to 3 attempts, instead of forcing a whole new login.
# --------------------------------------------------------------------------


def test_wrong_otp_then_right_otp_succeeds_same_pending_token(monkeypatch):
    calls: list[dict] = []
    verify_attempts = {"count": 0}

    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        calls.append(payload)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        assert action == "VERIFY_OTP"
        assert unquote(payload["selProds"]) == PENDING
        verify_attempts["count"] += 1
        if verify_attempts["count"] == 1:
            return _FakeResponse(
                _results(msg="Invalid or expired code. Attempts remaining : 5", jwt="")
            )
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []
    codes = iter(["111111", "654321"])

    def prompt(message: str) -> str:
        prompts.append(message)
        return next(codes)

    session = _am().login(otp_prompt=prompt)
    assert session.jwt == JWT
    assert len(prompts) == 2
    assert prompts[0] == OTP_MAILED
    assert "Attempts remaining" in prompts[1]

    validate_calls = [
        c for c in calls if unquote(str(c.get("action", ""))) == "VALIDATE_LOGIN"
    ]
    assert len(validate_calls) == 1, "a wrong OTP must not trigger a fresh login"


def test_wrong_otps_stop_when_portal_reports_zero_remaining(monkeypatch):
    """The retry bound comes from the portal's own countdown, not a number
    this client picks -- keep prompting while it reports attempts left, stop
    the moment it reports none, whatever that count turns out to be.
    """
    verify_attempts = {"count": 0}
    remaining_sequence = iter([2, 1, 0])  # portal's own countdown

    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        verify_attempts["count"] += 1
        remaining = next(remaining_sequence)
        return _FakeResponse(
            _results(
                msg=f"Invalid or expired code. Attempts remaining : {remaining}",
                jwt="",
            )
        )

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return "000000"

    with pytest.raises(BhoonidhiAuthError, match="after 3 attempts"):
        _am().login(otp_prompt=prompt)
    assert verify_attempts["count"] == 3, "must stop exactly when 0 remain, not before"
    assert len(prompts) == 3


def test_unparseable_rejection_falls_back_to_safety_cap(monkeypatch):
    """If a rejection's wording can't be parsed for a count at all, retrying
    still can't run forever -- it's bounded by the safety cap, not the
    portal's countdown (which isn't available here).
    """

    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(_results(msg="Incorrect OTP", jwt=""))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return "000000"

    with pytest.raises(BhoonidhiAuthError, match="after 10 attempts"):
        _am().login(otp_prompt=prompt)
    assert len(prompts) == 10


def test_malformed_otp_from_prompt_is_retried_not_fatal(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    codes = iter(["12ab", "654321"])  # first malformed, second valid

    def prompt(message: str) -> str:
        return next(codes)

    session = _am().login(otp_prompt=prompt)
    assert session.jwt == JWT


def test_otp_kwarg_wrong_code_fails_without_retry_even_if_prompt_given(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(_results(msg="Incorrect OTP", jwt=""))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    with pytest.raises(BhoonidhiAuthError, match="Incorrect OTP"):
        _am().login(
            otp="000000",
            otp_prompt=lambda m: pytest.fail("otp= must not fall back to prompting"),
        )


def test_wrong_otp_via_http_417_is_still_retried(monkeypatch):
    """Live-observed shape: the portal rejects a wrong-but-well-formed OTP via
    HTTP 417 with plain text (not HTTP 200 + JSON MSG). That must retry the
    same as the 200+MSG rejection path does -- the transport the portal used
    to say "wrong code" isn't the caller's concern.
    """
    calls: list[dict] = []
    verify_attempts = {"count": 0}

    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        calls.append(payload)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        assert action == "VERIFY_OTP"
        verify_attempts["count"] += 1
        if verify_attempts["count"] == 1:
            return _FakeResponse(
                status_code=417, text="Invalid or expired code. Attempts remaining : 5"
            )
        return _FakeResponse(_results(msg="ENABLED SERVICES: demo-user", jwt=JWT))

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []
    codes = iter(["111111", "654321"])

    def prompt(message: str) -> str:
        prompts.append(message)
        return next(codes)

    session = _am().login(otp_prompt=prompt)
    assert session.jwt == JWT
    assert len(prompts) == 2, "must re-prompt after a 417 wrong-code rejection"
    assert "Attempts remaining" in prompts[1]

    validate_calls = [
        c for c in calls if unquote(str(c.get("action", ""))) == "VALIDATE_LOGIN"
    ]
    assert len(validate_calls) == 1, "a 417 wrong OTP must not trigger a fresh login"


def test_http_417_session_error_is_not_retried(monkeypatch):
    """A 417 with no "attempts remaining" wording (e.g. a stale pending_token
    or rate limit) is a harder failure than a wrong digit -- retrying it the
    same way won't help, so it must not consume the retry loop's guesses.
    """

    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(status_code=417, text="Please wait before resending")

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return "123456"

    with pytest.raises(BhoonidhiAuthError, match="Please wait before resending"):
        _am().login(otp_prompt=prompt)
    assert len(prompts) == 1, "a non-code 417 must not be retried"


def test_http_417_during_verification_is_not_retried(monkeypatch):
    def fake_post(url, data=None, headers=None, timeout=None):
        payload = json.loads(data)
        action = unquote(str(payload.get("action", "")))
        if action == "VALIDATE_LOGIN":
            return _FakeResponse(
                _results(msg=OTP_MAILED, jwt="", pending_token=PENDING)
            )
        return _FakeResponse(status_code=417, text="Please wait before resending")

    monkeypatch.setattr(
        "bhoonidhi_downloader.core.auth.client.requests.post", fake_post
    )
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return "123456"

    with pytest.raises(BhoonidhiAuthError, match="Please wait before resending"):
        _am().login(otp_prompt=prompt)
    assert len(prompts) == 1, "a hard failure (417) must not be retried"
