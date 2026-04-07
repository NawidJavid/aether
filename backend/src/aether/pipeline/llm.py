from __future__ import annotations

import re
from pathlib import Path

from anthropic import AsyncAnthropic

from aether.config import settings
from aether.models import ParsedScript, ScriptElement

_PROMPT_TEMPLATE = (Path(__file__).parent.parent / "prompts" / "script_writer.txt").read_text()

_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

_ELEMENT_RE = re.compile(
    r'<shape\s+concept="([^"]+)"\s*/>|<say>(.*?)</say>',
    re.DOTALL,
)


async def generate_script(topic: str) -> ParsedScript:
    prompt = _PROMPT_TEMPLATE.replace("{topic}", topic)

    message = await _client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = ""
    for block in message.content:
        if block.type == "text":
            raw = block.text.strip()
            break

    if not raw:
        raise ValueError(f"LLM returned no text. Block types: {[b.type for b in message.content]}")

    return _parse_script(raw)


def _parse_script(raw: str) -> ParsedScript:
    elements: list[ScriptElement] = []
    say_chunks: list[str] = []
    seen_concepts: list[str] = []

    for match in _ELEMENT_RE.finditer(raw):
        shape_concept, say_text = match.group(1), match.group(2)
        if shape_concept is not None:
            concept = shape_concept.strip()
            elements.append(ScriptElement(kind="shape", concept=concept))
            if concept not in seen_concepts:
                seen_concepts.append(concept)
        elif say_text is not None:
            cleaned = " ".join(say_text.split())
            elements.append(ScriptElement(kind="say", text=cleaned))
            say_chunks.append(cleaned)

    if not elements or elements[0].kind != "shape":
        raise ValueError("Script must start with a <shape> cue")
    if not any(e.kind == "say" for e in elements):
        raise ValueError("Script has no <say> elements")

    return ParsedScript(
        elements=elements,
        full_text=" ".join(say_chunks),
        unique_concepts=seen_concepts,
    )
