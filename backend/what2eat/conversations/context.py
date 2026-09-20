from collections.abc import Callable
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from what2eat.errors import AppError


def _complete_tool_round(messages: list[BaseMessage]) -> bool:
    announced: set[str] = set()
    returned: set[str] = set()
    for message in messages:
        if isinstance(message, AIMessage):
            announced.update(call['id'] for call in message.tool_calls)
        elif isinstance(message, ToolMessage):
            if message.tool_call_id not in announced:
                return False
            returned.add(message.tool_call_id)
    return announced == returned


def build_context(
    turns: list[list[BaseMessage]], prefix: list[BaseMessage], budget: int,
    count_tokens: Callable[[list[BaseMessage]], int],
) -> list[BaseMessage]:
    if count_tokens(prefix) > budget:
        raise AppError('context_prefix_too_large', '上下文前缀超过预算，请缩小菜单或偏好。', 422)
    selected: list[list[BaseMessage]] = []
    current = list(prefix)
    for turn in reversed(turns):
        if not turn or not _complete_tool_round(turn):
            continue
        candidate = list(prefix)
        for kept in reversed(selected):
            candidate.extend(kept)
        candidate = list(prefix) + turn + candidate[len(prefix):]
        if count_tokens(candidate) > budget:
            break
        selected.append(turn)
    result = list(prefix)
    for turn in reversed(selected):
        result.extend(turn)
    return result
