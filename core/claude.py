import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request


@dataclass
class TextBlock:
    type: str
    text: str


@dataclass
class ToolUseBlock:
    type: str
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class OllamaMessage:
    content: list[TextBlock | ToolUseBlock]
    stop_reason: str


class Claude:
    def __init__(self, model: str):
        self.model = model
        self.base_url = self._normalize_base_url(
            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )

    def _normalize_base_url(self, base_url: str) -> str:
        normalized = base_url.rstrip("/")

        if normalized.endswith("/api"):
            return normalized[:-4]

        if normalized.endswith("/v1"):
            return normalized[:-3]

        return normalized

    def add_user_message(self, messages: list, message):
        user_message = {
            "role": "user",
            "content": message.content if hasattr(message, "content") else message,
        }
        messages.append(user_message)

    def add_assistant_message(self, messages: list, message):
        assistant_message = {
            "role": "assistant",
            "content": message.content if hasattr(message, "content") else message,
        }
        messages.append(assistant_message)

    def text_from_message(self, message):
        return "\n".join(
            [block.text for block in message.content if block.type == "text"]
        )

    def _normalize_tool_arguments(self, arguments: Any) -> dict[str, Any]:
        if isinstance(arguments, dict):
            return arguments

        if isinstance(arguments, str):
            try:
                loaded = json.loads(arguments)
                if isinstance(loaded, dict):
                    return loaded
            except json.JSONDecodeError:
                return {"input": arguments}

        return {}

    def _convert_assistant_content(self, content: Any) -> dict[str, Any]:
        if isinstance(content, str):
            return {"role": "assistant", "content": content}

        text_parts = []

        for block in content or []:
            block_type = getattr(block, "type", None)
            if isinstance(block, dict):
                block_type = block.get("type")

            if block_type == "text":
                text_parts.append(
                    block.get("text", "")
                    if isinstance(block, dict)
                    else getattr(block, "text", "")
                )
                continue

        assistant_message = {
            "role": "assistant",
            "content": "\n".join(part for part in text_parts if part),
        }

        return assistant_message

    def _convert_user_content(self, content: Any) -> list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"role": "user", "content": content}]

        if not isinstance(content, list):
            return [{"role": "user", "content": str(content)}]

        tool_results = []
        text_parts = []

        for block in content:
            block_type = getattr(block, "type", None)
            if isinstance(block, dict):
                block_type = block.get("type")

            if block_type == "tool_result":
                tool_results.append(
                    {
                        "role": "tool",
                        "tool_call_id": (
                            block.get("tool_use_id")
                            if isinstance(block, dict)
                            else getattr(block, "tool_use_id", "")
                        ),
                        "content": (
                            block.get("content", "")
                            if isinstance(block, dict)
                            else getattr(block, "content", "")
                        ),
                    }
                )
            elif block_type == "text":
                text_parts.append(
                    block.get("text", "")
                    if isinstance(block, dict)
                    else getattr(block, "text", "")
                )

        if tool_results:
            return tool_results

        return [{"role": "user", "content": "\n".join(text_parts)}]

    def _to_ollama_messages(self, messages: list, system: str | None = None):
        ollama_messages = []

        if system:
            ollama_messages.append({"role": "system", "content": system})

        for message in messages:
            role = message.get("role")
            content = message.get("content")

            if role == "assistant":
                ollama_messages.append(self._convert_assistant_content(content))
            elif role == "user":
                ollama_messages.extend(self._convert_user_content(content))

        return ollama_messages

    def _to_ollama_tools(self, tools: list[dict[str, Any]] | None):
        if not tools:
            return None

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object"}),
                },
            }
            for tool in tools
        ]

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with request.urlopen(http_request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _create_message_from_native_response(
        self, data: dict[str, Any]
    ) -> OllamaMessage:
        message = data.get("message", {})
        content: list[TextBlock | ToolUseBlock] = []

        if message.get("content"):
            content.append(TextBlock(type="text", text=message["content"]))

        for tool_call in message.get("tool_calls", []):
            function = tool_call.get("function", {})
            content.append(
                ToolUseBlock(
                    type="tool_use",
                    id=tool_call.get("id", function.get("name", "tool")),
                    name=function.get("name", ""),
                    input=self._normalize_tool_arguments(function.get("arguments", {})),
                )
            )

        done_reason = data.get("done_reason")
        stop_reason = "tool_use" if message.get("tool_calls") else done_reason
        return OllamaMessage(content=content, stop_reason=stop_reason or "stop")

    def chat(
        self,
        messages,
        system=None,
        temperature=1.0,
        stop_sequences=[],
        tools=None,
        thinking=False,
        thinking_budget=1024,
    ) -> OllamaMessage:
        params = {
            "model": self.model,
            "messages": self._to_ollama_messages(messages, system=system),
            "stream": False,
            "options": {
                "temperature": temperature,
                **({"stop": stop_sequences} if stop_sequences else {}),
            },
        }

        if tools:
            params["tools"] = self._to_ollama_tools(tools)

        try:
            return self._create_message_from_native_response(
                self._post_json(f"{self.base_url}/api/chat", params)
            )
        except error.HTTPError as exc:
            if exc.code != 404:
                raise

        openai_params = {
            "model": self.model,
            "messages": params["messages"],
            "temperature": temperature,
            "stream": False,
        }

        if stop_sequences:
            openai_params["stop"] = stop_sequences

        if tools:
            openai_params["tools"] = self._to_ollama_tools(tools)

        data = self._post_json(f"{self.base_url}/v1/chat/completions", openai_params)
        choice = data["choices"][0]
        message = choice["message"]
        content: list[TextBlock | ToolUseBlock] = []

        if message.get("content"):
            content.append(TextBlock(type="text", text=message["content"]))

        for tool_call in message.get("tool_calls", []):
            function = tool_call.get("function", {})
            content.append(
                ToolUseBlock(
                    type="tool_use",
                    id=tool_call.get("id", function.get("name", "tool")),
                    name=function.get("name", ""),
                    input=self._normalize_tool_arguments(function.get("arguments", {})),
                )
            )

        stop_reason = choice.get("finish_reason")
        if message.get("tool_calls"):
            stop_reason = "tool_use"

        return OllamaMessage(content=content, stop_reason=stop_reason or "stop")
