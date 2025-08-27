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

The initialization command creates a workflow file 'workflow.json' in the current directory.

Run it:
```shell
jotsu-mcp workflow run ./workflow.json
```

The output is only the start and end messages since the workflow doesn't have any nodes.


## Hello MCP
The workflow can call a tool from an MCP server.   This allows you to use MCP with models that don't yet support it (really any model other than Claude).

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

Next add a node for a server tool.

```json
[
    {"id":  "greet", "type":  "tool", "name": "greet", "server_id":  "hello"}
]
```

Add some initial data that the 'greet' tool needs:
```json
{"name": "World"}
```
and tell the workflow where to start:
```
"start_node_id": "greet"
```

Finally, add a 'generic' node at the end.
Generic nodes are application-specific - meaning the workflow only handles them by yielding the data -
and are generally used for output and/or debugging.   
The type can be any string not already used by the workflow.  In this case, 'output'.

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
    "start_node_id": "greet",
    "nodes": [
        {"id":  "greet", "type":  "tool", "name": "greet", "server_id":  "hello", "edges":  ["output"]},
        {"id":  "output", "type":  "output", "name": "The result"}
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

Running this workflow again generates a lot more data, but specifically there is a line similar to:

```json
{
  "action": "default",
  "timestamp": 132462.392532502,
  "id": "01k3h80zcaz050eg7080r3fnv7",
  "run_id": "01k3h80t6psmg0s5swsg4yke95",
  "node": {
    "id": "output",
    "name": "The result",
    "type": "output"
  },
  "data": {
    "name": "World",
    "greet": "Hello, World!"
  }
}
```

The data from this node acts as the 'result' of the workflow.
Since workflows can have many branches there is one 'result', 
instead there could be many such lines depending upon the actions the workflow took.

## Development

```shell
uv venv
uv pip install '.[dev,cli,anthropic,openai,cloudflare]'
```
