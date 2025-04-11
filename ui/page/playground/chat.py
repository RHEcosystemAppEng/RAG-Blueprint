# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import uuid
import streamlit as st
from llama_stack_client import Agent, AgentEventLogger
from modules.api import llama_stack_api

# Sidebar configurations
with st.sidebar:
    st.header("Configuration")
    available_models = llama_stack_api.client.models.list()
    available_models = [model.identifier for model in available_models if model.model_type == "llm"]
    selected_model = st.selectbox(
        "Choose a model",
        available_models,
        index=0,
    )

    tool_groups = llama_stack_api.client.toolgroups.list()
    tool_groups_list = [tool_group.identifier for tool_group in
                    tool_groups if tool_group.identifier.startswith("mcp::")]
    
    def reset_agent():
        st.session_state.clear()
        st.cache_resource.clear()

    st.header("MCP Servers")
    toolgroup_selection = st.pills(label="Available Servers",
                                   options=tool_groups_list, 
                                   selection_mode="multi",
                                   on_change=reset_agent)
    
    grouped_tools = {}
    total_tools = 0
    for toolgroup_id in toolgroup_selection:
        tools = llama_stack_api.client.tools.list(toolgroup_id=toolgroup_id)
        grouped_tools[toolgroup_id] = [tool.identifier for tool in tools]
        total_tools += len(tools)

    st.markdown(f"Active Tools: 🛠 {total_tools}")

    for group_id, tools in grouped_tools.items():
        with st.expander(f"🔧 Tools from `{group_id}`"):
            for idx, tool in enumerate(tools, start=1):
                st.markdown(f"{idx}. `{group_id}:{tool}`")

    temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1,
        help="Controls the randomness of the response. Higher values make the output more creative and unexpected, lower values make it more conservative and predictable",
    )

    top_p = st.slider(
        "Top P",
        min_value=0.0,
        max_value=1.0,
        value=0.95,
        step=0.1,
    )

    max_tokens = st.slider(
        "Max Tokens",
        min_value=0,
        max_value=4096,
        value=512,
        step=1,
        help="The maximum number of tokens to generate",
    )

    repetition_penalty = st.slider(
        "Repetition Penalty",
        min_value=1.0,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Controls the likelihood for generating the same word or phrase multiple times in the same sentence or paragraph. 1 implies no penalty, 2 will strongly discourage model to repeat words or phrases.",
    )

    stream = st.checkbox("Stream", value=True)
    system_prompt = st.text_area(
        "System Prompt",
        value="You are a helpful AI assistant.",
        help="Initial instructions given to the AI to set its behavior and context",
    )

    # Add clear chat button to sidebar
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# Main chat interface
st.title("🦙 Chat")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if temperature > 0.0:
    strategy = {
        "type": "top_p",
        "temperature": temperature,
        "top_p": top_p,
    }
else:
    strategy = {"type": "greedy"}

@st.cache_resource
def create_agent():
    return Agent(
        llama_stack_api.client,
        model=selected_model,
        instructions=system_prompt, # + " When you use a tool always respond with a summary of the result.",
        sampling_params={
            "strategy": strategy,
        },
        tools=toolgroup_selection,
    )

agent = create_agent()

# if "agent_session_id" not in st.session_state:
#     st.session_state["agent_session_id"] = agent.create_session(session_name=f"mcp_demo_{uuid.uuid4()}")
# session_id = st.session_state["agent_session_id"]

session_id = agent.create_session("mcp-session-{uuid.uuid4()")

# Chat input
if prompt := st.chat_input("Example: What is Llama Stack?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    response = agent.create_turn(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        session_id=session_id,
    )

    # Display assistant response
    with st.chat_message("assistant"):
        retrieval_message_placeholder = st.empty()
        message_placeholder = st.empty()
        full_response = ""
        retrieval_response = ""
        for log in AgentEventLogger().log(response):
            log.print()
            if log.role == "tool_execution":
                retrieval_response += log.content.replace("====", "").strip()
                retrieval_message_placeholder.info(retrieval_response)
            else:
                full_response += log.content
                message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

