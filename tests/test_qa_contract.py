import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SCHEMA_PATH = ROOT / "schemas/qa-manifest.schema.json"
SCENARIO_SCHEMA_PATH = ROOT / "schemas/qa-scenario.schema.json"
RESULT_SCHEMA_PATH = ROOT / "schemas/qa-result.schema.json"
LEGACY_RESULT_SCHEMA_PATH = ROOT / "schemas/qa-result-v1.schema.json"
MANIFEST_EXAMPLE_PATH = ROOT / "scaffold/qa/.qa/manifest.yaml"
SCENARIO_EXAMPLE_PATH = ROOT / "scaffold/qa/.qa/scenarios/example.yaml"
RESULT_EXAMPLE_PATH = ROOT / "scaffold/qa/.qa/result.example.json"


def load_schema(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(value)
    return value


def validate(schema, value):
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


@pytest.fixture()
def manifest_schema():
    return load_schema(MANIFEST_SCHEMA_PATH)


@pytest.fixture()
def scenario_schema():
    return load_schema(SCENARIO_SCHEMA_PATH)


@pytest.fixture()
def result_schema():
    return load_schema(RESULT_SCHEMA_PATH)


@pytest.fixture()
def result_example():
    return json.loads(RESULT_EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_manifest_schema_validation(manifest_schema):
    value = yaml.safe_load(MANIFEST_EXAMPLE_PATH.read_text(encoding="utf-8"))
    validate(manifest_schema, value)


def test_scenario_schema_validation(scenario_schema):
    value = yaml.safe_load(SCENARIO_EXAMPLE_PATH.read_text(encoding="utf-8"))
    validate(scenario_schema, value)


def test_result_schema_validation(result_schema, result_example):
    validate(result_schema, result_example)


@pytest.mark.parametrize(
    ("status", "summary", "stage_status", "scenario_status", "next_action"),
    [
        ("PASS", {"warnings": 0, "failed": 0, "humanGates": 0}, "PASS", "PASS", "NONE"),
        ("PASS_WITH_WARNINGS", {"warnings": 1, "failed": 0, "humanGates": 0}, "WARN", "WARN", "REVIEW_WARNINGS"),
        ("FAIL", {"warnings": 0, "failed": 1, "humanGates": 0}, "FAIL", "FAIL", "FIX_AND_RETRY"),
        ("HUMAN_GATE_REQUIRED", {"warnings": 0, "failed": 0, "humanGates": 1}, "PASS", "HUMAN_GATE_REQUIRED", "HUMAN_GATE"),
    ],
)
def test_required_run_statuses_are_valid(
    result_schema, result_example, status, summary, stage_status, scenario_status, next_action
):
    value = deepcopy(result_example)
    value["status"] = status
    value["summary"].update(summary)
    value["summary"]["total"] = 1
    value["summary"]["passed"] = 0 if status in {"FAIL", "HUMAN_GATE_REQUIRED"} else 1
    value["summary"]["skipped"] = 0
    value["stages"] = [{"id": "smoke", "status": stage_status}]
    value["scenarios"] = [{"id": "main", "status": scenario_status}]
    value["visualReviews"] = []
    value["artifacts"] = []
    value["errors"] = (
        [{"code": "TEST_FAILED", "message": "failure", "stage": "smoke", "kind": "test", "retryable": True}]
        if status == "FAIL"
        else []
    )
    value["nextAction"] = next_action
    validate(result_schema, value)


@pytest.mark.parametrize(
    "path",
    [
        "C:/temp/screen.png",
        "/tmp/screen.png",
        "../other-run/result.json",
        ".qa/runs/x/../secret.png",
        r".qa\runs\x\screenshot.png",
    ],
)
def test_artifact_paths_must_be_repository_relative(result_schema, result_example, path):
    value = deepcopy(result_example)
    value["artifacts"][0]["path"] = path
    with pytest.raises(ValidationError):
        validate(result_schema, value)


def test_screenshot_metadata_is_required(result_schema, result_example):
    value = deepcopy(result_example)
    value["artifacts"][0].pop("priority")
    with pytest.raises(ValidationError):
        validate(result_schema, value)


def test_visual_review_category_is_validated(result_schema, result_example):
    value = deepcopy(result_example)
    value["visualReviews"][0]["issues"][0]["category"] = "looks_bad"
    with pytest.raises(ValidationError):
        validate(result_schema, value)


def test_manifest_command_is_os_specific(manifest_schema):
    value = yaml.safe_load(MANIFEST_EXAMPLE_PATH.read_text(encoding="utf-8"))
    value["qa"]["command"] = {}
    with pytest.raises(ValidationError):
        validate(manifest_schema, value)


def test_legacy_v1_result_schema_remains_available():
    schema = load_schema(LEGACY_RESULT_SCHEMA_PATH)
    value = {
        "schema_version": "1.0",
        "run_id": "QA-legacy-001",
        "project": "legacy-project",
        "status": "PASS",
        "started_at": "2026-09-28T01:00:00Z",
        "finished_at": "2026-09-28T01:00:01Z",
        "preflight": "PASS",
        "build": "PASS",
        "launch": "SKIPPED",
        "smoke": "PASS",
        "functional": "PASS",
        "ui": "SKIPPED",
        "artifact_collection": "PASS",
        "cleanup": "PASS",
        "next_action": "NONE",
        "errors": [],
        "artifacts": [],
    }
    validate(schema, value)
