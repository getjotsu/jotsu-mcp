import pydantic


class WorkflowHandlerResult(pydantic.BaseModel):
    edge: str
    data: dict
