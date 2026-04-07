from __future__ import annotations

import pytest

from aether.pipeline.llm import _parse_script


VALID_SCRIPT = (
    '<shape concept="glowing brain"/>\n'
    "<say>Artificial intelligence is the field of building machines that think.</say>\n"
    '<shape concept="interconnected nodes"/>\n'
    "<say>Neural networks pass signals much like neurons in your mind.</say>\n"
    '<shape concept="glowing brain"/>\n'
    "<say>And we are still only at the beginning.</say>"
)


def test_parse_valid_script():
    result = _parse_script(VALID_SCRIPT)
    assert len(result.elements) == 6
    assert result.elements[0].kind == "shape"
    assert result.elements[0].concept == "glowing brain"
    assert result.elements[1].kind == "say"
    assert "Artificial intelligence" in result.elements[1].text
    assert len(result.unique_concepts) == 2
    assert result.unique_concepts == ["glowing brain", "interconnected nodes"]


def test_full_text_concatenation():
    result = _parse_script(VALID_SCRIPT)
    words = result.full_text.split()
    assert len(words) > 10
    assert "Artificial" in words
    assert "beginning." in words


def test_missing_opening_shape():
    bad_script = "<say>Hello world.</say>"
    with pytest.raises(ValueError, match="must start with a <shape>"):
        _parse_script(bad_script)


def test_no_say_elements():
    bad_script = '<shape concept="brain"/>'
    with pytest.raises(ValueError, match="no <say> elements"):
        _parse_script(bad_script)


def test_duplicate_concepts_deduped():
    script = (
        '<shape concept="brain"/>\n'
        "<say>First sentence.</say>\n"
        '<shape concept="brain"/>\n'
        "<say>Second sentence.</say>"
    )
    result = _parse_script(script)
    assert result.unique_concepts == ["brain"]
    assert len(result.elements) == 4


def test_whitespace_normalized():
    script = (
        '<shape concept="brain"/>\n'
        "<say>  Lots   of   spaces   here  </say>"
    )
    result = _parse_script(script)
    assert result.elements[1].text == "Lots of spaces here"


def test_multiline_say():
    script = (
        '<shape concept="brain"/>\n'
        "<say>Line one\nline two\nline three</say>"
    )
    result = _parse_script(script)
    assert result.elements[1].text == "Line one line two line three"
