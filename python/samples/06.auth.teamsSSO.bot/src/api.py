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

async def req_debug_logging(req: web.Request):
    req_json = await req.json()   
    req_to_get = ['text', 'name', 'type']
    req_info = [f"{k}: {req_json.get(k)}" for k, v in req_json.items() if k in req_to_get]
    logger.info(f"Received request on /api/messages with info: {req_info}")

@routes.post("/api/messages")
async def on_messages(req: web.Request) -> web.Response:
    await req_debug_logging(req)
    try:
        res = await app.process(req)
        logger.info(f"Processed message and got response: {type(res)} , {res.__dict__}")
        
        if res is None:
            # logger.info("Processed message, returning default 200 OK response")
            return web.Response(status=HTTPStatus.OK)
        
        if res.body is None:
            logger.info("Processed message, setting response body empty string instead of none")
            logger.info(f"original response: {res.__dict__}")
            res = web.Response(status=res.status, body={"message": "Test body content", "status": "success"})

        if isinstance(res, web.Response):
            #res.body = {"message": "Test body content", "status": "success"}
            logger.info(f"Response body: {res.body}")
            # logger.info(f"Response headers: {res.headers}")
            # logger.info(f"Response status: {res.status}")
            # logger.info(f"Response reason: {res.reason}")
            # logger.info(f"Response prepared: {res.prepared}")
            # logger.info("Returning fully prepared response.")
            return res
        else: # TODO dev
            # logger.warning("Response was not fully prepared, preparing default response.")
            return web.Response(status=HTTPStatus.CREATED, text="Message processed successfully.")
    

        # logger.info("Processed message and returning custom response")
        # return res

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
