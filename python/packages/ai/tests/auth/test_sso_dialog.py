"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock

from botbuilder.dialogs import DialogTurnResult, DialogTurnStatus
from msal import ConfidentialClientApplication

from teams.auth import ConfidentialClientApplicationOptions, SsoDialog, SsoOptions
from teams.state import TurnState


class TestSsoDialog(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage_mock = AsyncMock()
        self.msal_config = ConfidentialClientApplicationOptions(
            client_id="client_id",
            authority="https://login.microsoftonline.com/common",
            client_secret="client_secret",
        )

        self.options = SsoOptions(
            scopes=["User.Read"],
            msal_config=self.msal_config,
            sign_in_link="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            timeout=900000,
            end_on_invalid_message=True,
            storage=self.storage_mock,
        )

        self.msal_app = MagicMock(spec=ConfidentialClientApplication)
        self.sso_dialog = SsoDialog("test_sso", self.options, self.msal_app)

        self.context = self.create_mock_context()
        self.state = await TurnState.load(self.context)

    def create_mock_context(self):
        context = MagicMock()
        activity = MagicMock()
        activity.type = "message"
        activity.text = "dummy_text"
        activity.channel_id = "msteams"
        activity.from_property = MagicMock(id="user_id", aad_object_id="aad_object_id")
        activity.conversation = MagicMock(id="conversation_id")
        activity.value = {"token": "dummy_token", "id": "dummy_id"}
        context.activity = activity
        return context

    async def test_step_one(self):
        waterfall_step_context = MagicMock()
        waterfall_step_context.begin_dialog = AsyncMock(
            return_value=DialogTurnResult(DialogTurnStatus.Waiting)
        )

        result = await self.sso_dialog._step_one(waterfall_step_context)

        waterfall_step_context.begin_dialog.assert_called_once_with("TeamsSsoPrompt")
        self.assertEqual(result.status, DialogTurnStatus.Waiting)

    async def test_step_two_no_dedup_conflict(self):
        waterfall_step_context = MagicMock()
        waterfall_step_context.result = {"token": "new_access_token"}

        class TempState:
            duplicate_token_exchange = False

        waterfall_step_context.context.state.temp = TempState()

        self.sso_dialog._should_dedup = AsyncMock(return_value=True)
        waterfall_step_context.end_dialog = AsyncMock(
            return_value=DialogTurnResult(DialogTurnStatus.Waiting)
        )

        result = await self.sso_dialog._step_two(waterfall_step_context)

        self.sso_dialog._should_dedup.assert_called_once_with(waterfall_step_context.context)
        self.assertFalse(waterfall_step_context.context.state.temp.duplicate_token_exchange)
        self.assertEqual(result.status, DialogTurnStatus.Waiting)

    async def test_step_two_dedup_conflict(self):
        waterfall_step_context = MagicMock()
        waterfall_step_context.result = {"token": "new_access_token"}

        class TempState:
            duplicate_token_exchange = True

        waterfall_step_context.context.state.temp = TempState()

        self.sso_dialog._should_dedup = AsyncMock(return_value=True)
        waterfall_step_context.end_dialog = AsyncMock(
            return_value=DialogTurnResult(DialogTurnStatus.Waiting)
        )

        result = await self.sso_dialog._step_two(waterfall_step_context)

        self.sso_dialog._should_dedup.assert_called_once_with(waterfall_step_context.context)
        self.assertTrue(waterfall_step_context.context.state.temp.duplicate_token_exchange)
        self.assertEqual(result.status, DialogTurnStatus.Waiting)
