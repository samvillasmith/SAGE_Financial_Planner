"""
Sage Researcher Service - Investment Advice Agent
"""

import os
import logging
import json
from datetime import datetime, UTC
from typing import Optional, Any

import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from agents import Agent, Runner, trace
from agents.models.interface import Model
from agents.models.openai_responses import ModelResponse, Usage
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_text import ResponseOutputText
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
from agents.extensions.models.litellm_model import LitellmModel


class BedrockOpenAIModel(Model):
    """Custom model for OpenAI models on Bedrock that bypasses LiteLLM."""

    def __init__(self, model_id: str, region: str = "us-east-1"):
        self.model_id = model_id
        self.client = boto3.client('bedrock-runtime', region_name=region)

    async def get_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        previous_response_id=None,
        conversation_id=None,
        prompt=None
    ):
        # Build messages array
        messages = []

        # Add system message if present
        if system_instructions:
            messages.append({"role": "system", "content": system_instructions})

        # Convert input to messages
        if isinstance(input, str):
            messages.append({"role": "user", "content": input})
        elif isinstance(input, list):
            for item in input:
                # Handle dict format (from agents SDK)
                if isinstance(item, dict) and 'role' in item and 'content' in item:
                    messages.append({"role": item['role'], "content": str(item['content'])})
                # Handle tool call results
                elif isinstance(item, dict) and item.get('type') == 'function_call_output':
                    messages.append({
                        "role": "tool",
                        "tool_call_id": item.get('call_id', ''),
                        "content": str(item.get('output', ''))
                    })
                # Handle object format
                elif hasattr(item, 'role') and hasattr(item, 'content'):
                    content = item.content
                    if isinstance(content, list):
                        text_parts = []
                        for part in content:
                            if hasattr(part, 'text'):
                                text_parts.append(part.text)
                            elif isinstance(part, str):
                                text_parts.append(part)
                        content = " ".join(text_parts)
                    messages.append({"role": item.role, "content": str(content)})
                # Handle tool call output objects
                elif hasattr(item, 'type') and item.type == 'function_call_output':
                    messages.append({
                        "role": "tool",
                        "tool_call_id": getattr(item, 'call_id', ''),
                        "content": str(getattr(item, 'output', ''))
                    })
                elif isinstance(item, str):
                    messages.append({"role": "user", "content": item})

        # Build request body
        body = {
            "messages": messages,
            "max_tokens": getattr(model_settings, 'max_tokens', 4096) if model_settings else 4096
        }

        # Convert tools to OpenAI format
        # Note: Only pass essential tools to avoid model errors with too many complex tools
        if tools:
            openai_tools = []
            for tool in tools:
                if hasattr(tool, 'name') and hasattr(tool, 'params_json_schema'):
                    # Filter to only include essential tools (skip complex MCP browser tools)
                    # The model can still describe what it would do with browser tools
                    if tool.name in ['ingest_financial_document']:
                        openai_tools.append({
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": getattr(tool, 'description', ''),
                                "parameters": tool.params_json_schema
                            }
                        })
            if openai_tools:
                body["tools"] = openai_tools

        print(f"DEBUG sending to model: {len(messages)} messages, {len(body.get('tools', []))} tools")
        print(f"DEBUG request body: {json.dumps(body, indent=2)[:2000]}")

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType='application/json',
            accept='application/json'
        )

        result = json.loads(response['body'].read())
        message = result['choices'][0]['message']

        # Build output list
        output = []

        # Check for tool calls
        if 'tool_calls' in message and message['tool_calls']:
            for tool_call in message['tool_calls']:
                output.append(ResponseFunctionToolCall(
                    id=tool_call['id'],
                    type="function_call",
                    call_id=tool_call['id'],
                    name=tool_call['function']['name'],
                    arguments=tool_call['function']['arguments']
                ))

        # Add text content if present
        if message.get('content'):
            output.append(ResponseOutputMessage(
                id="msg_" + result.get('id', 'unknown'),
                type="message",
                role="assistant",
                status="completed",
                content=[ResponseOutputText(type="output_text", text=message['content'], annotations=[])]
            ))

        # If no output, add empty message
        if not output:
            output.append(ResponseOutputMessage(
                id="msg_" + result.get('id', 'unknown'),
                type="message",
                role="assistant",
                status="completed",
                content=[ResponseOutputText(type="output_text", text="", annotations=[])]
            ))

        # Return ModelResponse
        usage_data = result.get('usage', {})
        return ModelResponse(
            output=output,
            usage=Usage(
                input_tokens=usage_data.get('prompt_tokens', 0),
                output_tokens=usage_data.get('completion_tokens', 0),
                total_tokens=usage_data.get('total_tokens', 0)
            ),
            response_id=result.get('id')
        )

    async def stream_response(self, *args, **kwargs):
        # Fall back to non-streaming
        return await self.get_response(*args, **kwargs)

# Suppress LiteLLM warnings about optional dependencies
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)

# Import from our modules
from context import get_agent_instructions, DEFAULT_RESEARCH_PROMPT
from mcp_servers import create_playwright_mcp_server
from tools import ingest_financial_document

# Load environment
load_dotenv(override=True)

app = FastAPI(title="Sage Researcher Service")


# Request model
class ResearchRequest(BaseModel):
    topic: Optional[str] = None  # Optional - if not provided, agent picks a topic


async def run_research_agent(topic: str = None) -> str:
    """Run the research agent to generate investment advice."""

    # Prepare the user query
    if topic:
        query = f"Research this investment topic: {topic}"
    else:
        query = DEFAULT_RESEARCH_PROMPT

    # Region configuration - all us-east-1
    REGION = "us-east-1"
    os.environ["AWS_REGION_NAME"] = REGION  # LiteLLM's preferred variable
    os.environ["AWS_REGION"] = REGION  # Boto3 standard
    os.environ["AWS_DEFAULT_REGION"] = REGION  # Fallback

    # Model configuration - OpenAI GPT OSS 120B via custom Bedrock class
    model = BedrockOpenAIModel(model_id="openai.gpt-oss-120b-1:0", region=REGION)

    # Create and run the agent with MCP server
    with trace("Researcher"):
        async with create_playwright_mcp_server(timeout_seconds=60) as playwright_mcp:
            agent = Agent(
                name="Sage Investment Researcher",
                instructions=get_agent_instructions(),
                model=model,
                tools=[ingest_financial_document],
                mcp_servers=[playwright_mcp],
            )

            result = await Runner.run(agent, input=query, max_turns=15)

    return result.final_output


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Sage Researcher",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/research")
async def research(request: ResearchRequest) -> str:
    """
    Generate investment research and advice.

    The agent will:
    1. Browse current financial websites for data
    2. Analyze the information found
    3. Store the analysis in the knowledge base

    If no topic is provided, the agent will pick a trending topic.
    """
    try:
        response = await run_research_agent(request.topic)
        return response
    except Exception as e:
        print(f"Error in research endpoint: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/research/auto")
async def research_auto():
    """
    Automated research endpoint for scheduled runs.
    Picks a trending topic automatically and generates research.
    Used by EventBridge Scheduler for periodic research updates.
    """
    try:
        # Always use agent's choice for automated runs
        response = await run_research_agent(topic=None)
        return {
            "status": "success",
            "timestamp": datetime.now(UTC).isoformat(),
            "message": "Automated research completed",
            "preview": response[:200] + "..." if len(response) > 200 else response,
        }
    except Exception as e:
        print(f"Error in automated research: {e}")
        return {"status": "error", "timestamp": datetime.now(UTC).isoformat(), "error": str(e)}


@app.get("/health")
async def health():
    """Detailed health check."""
    # Debug container detection
    container_indicators = {
        "dockerenv": os.path.exists("/.dockerenv"),
        "containerenv": os.path.exists("/run/.containerenv"),
        "aws_execution_env": os.environ.get("AWS_EXECUTION_ENV", ""),
        "ecs_container_metadata": os.environ.get("ECS_CONTAINER_METADATA_URI", ""),
        "kubernetes_service": os.environ.get("KUBERNETES_SERVICE_HOST", ""),
    }

    return {
        "service": "Sage Researcher",
        "status": "healthy",
        "sage_api_configured": bool(os.getenv("SAGE_API_ENDPOINT") and os.getenv("SAGE_API_KEY")),
        "timestamp": datetime.now(UTC).isoformat(),
        "debug_container": container_indicators,
        "aws_region": os.environ.get("AWS_DEFAULT_REGION", "not set"),
        "bedrock_model": "bedrock/amazon.nova-pro-v1:0",
    }


@app.get("/test-bedrock")
async def test_bedrock():
    """Test Bedrock connection directly."""
    try:
        import boto3

        # Set ALL region environment variables
        os.environ["AWS_REGION_NAME"] = "us-east-1"
        os.environ["AWS_REGION"] = "us-east-1"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

        # Debug: Check what region boto3 is actually using
        session = boto3.Session()
        actual_region = session.region_name

        # Try to create Bedrock client explicitly in us-west-2
        client = boto3.client("bedrock-runtime", region_name="us-west-2")

        # Debug: Try to list models to verify connection
        try:
            bedrock_client = boto3.client("bedrock", region_name="us-west-2")
            models = bedrock_client.list_foundation_models()
            openai_models = [
                m["modelId"] for m in models["modelSummaries"] if "openai" in m["modelId"].lower()
            ]
        except Exception as list_error:
            openai_models = f"Error listing: {str(list_error)}"

        # Try basic model invocation with Nova Pro
        model = LitellmModel(model="bedrock/amazon.nova-pro-v1:0")

        agent = Agent(
            name="Test Agent",
            instructions="You are a helpful assistant. Be very brief.",
            model=model,
        )

        result = await Runner.run(agent, input="Say hello in 5 words or less", max_turns=1)

        return {
            "status": "success",
            "model": str(model.model),  # Use actual model from LitellmModel
            "region": actual_region,
            "response": result.final_output,
            "debug": {
                "boto3_session_region": actual_region,
                "available_openai_models": openai_models,
            },
        }
    except Exception as e:
        import traceback

        return {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "debug": {
                "boto3_session_region": session.region_name if "session" in locals() else "unknown",
                "env_vars": {
                    "AWS_REGION_NAME": os.environ.get("AWS_REGION_NAME"),
                    "AWS_REGION": os.environ.get("AWS_REGION"),
                    "AWS_DEFAULT_REGION": os.environ.get("AWS_DEFAULT_REGION"),
                },
            },
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
