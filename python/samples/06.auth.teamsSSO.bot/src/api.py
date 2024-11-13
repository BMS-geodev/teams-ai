"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Description: initialize the api and route incoming messages
to our app
"""
from http import HTTPStatus
from aiohttp import web
import logging

from botbuilder.core.integration.aiohttp_channel_service_exception_middleware import aiohttp_error_middleware
from bot import app

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)

routes = web.RouteTableDef()


@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    logger.info(f"Received request on /api/messages with body: {await req.text()}")
    try:
        res = await app.process(req)
        logger.info(f"Processed message and got response: {res}")
        if res is not None:
            logger.info("Processed message and returning custom response")
            return res

        logger.info("Processed message, returning default 200 OK response")
        return web.Response(status=HTTPStatus.OK)

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return web.Response(status=HTTPStatus.INTERNAL_SERVER_ERROR, text=str(e))

@routes.get("/auth-start.html")
async def on_auth_start(req: web.Request) -> web.FileResponse:
    logger.info("Received request on /auth-start.html")
    return web.FileResponse(path="./public/auth-start.html")

@routes.get("/auth-end.html")
async def on_auth_end(req: web.Request) -> web.FileResponse:
    logger.info("Received request on /auth-end.html")
    return web.FileResponse(path="./public/auth-end.html")

api = web.Application(middlewares=[aiohttp_error_middleware])
api.add_routes(routes)
