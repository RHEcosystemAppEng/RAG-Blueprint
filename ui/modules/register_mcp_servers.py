import os
import yaml

class RegisterMCPServers:
    @staticmethod
    def register(client):
        "Register mcp_servers from the configuration file"
        mcp_config_file = os.environ.get("MCP_SERVERS_CONFIG_FILE", "mcp_servers_config.yaml")
        if mcp_config_file is not None:
            try:
                with open(mcp_config_file) as f:
                    mcp_config = yaml.safe_load(f)
                    if "mcp_servers" in  mcp_config:
                        for mcp_server in mcp_config["mcp_servers"]:
                            try:
                                RegisterMCPServers.register_mcp_server(client, mcp_server)
                            except Exception as e:
                                print("failed to register mcp server", e)
            except yaml.YAMLError as exc:
                print(exc)
    @staticmethod
    def register_mcp_server(client, mcp_server: dict):
        "Register an mcp_server"

        # Validate MCP config
        if "name" not in mcp_server:
            raise ValueError("MCP name cannot be empty")
        
        if "url" not in mcp_server:
            raise ValueError("MCP url cannot be empty")

        # Get tool info and register tools
        registered_tools = client.tools.list()
        registered_tools_identifiers = [t.identifier for t in registered_tools]
        registered_toolgroups = [t.toolgroup_id for t in registered_tools]
        
        mcp_server_id = f"mcp::{mcp_server['name']}"
        if mcp_server_id not in registered_toolgroups:
            # Register MCP tool
            client.toolgroups.register(
                toolgroup_id=mcp_server_id,
                provider_id="model-context-protocol",
                mcp_endpoint={"uri":mcp_server['url']},
            )


