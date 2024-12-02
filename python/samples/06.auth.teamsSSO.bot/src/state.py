"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional
import logging
from typing import Optional, cast

from botbuilder.core import Storage, TurnContext
from teams.state import TurnState, ConversationState, UserState, TempState

logger = logging.getLogger("state")

class AppConversationState(ConversationState):
    count: int = 0

    @classmethod
    async def load(cls, context: TurnContext, storage: Optional[Storage] = None) -> "AppConversationState":
        state = await super().load(context, storage)
        # logger.info("Loaded AppConversationState")
        return cls(**state)


class AppTurnState(TurnState[AppConversationState, UserState, TempState]):
    conversation: AppConversationState

    @classmethod
    async def load(cls, context: TurnContext, storage: Optional[Storage] = None) -> "AppTurnState":
        # if "app_turn_state" in context.turn_state:
        #     logger.info("Using cached AppTurnState")
        #     return cast(AppTurnState, context.turn_state["app_turn_state"])

        # logger.info("Loading AppTurnState components")

        conversation_state = await AppConversationState.load(context, storage)
        user_state = await UserState.load(context, storage)
        temp_state = await TempState.load(context, storage)

        turn_state = cls(
            conversation=conversation_state,
            user=user_state,
            temp=temp_state
        )
        
        # Cache the loaded turn state in context to prevent re-loading within the same turn
        # context.turn_state["app_turn_state"] = turn_state
        
        # logger.info("AppTurnState fully loaded")
        return turn_state