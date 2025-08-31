import typing

import pydantic
from mcp.types import Tool, Resource, Prompt
from ulid import ULID

from .rules import Rule


def slug():
    return str(ULID()).lower()


Slug = typing.Annotated[
    str,
    pydantic.StringConstraints(pattern=r'^[a-z0-9_\-]+$', max_length=255)
]
WorkflowData = typing.Optional[typing.Dict[str, typing.Any]]
WorkflowMetadata = typing.Optional[typing.Dict[str, typing.Any]]
WorkflowJsonSchema = typing.Optional[typing.Dict[str, typing.Any]]


class WorkflowEvent(pydantic.BaseModel):
    name: str
    type: str
    json_schema: WorkflowJsonSchema = None
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

    @classmethod
    def model_create(cls, **kwargs):
        kwargs['id'] = kwargs.get('id', slug())
        kwargs['name'] = kwargs.get('name', slug())
        return cls(**kwargs)


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


class WorkflowTransform(pydantic.BaseModel):
    type: typing.Literal['set', 'move', 'delete']
    source: str
    target: str | None = None
    datatype: typing.Optional[typing.Literal['string', 'integer', 'float', 'boolean']] = None


class WorkflowTransformNode(WorkflowRulesNode):
    """ Change data.
    """
    type: typing.Literal['transform'] = 'transform'
    transforms: list[WorkflowTransform]
    expr: str | None = None


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


class WorkflowPickNode(WorkflowNode):
    """ Prune the data down to make it more readable.
    """
    type: typing.Literal['pick'] = 'pick'
    expressions: typing.Dict[str, str]


class WorkflowModelNode(WorkflowNode):
    model: str
    prompt: str | None = None
    messages: list[str] | None = None
    system: str | None = None
    max_tokens: int = 1024
    use_json_schema: typing.Optional[bool] = None
    json_schema: typing.Optional[dict] = None
    include_message_in_output: bool = True
    # Where the output goes in the result.
    member: str | None = None


class WorkflowAnthropicNode(WorkflowModelNode):
    type: typing.Literal['anthropic'] = 'anthropic'
    servers: typing.Literal['*'] | list[str] | None = None


class WorkflowOpenAINode(WorkflowModelNode):
    type: typing.Literal['openai'] = 'openai'


class WorkflowCloudflareNode(WorkflowModelNode):
    type: typing.Literal['cloudflare'] = 'cloudflare'


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

    @classmethod
    def model_create(cls, **kwargs):
        kwargs['id'] = kwargs.get('id', slug())
        return cls(**kwargs)


class WorkflowServerFull(WorkflowServer):
    tools: typing.List[Tool]
    resources: typing.List[Resource]
    prompts: typing.List[Prompt]


NodeUnion = typing.Annotated[
    typing.Union[
        WorkflowToolNode, WorkflowResourceNode, WorkflowPromptNode,
        WorkflowSwitchNode, WorkflowLoopNode, WorkflowFunctionNode, WorkflowTransformNode,
        WorkflowAnthropicNode, WorkflowOpenAINode, WorkflowCloudflareNode, WorkflowNode
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
    # Initial data for this workflow that can be overridden when run.
    data: WorkflowData = None
    # General metadata for application use (NOT used by the workflow)
    metadata: WorkflowMetadata = None

    @classmethod
    def model_create(cls, **kwargs):
        kwargs['id'] = kwargs.get('id', slug())
        return cls(**kwargs)


class WorkflowModelUsage(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='allow')
    ref_id: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
