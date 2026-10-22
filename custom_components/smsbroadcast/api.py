"""Small asynchronous SMS Broadcast Advanced HTTP API client."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

import aiohttp

API_URL = "https://api.smsbroadcast.com.au/api-adv.php"


class ApiError(Exception):
    """Provider rejected a request or returned an unexpected response."""


class AuthenticationError(ApiError):
    """Credentials were rejected."""


class CommunicationError(ApiError):
    """Transport failure; a send may already have been accepted."""


@dataclass(frozen=True)
class SendResult:
    status: str
    recipient: str
    sms_reference: str | None = None


def check_error(text: str) -> None:
    if text.upper().startswith("ERROR:"):
        detail = text.partition(":")[2].strip().lower()
        if "username or password" in detail or "incorrect password" in detail:
            raise AuthenticationError(
                "SMS Broadcast rejected the username or password."
            )
        # Do not propagate raw provider text, which could contain sensitive data.
        raise ApiError(
            "SMS Broadcast rejected the request. Check sender approval, credit and account settings."
        )


def parse_balance(text: str) -> int:
    text = text.strip()
    check_error(text)
    match = re.fullmatch(r"OK\s*:\s*(\d+)", text, re.IGNORECASE)
    if not match:
        raise ApiError("SMS Broadcast returned an unexpected balance response.")
    return int(match.group(1))


def parse_send(
    text: str, expected_count: int, expected_recipients: list[str] | None = None
) -> list[SendResult]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    check_error(text.strip())
    results = []
    for line in lines:
        check_error(line)
        fields = [field.strip() for field in line.split(":", 2)]
        if (
            len(fields) != 3
            or fields[0] not in ("OK", "BAD")
            or not fields[1]
            or not fields[2]
        ):
            raise ApiError(
                "Unexpected send response. Some messages may have been accepted; do not retry blindly."
            )
        results.append(
            SendResult(fields[0], fields[1], fields[2] if fields[0] == "OK" else None)
        )
    if len(results) != expected_count:
        raise ApiError(
            "Incomplete send response. Some messages may have been accepted; do not retry blindly."
        )
    if expected_recipients is not None:
        try:
            returned = [normalize_recipients(result.recipient)[0] for result in results]
        except ValueError:
            returned = []
        if sorted(returned) != sorted(expected_recipients):
            raise ApiError(
                "Mismatched send response. Some messages may have been accepted; check the portal before retrying."
            )
    return results


def normalize_recipients(value: str | list[str]) -> list[str]:
    values = value.split(",") if isinstance(value, str) else value
    if not values:
        raise ValueError("Provide at least one mobile number.")
    recipients = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("Mobile numbers must be quoted strings.")
        number = re.sub(r"[ ()-]", "", value.strip())
        if number.startswith("+"):
            number = number[1:]
        if not re.fullmatch(r"[0-9]{8,15}", number):
            raise ValueError("Provide mobile numbers containing 8 to 15 digits.")
        if number.startswith("04") and len(number) == 10:
            number = "61" + number[1:]
        elif number.startswith("4") and len(number) == 9:
            number = "61" + number
        if number not in recipients:
            recipients.append(number)
    return recipients


def validate_sender(value: str) -> str:
    if value and not re.fullmatch(r"[A-Za-z0-9]{1,11}", value):
        raise ValueError("Sender must be blank or 1–11 letters/numbers without spaces.")
    return value


class SmsBroadcastClient:
    def __init__(self, session: aiohttp.ClientSession, username: str, password: str):
        self._session = session
        self._username = username
        self._password = password

    async def _post(self, params: dict[str, str], *, sending: bool = False) -> str:
        data = {"username": self._username, "password": self._password, **params}
        try:
            async with self._session.post(
                API_URL,
                data=data,
                timeout=aiohttp.ClientTimeout(total=30),
                allow_redirects=False,
            ) as response:
                if response.status in (401, 403):
                    raise AuthenticationError(
                        "SMS Broadcast refused access. Check credentials and API access restrictions."
                    )
                if response.status != 200:
                    raise ApiError(
                        "SMS Broadcast returned an HTTP error."
                        + (
                            " Some messages may have been accepted; do not retry blindly."
                            if sending
                            else ""
                        )
                    )
                return await response.text()
        except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeError):
            raise CommunicationError(
                "Cannot reach SMS Broadcast."
                + (
                    " Delivery is uncertain; check the SMS Broadcast portal before retrying."
                    if sending
                    else ""
                )
            ) from None

    async def async_balance(self) -> int:
        return parse_balance(await self._post({"action": "balance"}))

    async def async_send(
        self,
        recipients: list[str],
        message: str,
        sender: str,
        reference: str,
        delay: int,
        maxsplit: int,
    ) -> list[SendResult]:
        recipients = normalize_recipients(recipients)
        limit = 160 if maxsplit == 1 else 153 * maxsplit
        if not 1 <= maxsplit <= 5 or not message.strip() or len(message) > limit:
            raise ValueError(
                f"Message must contain 1 to {limit} characters for this maxsplit."
            )
        if len(reference) > 20 or delay < 0:
            raise ValueError(
                "Reference must be at most 20 characters and delay cannot be negative."
            )
        validate_sender(sender)
        return parse_send(
            await self._post(
                {
                    "to": ",".join(recipients),
                    "from": sender,
                    "message": message,
                    "ref": reference,
                    "delay": str(delay),
                    "maxsplit": str(maxsplit),
                },
                sending=True,
            ),
            len(recipients),
            recipients,
        )
