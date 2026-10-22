"""Offline protocol tests. Never contact the provider or send an SMS."""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "custom_components/smsbroadcast/api.py"
spec = importlib.util.spec_from_file_location("smsbroadcast_api", path)
api = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = api
spec.loader.exec_module(api)


class FakeResponse:
    def __init__(self, text, status=200):
        self.body, self.status = text, status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def text(self):
        return self.body


class FakeSession:
    def __init__(self, text="", status=200, error=None):
        self.text, self.status, self.error, self.calls = text, status, error, []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return FakeResponse(self.text, self.status)


class ParsingTests(unittest.TestCase):
    def test_balance_and_zero(self):
        self.assertEqual(api.parse_balance("OK: 5000\n"), 5000)
        self.assertEqual(api.parse_balance("OK: 0"), 0)

    def test_auth_error(self):
        with self.assertRaises(api.AuthenticationError):
            api.parse_balance("ERROR: Username or password is incorrect")

    def test_unknown_error_does_not_echo_response(self):
        with self.assertRaises(api.ApiError) as ctx:
            api.parse_balance("ERROR: confidential password=mysecret")
        self.assertNotIn("mysecret", str(ctx.exception))

    def test_malformed_balances(self):
        for body in ["", "OK: -1", "<html>error</html>", "OK: 5\nERROR: bad"]:
            with self.subTest(body=body), self.assertRaises(api.ApiError):
                api.parse_balance(body)

    def test_multiple_acceptances(self):
        results = api.parse_send("OK: 61400111222:2942263\r\nOK:61400222333:2942264", 2)
        self.assertEqual([r.sms_reference for r in results], ["2942263", "2942264"])

    def test_partial_failure(self):
        results = api.parse_send(
            "OK:61400111222:2942263\nBAD:0400abc111:Invalid Number", 2
        )
        self.assertEqual([r.status for r in results], ["OK", "BAD"])
        self.assertIsNone(results[1].sms_reference)

    def test_incomplete_or_malformed_sends(self):
        for body, count in [
            ("OK:61400111222:123", 2),
            ("", 1),
            ("OK:123", 1),
            ("UNKNOWN:123:456", 1),
        ]:
            with self.subTest(body=body), self.assertRaises(api.ApiError):
                api.parse_send(body, count)

    def test_normalization_deduplication(self):
        self.assertEqual(
            api.normalize_recipients(["0412 345 678", "+61 412 345 678", "412345678"]),
            ["61412345678"],
        )
        self.assertEqual(
            api.normalize_recipients("0412345678,0498765432"),
            ["61412345678", "61498765432"],
        )

    def test_bad_recipients(self):
        for value in [
            [],
            "",
            [""],
            ["0412abc678"],
            ["123"],
            [412345678],
            ["0412345678\nBAD"],
        ]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                api.normalize_recipients(value)

    def test_sender_validation(self):
        for value in ["", "HomeAlarm", "HomeAlarm"]:
            self.assertEqual(api.validate_sender(value), value)
        for value in ["Home Alarm", "+61412345678", "123456789012"]:
            with self.assertRaises(ValueError):
                api.validate_sender(value)


class RequestTests(unittest.IsolatedAsyncioTestCase):
    async def test_client_normalizes_and_deduplicates_before_sending(self):
        session = FakeSession("OK:61412345678:99")
        await api.SmsBroadcastClient(session, "u", "p").async_send(
            ["0412345678", "+61 412 345 678"], "Alarm", "", "", 0, 1
        )
        self.assertEqual(session.calls[0][1]["data"]["to"], "61412345678")

    async def test_mismatched_or_duplicate_response_is_uncertain(self):
        for body in [
            "OK:61412345678:1\nOK:61412345678:2",
            "OK:61412345678:1\nOK:61499999999:2",
            "OK:61412345678:1\nBAD:secret-value:private data",
        ]:
            session = FakeSession(body)
            with self.subTest(body=body), self.assertRaises(api.ApiError) as ctx:
                await api.SmsBroadcastClient(session, "u", "p").async_send(
                    ["0412345678", "0498765432"], "Alarm", "", "", 0, 1
                )
            self.assertIn("check the portal", str(ctx.exception))
            self.assertNotIn("secret-value", str(ctx.exception))
            self.assertEqual(len(session.calls), 1)

    async def test_send_http_failures_never_retry(self):
        for status in [301, 302, 307, 308, 400, 401, 403, 429, 500, 503]:
            session = FakeSession("private response", status)
            with self.subTest(status=status), self.assertRaises(api.ApiError) as ctx:
                await api.SmsBroadcastClient(session, "u", "p").async_send(
                    ["0412345678"], "Alarm", "", "", 0, 1
                )
            self.assertEqual(len(session.calls), 1)
            self.assertFalse(session.calls[0][1]["allow_redirects"])
            self.assertNotIn("private response", str(ctx.exception))

    async def test_send_authentication_and_partial_results(self):
        session = FakeSession("ERROR: Username or password is incorrect.")
        with self.assertRaises(api.AuthenticationError):
            await api.SmsBroadcastClient(session, "u", "p").async_send(
                ["0412345678"], "Alarm", "", "", 0, 1
            )
        self.assertEqual(len(session.calls), 1)
        session = FakeSession("OK:61412345678:1\nBAD:61498765432:Invalid Number")
        result = await api.SmsBroadcastClient(session, "u", "p").async_send(
            ["0412345678", "0498765432"], "Alarm", "", "", 0, 1
        )
        self.assertEqual([item.status for item in result], ["OK", "BAD"])

    async def test_balance_uses_https_post_body(self):
        session = FakeSession("OK: 23")
        client = api.SmsBroadcastClient(session, "user", "pass")
        self.assertEqual(await client.async_balance(), 23)
        url, kwargs = session.calls[0]
        self.assertEqual(url, api.API_URL)
        self.assertNotIn("pass", url)
        self.assertEqual(
            kwargs["data"],
            {"username": "user", "password": "pass", "action": "balance"},
        )
        self.assertFalse(kwargs["allow_redirects"])

    async def test_send_body_preserves_special_characters(self):
        session = FakeSession("OK:61412345678:99")
        client = api.SmsBroadcastClient(session, "user", "pass")
        message = "Alarm & power = down? + é"
        results = await client.async_send(
            ["61412345678"], message, "HomeAlarm", "ha", 15, 5
        )
        self.assertEqual(results[0].sms_reference, "99")
        self.assertEqual(session.calls[0][1]["data"]["message"], message)
        self.assertEqual(session.calls[0][1]["data"]["delay"], "15")
        self.assertEqual(session.calls[0][1]["data"]["maxsplit"], "5")

    async def test_timeout_is_not_retried(self):
        session = FakeSession(error=asyncio.TimeoutError())
        client = api.SmsBroadcastClient(session, "user", "pass")
        with self.assertRaises(api.CommunicationError) as ctx:
            await client.async_send(["61412345678"], "Alarm", "sender", "", 0, 1)
        self.assertIn("uncertain", str(ctx.exception))
        self.assertEqual(len(session.calls), 1)

    async def test_http_errors_redacted(self):
        for status in [302, 500, 401, 403]:
            session = FakeSession("password=secret", status)
            with self.subTest(status=status), self.assertRaises(api.ApiError) as ctx:
                await api.SmsBroadcastClient(session, "user", "pass").async_balance()
            self.assertNotIn("secret", str(ctx.exception))

    async def test_message_limits_prevent_network_request(self):
        for message, split in [("", 1), ("x" * 161, 1), ("x" * 307, 2), ("x" * 766, 5)]:
            session = FakeSession()
            with self.subTest(split=split), self.assertRaises(ValueError):
                await api.SmsBroadcastClient(session, "u", "p").async_send(
                    ["61412345678"], message, "sender", "", 0, split
                )
            self.assertEqual(session.calls, [])

    async def test_long_message_boundary(self):
        session = FakeSession("OK:61412345678:99")
        await api.SmsBroadcastClient(session, "u", "p").async_send(
            ["61412345678"], "x" * 765, "sender", "", 0, 5
        )
        self.assertEqual(len(session.calls), 1)


if __name__ == "__main__":
    unittest.main()
