import pytest

from utils.json_utils import extract_json_object


def test_extract_json_object_direct_json():
    text = '{"intent":"collect","metrics":["creation_date"]}'
    result = extract_json_object(text)
    assert result["intent"] == "collect"
    assert result["metrics"] == ["creation_date"]


def test_extract_json_object_wrapped_json():
    text = 'Here is the result:\n{"intent":"analyze","metrics":["commits_distribution"]}\nDone.'
    result = extract_json_object(text)
    assert result["intent"] == "analyze"
    assert result["metrics"] == ["commits_distribution"]


def test_extract_json_object_raises_when_missing():
    with pytest.raises(ValueError, match="No JSON object found"):
        extract_json_object("not json at all")
