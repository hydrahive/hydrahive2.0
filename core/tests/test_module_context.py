def test_context_accumulates():
    from hydrahive.modules.context import ModuleContext
    from fastapi import APIRouter
    ctx = ModuleContext("example")
    r = APIRouter()
    ctx.register_router(r)
    ctx.register_migrations("migrations")
    ctx.register_service("extension")
    assert ctx.routers == [r]
    assert ctx.migrations_rel == "migrations"
    assert ctx.service_rel == "extension"
