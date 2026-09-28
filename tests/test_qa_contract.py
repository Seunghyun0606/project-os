import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/qa-result.schema.json"
EXAMPLE_PATH = ROOT / "scaffold/qa/qa/result.example.json"


@pytest.fixture()
def schema():
    value = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return value


@pytest.fixture()
def example():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def validate(schema, value):
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def test_sample_result_matches_schema(schema, example):
    validate(schema, example)


@pytest.mark.parametrize("status", ["UI_APPROVED", "UI_REJECTED", "UNKNOWN"])
def test_remote_control_human_gate_status_is_not_qa_status(schema, example, status):
    example["status"] = status
    with pytest.raises(ValidationError):
        validate(schema, example)


@pytest.mark.parametrize(
    "path",
    [
        "C:/temp/screen.png",
        "/tmp/screen.png",
        "../other-run/result.json",
        "screenshots/../secret.png",
        r"screenshots\01-main.png",
    ],
)
def test_artifact_path_must_be_run_relative(schema, example, path):
    example["artifacts"][0]["path"] = path
    with pytest.raises(ValidationError):
        validate(schema, example)


def test_forward_slash_relative_artifact_path_is_valid(schema, example):
    example["artifacts"][0]["path"] = "screenshots/01-main.png"
    validate(schema, example)


def test_ui_review_status_requires_review_required_ui(schema, example):
    example["ui"] = "PASS"
    with pytest.raises(ValidationError):
        validate(schema, example)
