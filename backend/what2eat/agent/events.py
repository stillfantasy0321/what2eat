import json
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentEvent:
    event: str
    data: dict


def encode_sse(event: AgentEvent) -> bytes:
    payload = json.dumps(event.data, ensure_ascii=False, separators=(',', ':'))
    return f'event: {event.event}\ndata: {payload}\n\n'.encode('utf-8')
