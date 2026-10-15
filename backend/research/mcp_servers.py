from agents.mcp.server import MCPServerStdio

def get_edgar_mcp_tools(params=None, timeout_seconds=60):
    if params is None:
        params = {
            "command": "uvx", 
            "args": ["--from", "edgartools[ai]", "edgartools-mcp"],
            "env": {
                "EDGAR_IDENTITY": "Richard Myers richard@frog-hollow.net"
            }
        } 

    return MCPServerStdio(params=params, client_session_timeout_seconds=timeout_seconds)

