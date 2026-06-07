"""Tasks-Modul Backend.

register(ctx) →
  - Router   /api/modules/tasks/tasks/*
  - Tools    task_write, task_list, task_read, task_delete
  - Migration 001_tasks.sql
"""
from __future__ import annotations

from .routes import router
from .tools import task_write, task_list, task_read, task_delete


def register(ctx) -> None:
    ctx.register_router(router)
    ctx.register_tool(task_write.TOOL)
    ctx.register_tool(task_list.TOOL)
    ctx.register_tool(task_read.TOOL)
    ctx.register_tool(task_delete.TOOL)
    ctx.register_migrations("migrations")
