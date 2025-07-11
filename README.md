# Jotsu MCP

General-purpose library for implementing the Model Context Protocol (MCP) and creating workflows
that use MCP tools, resources and prompts.

## Quickstart

Install the package, including the CLI.
```shell
pip install jotsu-mcp[cli]
```

Create an empty workflow.
```shell
jotsu-mcp workflow init
```

The initialization command creates a workflow 'workflow.json' in the current directory.

Run it:
```shell
jotsu-mcp workflow run ./workflow.json
```

The output is only the start and end messages since the workflow doesn't have any nodes.

Add the following server entry:
```json
{
    "id": "hello",
    "name": "Hello World",
    "url": "https://hello.mcp.jotsu.com/mcp/"
}
```

NOTE: don't forget the path `/mcp/` on the URL.

This server is a publicly available MCP server (with no authentication) that has a couple of resources and a tool.
(The code is available [here](https://github.com/getjotsu/mcp-servers/tree/main/hello)).

Next add nodes for the server resources.

```json
[
    {"id":  "get_greeting", "type": "resource", "name": "resource://greeting", "server_id":  "hello", "edges": ["get_config"]},
    {"id":  "get_config", "type": "resource", "name": "data://config", "server_id":  "hello", "edges": ["greet"]},
    {"id":  "greet", "type":  "tool", "name": "greet", "server_id":  "hello"}
]
```

Finally, add some initial data that the 'greet' tool needs.
```json
{"name": "World"}
```

<details>
<summary>Full Workflow</summary>

```json
{
    "id": "quickstart",
    "name": "quickstart",
    "description": "Simple workflow to interact with the 'hello' MCP server",
    "event": {
        "name": "Manual",
        "type": "manual",
        "metadata": null
    },
    "nodes": [
        {"id":  "get_greeting", "type": "resource", "name": "resource://greeting", "server_id":  "hello", "edges": ["get_config"]},
        {"id":  "get_config", "type": "resource", "name": "data://config", "server_id":  "hello", "edges": ["greet"]},
        {"id":  "greet", "type":  "tool", "name": "greet", "server_id":  "hello"}
    ],
    "servers": [
        {
            "id": "hello",
            "name": "Hello World",
            "url": "https://hello.mcp.jotsu.com/mcp/"
        }
    ],
    "data": {"name":  "World"},
    "metadata": null
}
```

</details>

Running it again generates:


