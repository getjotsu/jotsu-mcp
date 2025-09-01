import asyncio
import typing

from jotsu.mcp.client import MCPClient
from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import Workflow, WorkflowServer


class WorkflowSessionManager:
    """
    Caches MCP sessions per server and guarantees that all context-enter/exit
    happen in the SAME owning task to avoid AnyIO cancel-scope errors.
    """
    def __init__(self, workflow: Workflow, *, client: MCPClient):
        self._workflow = workflow
        self._client = client

        self._sessions: dict[str, MCPClientSession] = {}
        self._cms: list[typing.AsyncContextManager[MCPClientSession]] = []
        self._lock = asyncio.Lock()

        # Remember the task that 'owns' enter/exit. We'll enforce close() is called by the same task.
        self._owner_task: asyncio.Task | None = None
        self._closed = False

    @property
    def workflow(self) -> Workflow:
        return self._workflow

    async def get_session(self, server: WorkflowServer) -> MCPClientSession:
        if self._closed:
            raise RuntimeError('WorkflowSessionManager is closed')

        async with self._lock:
            if self._owner_task is None:
                self._owner_task = asyncio.current_task()

            session = self._sessions.get(server.id)
            if session is not None:
                return session

            # Enter the client's context here; we own the exit later.
            cm = self._client.session(server)  # async context manager
            session = await cm.__aenter__()    # DO NOT call from another task
            self._cms.append(cm)

            await session.load()

            self._sessions[server.id] = session
            return session

    async def close(self) -> None:
        """Close all sessions together in LIFO order (like an ExitStack)."""
        if self._closed:
            return
        self._closed = True

        owner = self._owner_task
        current = asyncio.current_task()
        if owner is not None and owner is not current:
            raise RuntimeError('close() must be called from the same task that created sessions')

        # Prevent reuse while closing
        self._sessions.clear()

        # First try per-session aclose() (if provided), then exit contexts.
        # aclose() is optional; if present it lets the session tidy up before CM exit.
        for cm in reversed(self._cms):
            try:
                await cm.__aexit__(None, None, None)
            except Exception:  # noqa
                # swallow or log; we don't want teardown exceptions to cascade
                pass

        self._cms.clear()
