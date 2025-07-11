import typing

import pydantic
from mcp.types import Tool, Resource, Prompt

from .rules import Rule


Slug = typing.Annotated[
    str,
    pydantic.StringConstraints(pattern=r'^[a-z0-9_\-]+$', max_length=255)
]
type WorkflowData = typing.Optional[typing.Dict[str, typing.Any]]
type WorkflowMetadata = typing.Optional[typing.Dict[str, typing.Any]]


class WorkflowEvent(pydantic.BaseModel):
    name: str
    type: str
    metadata: WorkflowMetadata = None


class WorkflowNode(pydantic.BaseModel):
    """ Nodes are any action taken on data including but not limited to MCP tools,
    resources and prompts.
    """
    model_config = pydantic.ConfigDict(extra='allow')
    id: Slug
    name: str
    type: str
    metadata: WorkflowMetadata = None
    edges: typing.List[Slug | None] = pydantic.Field(default_factory=list)


class WorkflowRulesNode(WorkflowNode):
    """ Workflow node type with rules.
    """
    rules: typing.List[Rule] | None = None


class WorkflowMCPNode(WorkflowNode):
    """ Base class for WorkflowNodes which are MCP tools, resources or prompts.
    """
    server_id: str
    # Where the output goes in the result.
    member: str | None = None


class WorkflowToolNode(WorkflowMCPNode):
    """ MCP Tool(s)
    """
    type: typing.Literal['tool'] = 'tool'


class WorkflowResourceNode(WorkflowMCPNode):
    """ MCP Resources(s)
    """
    type: typing.Literal['resource'] = 'resource'


class WorkflowPromptNode(WorkflowMCPNode):
    """ MCP Prompt(s)
    """
    type: typing.Literal['prompt'] = 'prompt'


class WorkflowSwitchNode(WorkflowRulesNode):
    """ Switch node with multiple output(s)
    """
    type: typing.Literal['switch'] = 'switch'
    expr: str | None = None


class WorkflowLoopNode(WorkflowRulesNode):
    """ Process each value in a list
    """
    type: typing.Literal['loop'] = 'loop'
    expr: str
    # What member will hold the 'each' value.
    member: str | None = None


class WorkflowFunctionNode(WorkflowRulesNode):
    """ Run a (minimal) Python function on the data.
    """
    type: typing.Literal['function'] = 'function'
    function: str


class WorkflowAnthropicNode(WorkflowNode):
    type: typing.Literal['anthropic'] = 'anthropic'
    model: str
    prompt: str | None = None
    messages: list[str] | None = None
    system: str | None = None
    servers: typing.Literal['*'] | list[str] | None = None
    max_tokens: int = 1024
    json_schema: typing.Optional[dict] = None
    include_message_in_output: bool = True


class WorkflowServer(pydantic.BaseModel):
    """ Servers are any streaming-http MCP Server that this workflow can use.
    When the workflow is started, each of these servers is queried for all available actions.
    """
    id: Slug
    name: str | None = None
    url: pydantic.AnyHttpUrl
    headers: typing.Dict[str, str] = pydantic.Field(default_factory=dict)
    metadata: WorkflowMetadata = None

    @pydantic.field_validator('headers', mode='before')
    def lowercase_headers(cls, value):  # noqa
        return {k.lower(): v for k, v in value.items()} if isinstance(value, dict) else value


class WorkflowServerFull(WorkflowServer):
    tools: typing.List[Tool]
    resources: typing.List[Resource]
    prompts: typing.List[Prompt]


NodeUnion = typing.Annotated[
    typing.Union[
        WorkflowToolNode, WorkflowResourceNode, WorkflowPromptNode,
        WorkflowSwitchNode, WorkflowLoopNode, WorkflowFunctionNode,
        WorkflowAnthropicNode, WorkflowNode
    ],
    'type'
]


class Workflow(pydantic.BaseModel):
    id: Slug
    name: str | None = None
    description: str | None = None
    event: WorkflowEvent | None = None
    start_node_id: str | None = None
    nodes: typing.List[NodeUnion] = pydantic.Field(default_factory=list)
    servers: typing.List[WorkflowServer] = pydantic.Field(default_factory=list)
    # Initial data for this workflow.
    data: WorkflowData = None
    # General metadata for application use (NOT used by the workflow)
    metadata: WorkflowMetadata = None


class WorkflowModelUsage(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='allow')
    node_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
