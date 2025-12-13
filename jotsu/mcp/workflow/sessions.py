import asyncio
import typing

from jotsu.mcp.client import MCPClient
from jotsu.mcp.client.client import MCPClientSession
from jotsu.mcp.types import Workflow, WorkflowServer, WorkflowMCPNode


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

    async def get_session(self, session_id: str) -> MCPClientSession:
        if self._closed:
            raise RuntimeError('WorkflowSessionManager is closed')

        current = asyncio.current_task()
        async with self._lock:
            if self._owner_task is None:
                self._owner_task = asyncio.current_task()
            elif self._owner_task is not current:
                raise RuntimeError(  # pragma: no cover
                    'WorkflowSessionManager used from a different task; '
                    'this breaks MCP client session cancel scopes.'
                )

            session = self._sessions.get(session_id)
            if session is not None:
                return session

            server = self._get_server(session_id)
            if not server:
                node = self._get_node(session_id)
                if not node:
                    raise RuntimeError(f'Invalid session id: {session_id}')

                server = WorkflowServer(
                    id=session_id,
                    url=node.url,
                    headers=node.headers,
                    client_info=node.client_info,
                )
                self.workflow.servers.append(server)

            # Enter the client's context here; we own the exit later.
            cm = self._client.session(server)  # async context manager
            session = await cm.__aenter__()    # DO NOT call from another task
            self._cms.append(cm)

            await session.load()

            self._sessions[server.id] = session
            return session

    def is_owner(self):
        """Is the current task the owning task"""
        return not self._owner_task or self._owner_task is asyncio.current_task()

    async def aclose(self) -> None:
        """Close all sessions together in LIFO order (like an ExitStack)."""
        if self._closed:
            return
        self._closed = True

        if not self.is_owner():
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

    def _get_server(self, server_id: str) -> WorkflowServer | None:
        for server in self.workflow.servers:
            if server.id == server_id:
                return server
        return None

    def _get_node(self, node_id: str) -> WorkflowMCPNode | None:
        for node in self.workflow.nodes:
            if node.id == node_id:
                if getattr(node, 'url', None):
                    return node
        return None
