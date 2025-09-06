from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import HTTPException
import crud

import logging

logger = logging.getLogger(__name__)


def register(mcp_server):
    from main import SessionLocal

    ########################################################
    # Health check
    ########################################################

    @mcp_server.custom_route("/health", methods=["GET"])
    async def http_health_check(request):
        return JSONResponse({"status": "healthy", "service": "mcp-server"})

    ########################################################
    # User management
    ########################################################

    @mcp_server.custom_route("/register_user", methods=["POST"])
    async def http_register_user(request: Request):
        logger.info("http_register_user called")
        data = await request.json()
        user_id = data.get("user_id", "")
        role_name = data.get("role_name", "")
        if user_id == "":
            raise HTTPException(status_code=400, detail="user_id is required")
        with SessionLocal() as db:
            crud.get_or_create_user(db, user_id=user_id)
            if role_name:
                crud.assign_role_to_user(db, user_id=user_id, role_name=role_name)
        return JSONResponse({"status": "user registered"})

    @mcp_server.custom_route("/list_users", methods=["GET"])
    async def http_list_users(request: Request):
        logger.info("http_list_users called")
        with SessionLocal() as db:
            users = crud.list_users(db)
            return JSONResponse(
                {
                    "users": [
                        {
                            "user": {
                                "user_id": user.user_id,
                                "role": user.role.name if user.role else ""
                            }
                            for user in users
                        }
                    ]
                }
            )

    ########################################################
    # Role-based access management
    ########################################################

    @mcp_server.custom_route("/role_for_user", methods=["POST"])
    async def http_role_for_user(request: Request):
        logger.info("http_role_for_user called")
        data = await request.json()
        user_id = data.get("user_id", "")
        if user_id == "":
            raise HTTPException(status_code=400, detail="user_id is required")

        with SessionLocal() as db:
            # Ensure the user exists, then fetch with correct lookup key (external user_id)
            crud.get_or_create_user(db, user_id=user_id)
            role = crud.get_role_for_user(db, user_id=user_id)

        if role is None:
            return JSONResponse({"role": ""})
        return JSONResponse({"role": role.name})


    @mcp_server.custom_route("/tools_for_role", methods=["POST"])
    async def http_tools_for_role(request: Request):
        logger.info("http_tools_for_role called")
        data = await request.json()
        role_name = data.get("role", "")
        if role_name == "":
            raise HTTPException(
                status_code=400, detail="role is required and should be non-empty"
            )
        with SessionLocal() as db:
            tools = crud.list_tools_by_role(db, role_name=role_name)

        return JSONResponse(
            {
                "tools": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "description": t.description,
                    }
                    for t in tools
                ]
            }
        )


    @mcp_server.custom_route("/system_prompt_for_role", methods=["POST"])
    async def http_system_prompt_for_role(request: Request):
        logger.info("http_system_prompt_for_role called")
        data = await request.json()
        role_name = data.get("role", "")
        if role_name == "":
            raise HTTPException(
                status_code=400, detail="role is required and should be non-empty"
            )
        with SessionLocal() as db:
            prompt = crud.get_role_default_system_prompt(db, role_name=role_name)
        return JSONResponse({"default_system_prompt": prompt})


    ########################################################
    # Service management
    ########################################################


    @mcp_server.custom_route("/list_services", methods=["GET"])
    def http_list_services(request: Request):
        logger.info("http_list_services called")
        with SessionLocal() as db:
            services = crud.list_services_brief(db)
            result = {
                service["service_name"]: {
                    "transport": "streamable_http",
                    "url": service["endpoint"],
                }
                for service in services
            }
            return JSONResponse({"services": result})


    ########################################################
    # Token management
    ########################################################


    @mcp_server.custom_route("/token", methods=["GET"])
    async def http_get_token(request: Request):
        logger.info("http_get_token called")
        data = await request.json()
        service_name = data.get("service_name", "")
        user_id = data.get("user_id", "")
        if service_name == "" or user_id == "":
            raise HTTPException(
                status_code=400, detail="service_name and user_id are required"
            )

        logger.info(f"http_get_token called service_name={service_name}, user_id={user_id}")

        with SessionLocal() as db:
            # If service does not require authorization, return 200 OK without token
            requires_auth = crud.get_service_requires_authorization(
                db, service_name=service_name
            )
            if requires_auth is None:
                raise HTTPException(status_code=404, detail="Service not found")
            if requires_auth is False:
                return JSONResponse({"status": "Ok"})

            token = crud.get_user_service_token(
                db, user_id=user_id, service_name=service_name
            )
            if token is None:
                raise HTTPException(
                    status_code=401,
                    detail="User is not authorized to use this service. Authroize please.",
                )
            method = crud.get_service_auth_method(db, service_name=service_name)
            if method is None:
                raise HTTPException(status_code=404, detail="Service not found")
            logger.info(
                f"http_get_token returned token={token}, method_authorization={method}"
            )
            return JSONResponse({"token": token, "method_authorization": method})
