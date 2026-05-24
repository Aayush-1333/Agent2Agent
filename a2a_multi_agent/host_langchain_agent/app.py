"""
This file wraps host langchain agent in a gradio chat app for interaction with the user to handle
requests based on user's queries.

This demonstrates how client agent is responsible for handling the requests and responses between multiple
agents in the agentic environment acting as an orchestrator.
"""

from typing import Generator

import gradio as gr
from gradio.themes import Ocean
from host_agent import root_agent as host_agent


def get_response_from_agent(
    user_msg: str, history: list[dict]
) -> Generator[str, None, None]:
    """Retrieves response from the host agent executor"""

    # 1. FIXED: Gradio is passing history elements as raw dictionaries. 
    # Use .get() lookups instead of .role / .content object attributes.
    input_messages = []
    for msg in history:
        if isinstance(msg, dict):
            input_messages.append({
                "role": msg.get("role", "user"), 
                "content": msg.get("content", "")
            })
            
    print("DEBUG - Sent to Agent:", input_messages)
    
    # Append the current fresh user message to the stack
    input_messages.append({"role": "user", "content": user_msg})
    
    # 2. Invoke agent and get the full state back
    agent_state = host_agent.invoke(
        input={
            "messages": input_messages[:-5]
            if len(input_messages) > 5
            else input_messages
        }
    )

    # 3. Safely extract the final message object/dictionary from the state messages list
    if isinstance(agent_state, dict) and "messages" in agent_state and agent_state["messages"]:
        last_message = agent_state["messages"][-1]
    else:
        last_message = agent_state

    final_text = ""
    reasoning_text = ""

    # 4. Check for content blocks safely depending on framework formats
    content_blocks = None
    if isinstance(last_message, dict):
        content_blocks = last_message.get("content_blocks")
    elif hasattr(last_message, "content_blocks"):
        content_blocks = last_message.content_blocks

    # 5. Parse blocks into text streams cleanly
    if content_blocks:
        for block in content_blocks:
            if isinstance(block, dict):
                if block.get("type") == "reasoning":
                    reasoning_text += block.get("reasoning", "")
                elif block.get("type") == "text":
                    final_text += block.get("text", "")
            elif hasattr(block, "type"):
                if block.type == "reasoning":
                    reasoning_text += getattr(block, "reasoning", "")
                elif block.type == "text":
                    final_text += getattr(block, "text", "")
    else:
        # Fallback to standard content string extraction
        if isinstance(last_message, dict):
            final_text = last_message.get("content", str(last_message))
        else:
            final_text = getattr(last_message, "content", str(last_message))

    # 6. Yield a string back to the ChatInterface.
    # If reasoning exists, we format it neatly using markdown blockquotes.
    if reasoning_text:
        yield f"> 🧠 **Orchestrator Planning & Reasoning:**\n> {reasoning_text}\n\n{final_text}"
    else:
        yield final_text


with gr.Blocks(title="Multi A2A Agents App") as demo:
    gr.Image(
        "https://a2a-protocol.org/latest/assets/a2a-logo-white.svg",
        width=100,
        height=100,
        scale=0,
        show_label=False,
        buttons=[],
        interactive=False,
        container=False,
    )
    # Note: 'type' parameter is removed entirely to align cleanly with your Gradio environment setup
    gr.ChatInterface(
        get_response_from_agent,
        title="A2A Host Agent",
        description="This assistant can help you to check weather and in calculations.",
    )


demo.launch(server_name="0.0.0.0", server_port=3000, theme=Ocean())