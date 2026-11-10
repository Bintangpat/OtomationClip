import asyncio
import os
import unittest
from unittest.mock import AsyncMock
from core.config import Config
from bot.middlewares import AuthMiddleware


class DummyUser:
    def __init__(self, user_id: int, username: str = "testuser"):
        self.id = user_id
        self.username = username
        self.full_name = "Test User"


class DummyMessage:
    def __init__(self, user_id: int, username: str = "testuser"):
        self.from_user = DummyUser(user_id, username)
        self.answer = AsyncMock()


class TestAuthSecurity(unittest.TestCase):
    def setUp(self):
        self.original_allowed = os.environ.get("ALLOWED_USER_ID")

    def tearDown(self):
        if self.original_allowed is not None:
            os.environ["ALLOWED_USER_ID"] = self.original_allowed
        elif "ALLOWED_USER_ID" in os.environ:
            del os.environ["ALLOWED_USER_ID"]

    def test_single_user_id(self):
        os.environ["ALLOWED_USER_ID"] = "11223344"
        self.assertEqual(Config.get_allowed_user_ids(), [11223344])
        self.assertTrue(Config.is_user_allowed(11223344))
        self.assertFalse(Config.is_user_allowed(99999999))

    def test_multiple_user_ids(self):
        os.environ["ALLOWED_USER_ID"] = "11223344, 55667788; 99001122"
        self.assertEqual(Config.get_allowed_user_ids(), [11223344, 55667788, 99001122])
        self.assertTrue(Config.is_user_allowed(55667788))
        self.assertFalse(Config.is_user_allowed(1234))

    def test_empty_user_id_blocks_all(self):
        os.environ["ALLOWED_USER_ID"] = ""
        self.assertEqual(Config.get_allowed_user_ids(), [])
        self.assertFalse(Config.is_user_allowed(11223344))

    def test_auth_middleware_blocks_unauthorized(self):
        os.environ["ALLOWED_USER_ID"] = "12345"
        middleware = AuthMiddleware()

        mock_event = DummyMessage(user_id=99999, username="intruder")
        handler = AsyncMock()
        
        # Run coroutine synchronously
        asyncio.run(middleware(handler, mock_event, {}))

        # Assert: Handler should NOT be called, message.answer was called with rejection
        handler.assert_not_called()
        mock_event.answer.assert_called_once()
        self.assertIn("Akses Ditolak", mock_event.answer.call_args[0][0])
        self.assertIn("99999", mock_event.answer.call_args[0][0])

    def test_auth_middleware_allows_authorized(self):
        os.environ["ALLOWED_USER_ID"] = "12345"
        middleware = AuthMiddleware()

        mock_event = DummyMessage(user_id=12345, username="owner")
        handler = AsyncMock(return_value="OK")

        # Run coroutine synchronously
        res = asyncio.run(middleware(handler, mock_event, {}))

        # Assert: Handler should be called, answer not called
        handler.assert_called_once_with(mock_event, {})
        mock_event.answer.assert_not_called()
        self.assertEqual(res, "OK")


if __name__ == "__main__":
    unittest.main()
