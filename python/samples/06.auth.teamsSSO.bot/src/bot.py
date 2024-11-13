"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Description: initialize the app and listen for activities.
"""

import sys
import traceback
import logging

from botbuilder.core import MemoryStorage, TurnContext
from teams import Application, TeamsAdapter, ApplicationOptions
from teams.auth import AuthOptions, SsoOptions, ConfidentialClientApplicationOptions, SignInResponse

from config import Config
from state import AppTurnState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('aiohttp.access').setLevel(logging.DEBUG)

config = Config()

# Initialize Teams AI application
storage = MemoryStorage()
app = Application[AppTurnState](
    ApplicationOptions(
        bot_app_id=config.APP_ID,
        storage=storage,
        adapter=TeamsAdapter(config),
        auth=AuthOptions(
            auto=True,
            default="graph",
            settings={
                "graph": SsoOptions(
                    scopes=["User.Read"],
                    msal_config=ConfidentialClientApplicationOptions(
                        client_id=config.AAD_APP_CLIENT_ID,
                        client_secret=config.AAD_APP_CLIENT_SECRET,
                        authority=f"{config.AAD_APP_OAUTH_AUTHORITY_HOST}/{config.AAD_APP_TENANT_ID}"),
                    sign_in_link=f"https://{config.BOT_DOMAIN}/auth-start.html",
                    end_on_invalid_message=True
                ),
            },
        ),
    )
)

auth = app.auth.get("graph")

@app.turn_state_factory
async def turn_state_factory(context: TurnContext):
    logger.info("Initializing turn state")
    turn_state = await AppTurnState.load(context, storage)
    logger.info("Turn state initialized successfully")
    return turn_state

@app.message("/reset")
async def on_reset(
    context: TurnContext, state: AppTurnState
):
    del state.conversation
    logger.info("Conversation state reset")
    await context.send_activity("Ok I've deleted the current conversation state")
    return True

@app.message("/signout")
async def on_sign_out(
    context: TurnContext, state: AppTurnState
):
    logger.info("Sign out initiated by user")
    await app.auth.sign_out(context, state)
    await context.send_activity("you are now signed out...👋")
    return False

@app.activity("message")
async def on_message(
    context: TurnContext, state: AppTurnState
):
    logger.info(f"Received message: : {context.activity.text}")
    curr_count = state.conversation.count
    state.conversation.count = curr_count + 1

    if "graph" in state.temp.auth_tokens:
        logger.info(f"Auth token found {state.temp.auth_tokens['graph']}")
    # if "graph" not in state.temp.auth_tokens:
    #     logger.warning("Auth token not found, prompting for sign-in")
    #     await context.send_activity(f"Please sign in to continue: [Sign in]({config.BOT_DOMAIN}/auth-start.html)")
    #     return True

    await context.send_activity(f"you said: {context.activity.text}")
    return False

@auth.on_sign_in_success
async def on_sign_in_success(
    context: TurnContext, state: AppTurnState
):
    logger.info("Sign-in success event triggered")
    await context.send_activity("successfully logged in!")
    if "graph" in state.temp.auth_tokens:
        token_length = len(state.temp.auth_tokens['graph'])
        logger.info(f"Auth token length: {token_length}")
        await context.send_activity(f"Token string length: {token_length}")
    else:
        logger.warning("Token not found after successful sign-in.")
    await context.send_activity(f"This is what you said before the AuthFlow started: {context.activity.text}")

@auth.on_sign_in_failure
async def on_sign_in_failure(
    context: TurnContext,
    _state: AppTurnState,
    _res: SignInResponse,
):
    logger.error("Sign-in failure event triggered")
    await context.send_activity("failed to login...")
    if _res:
        logger.error(f"Sign-in failure details: {_res}")

@app.error
async def on_error(context: TurnContext, error: Exception):
    # This check writes out errors to console log .vs. app insights.
    # NOTE: In production environment, you should consider logging this to Azure
    #       application insights.
    logger.error(f"\n[on_turn_error] unhandled error: {error}")
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")

# @app.activity("invoke")
# async def on_invoke(context: TurnContext, state: AppTurnState):
#     logger.info("Received invoke activity")
#     activity_type = context.activity.name
#     if activity_type == "signin/verifyState" or activity_type == "signin/tokenExchange":
#         logger.info(f"Processing {activity_type} activity")
#         token_response = None
#         try:
#             if activity_type == "signin/verifyState":
#                 token_response = await auth.verify_state(context, state)
#             elif activity_type == "signin/tokenExchange":
#                 token_response = await auth.exchange_token(context, state)

#             if token_response:
#                 state.temp.auth_tokens["graph"] = token_response.token
#                 await context.send_activity("You are now signed in and can continue.")
#             else:
#                 logger.warning(f"{activity_type} failed; re-prompting for sign-in.")
#                 await context.send_activity(
#                     f"Please complete sign-in: [Sign in]({config.BOT_DOMAIN}/auth-start.html)"
#                 )
#         except Exception as e:
#             logger.error(f"Error handling {activity_type}: {e}")
#             await context.send_activity("An error occurred while processing your sign-in.")
#         return True

#     logger.warning(f"Received unsupported invoke activity: {activity_type}")
#     await context.send_activity(f"Activity '{activity_type}' is not supported at this time.")
#     return False