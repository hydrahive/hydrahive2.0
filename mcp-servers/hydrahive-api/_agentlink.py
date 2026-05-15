from __future__ import annotations
import asyncio
import json
import logging
from typing import Any
import websockets
from _rest import RestClient

logger = logging.getLogger(__name__)


class AgentLinkClient:
    def __init__(self, rest: RestClient, agent_id: str, base_url: str):
        self.rest = rest
        self.agent_id = agent_id
        self.base_url = base_url.rstrip("/")
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._connected = False
        self._last_error: str | None = None
        self._ws_task: asyncio.Task | None = None

    @property
    def al_rest_base(self) -> str:
        return self.base_url + "/agentlink/api"

    @property
    def al_ws_url(self) -> str:
        ws_base = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        return ws_base + "/agentlink/ws/"

    async def send_state(
        self,
        to_agent: str,
        task_type: str,
        description: str,
        context: dict | None = None,
    ) -> dict[str, Any]:
        body: dict = {
            "agent_id": self.agent_id,
            "task": {
                "type": task_type,
                "description": description,
                "priority": 5,
                "status": "in_progress",
            },
            "handoff": {
                "to_agent": to_agent,
                "reason": description,
                "required_skills": [],
            },
        }
        if context:
            body["context"] = context
        return await self.rest.post("/agentlink/api/states", body=body)

    async def reply_to_handoff(self, state_id: str, result: str) -> dict[str, Any]:
        body: dict = {
            "agent_id": self.agent_id,
            "task": {
                "type": "feature",
                "description": result,
                "priority": 5,
                "status": "completed",
            },
            "handoff": {
                "to_agent": "reply",
                "reason": f"reply_to:{state_id}",
                "required_skills": [],
            },
        }
        return await self.rest.post("/agentlink/api/states", body=body)

    def drain_inbox(self) -> list[dict]:
        items = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return items

    def is_connected(self) -> bool:
        return self._connected

    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        self._ws_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

    async def _listen_loop(self) -> None:
        retry_delay = 1.0
        while True:
            try:
                await self.rest.auth.ensure_token()
                headers = self.rest.auth.headers()
                ws_url = f"{self.al_ws_url}?agent_id={self.agent_id}"
                async with websockets.connect(
                    ws_url, additional_headers=headers, ssl=None
                ) as ws:
                    self._connected = True
                    self._last_error = None
                    retry_delay = 1.0
                    logger.info("AgentLink WS verbunden: %s", ws_url)
                    async for raw in ws:
                        await self._handle_message(str(raw))
            except asyncio.CancelledError:
                self._connected = False
                return
            except Exception as e:
                self._connected = False
                self._last_error = str(e)
                logger.warning("AgentLink WS Fehler: %s — retry in %ss", e, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30.0)

    async def _handle_message(self, raw: str) -> None:
        try:
            event = json.loads(raw)
            if event.get("type") == "handoff_received":
                state_id = event.get("state_id")
                if state_id:
                    state = await self.rest.get(f"/agentlink/api/states/{state_id}")
                    await self._queue.put(state)
        except Exception as e:
            logger.debug("WS-Message parse error: %s", e)
