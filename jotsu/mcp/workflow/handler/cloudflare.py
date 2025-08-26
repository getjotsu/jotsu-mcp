import logging
import os
import typing

from jotsu.mcp.types import WorkflowModelUsage
from jotsu.mcp.types.models import WorkflowCloudflareNode
from jotsu.mcp.workflow import utils
from .utils import get_messages, update_data_from_json, update_data_from_text

logger = logging.getLogger(__name__)


JSON_SCHEMA = {
    'type': 'object',
    'properties': {},
    'additionalProperties': True
}


class CloudflareMixin:

    @property
    def cloudflare_client(self):
        if not hasattr(self, '_cloudflare'):
            from cloudflare import AsyncCloudflare
            setattr(self, '_cloudflare', AsyncCloudflare())
        return getattr(self, '_cloudflare')

    async def handle_cloudflare(
            self, data: dict, *, action_id: str, node: WorkflowCloudflareNode,
            usage: typing.List[WorkflowModelUsage], **_kwargs
    ):
        from cloudflare import AsyncCloudflare

        client: AsyncCloudflare = self.cloudflare_client

        messages = get_messages(data, node.prompt)

        kwargs: dict = {}
        system = data.get('system', node.system)
        if system:
            messages.insert(0, {
                'role': 'system',
                'content': utils.pybars_render(system, data)
            })

        if node.use_json_schema or (node.use_json_schema is None and node.json_schema):
            response_format = {
                'type': 'json_schema',
                'json_schema': node.json_schema or JSON_SCHEMA
            }
            kwargs['response_format'] = response_format

        res = await client.ai.run(
            node.model,
            account_id=os.environ.get('CLOUDFLARE_ACCOUNT_ID'),
            max_tokens=node.max_tokens,
            messages=messages
        )

        usage.append(
            WorkflowModelUsage(
                ref_id=action_id,
                model=node.model,
                **(typing.cast(dict, res.get('usage')))
            )
        )

        # Optionally include the whole response
        if node.include_message_in_output:
            data.update(res)

        # Extract structured output if JSON schema was used
        if node.use_json_schema or (node.use_json_schema is None and node.json_schema):
            update_data_from_json(data, res.get('response'), node=node)
        else:
            update_data_from_text(data, res.get('response'), node=node)

        return data
