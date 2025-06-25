import typing

import pydantic
from mcp.types import Tool, Resource, Prompt


type WorkflowMetadata = typing.Dict[str, typing.Any]
type WorkflowActionType = (
        typing.Literal['resource'] |
        typing.Literal['prompt'] |
        typing.Literal['tool']
)


class WorkflowEvent(pydantic.BaseModel):
    name: str
    type: str
    metadata: WorkflowMetadata


class WorkflowAction(pydantic.BaseModel):
    """ Actions are any interaction with an MCP client/server
    e.g. get a resource, call a tool, etc.
    """
    name: str
    type: WorkflowActionType


class WorkflowServer(pydantic.BaseModel):
    """ Servers are any MCP Server that this workflow can user.
    When the workflow is started, each of these servers is queried for all available actions.
    """
    id: str
    name: str | None = None
    url: pydantic.AnyHttpUrl


class WorkflowServerFull(WorkflowServer):
    tools: typing.List[Tool]
    resources: typing.List[Resource]
    prompts: typing.List[Prompt]


Slug = pydantic.constr(pattern=r'^[a-z0-9\-]+$')


class Workflow(pydantic.BaseModel):
    id: Slug
    name: str | None = None
    description: str | None = None
    event: WorkflowEvent | None = None
    servers: typing.List[WorkflowServer]
