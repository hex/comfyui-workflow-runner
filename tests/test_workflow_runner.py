# ABOUTME: Tests for the core workflow runner logic using captured response.json data.
# ABOUTME: Validates input injection, dependency pruning, and schema detection.

import json
import os
import copy
import pytest

import workflow_runner

FIXTURE_PATH = os.path.join(
    os.path.dirname(__file__), "fixtures", "test_workflow.api.json"
)

# The fixture is a captured /prompt POST for the demo-video-1 output path.
# It contains 312 nodes — already pruned to that single output pipeline.
# This means only output node 923 (demo-video-1) is present; other outputs
# (avatar-proposals, client-intelligence, etc.) are on separate paths and
# were not included in the capture.

# Known input nodes present in the fixture
KNOWN_INPUTS = {
    "client-name": {"node_id": "968", "class_type": "String Literal"},
    "client-market": {"node_id": "969", "class_type": "String Literal"},
    "avatar-select": {"node_id": "977", "class_type": "ImageFromBatch"},
    "avatar-edits-request": {"node_id": "938", "class_type": "String Literal"},
}

# "client-region" has duplicate titles: 933 (input) and 984 (prompt prefix)
DUPLICATE_TITLE_NODES = {
    "client-region": ["933", "984"],
}

# The only output node in this fixture (already-pruned snapshot)
KNOWN_OUTPUTS = {
    "demo-video-1": {"node_id": "923", "output_type": "video"},
}

# Output nodes detected by class_type (CreateVideo nodes are internal, not named outputs)
EXPECTED_OUTPUT_CLASS_TYPES = {"SaveVideo", "CreateVideo"}


@pytest.fixture
def api_workflow():
    return workflow_runner.load_api_workflow(FIXTURE_PATH)


class TestLoadApiWorkflow:
    def test_loads_all_nodes(self, api_workflow):
        assert len(api_workflow) == 312

    def test_nodes_have_expected_structure(self, api_workflow):
        for node_id, node in api_workflow.items():
            assert "class_type" in node, f"Node {node_id} missing class_type"
            assert "inputs" in node, f"Node {node_id} missing inputs"
            assert "_meta" in node, f"Node {node_id} missing _meta"


class TestDetectSchema:
    def test_detects_input_nodes(self, api_workflow):
        slugs = list(KNOWN_INPUTS.keys())
        schema = workflow_runner.detect_schema(api_workflow, input_slugs=slugs)
        found = {inp["slug"]: inp for inp in schema["inputs"]}

        for slug, expected in KNOWN_INPUTS.items():
            assert slug in found, f"Missing input: {slug}"
            assert found[slug]["node_id"] == expected["node_id"]
            assert found[slug]["class_type"] == expected["class_type"]

    def test_detects_duplicate_title_inputs(self, api_workflow):
        """Nodes with duplicate titles should all be detected."""
        schema = workflow_runner.detect_schema(
            api_workflow, input_slugs=["client-region"]
        )
        found_ids = {inp["node_id"] for inp in schema["inputs"]}
        assert found_ids == {"933", "984"}

    def test_detects_output_by_class_type(self, api_workflow):
        schema = workflow_runner.detect_schema(api_workflow)
        output_types = {out["class_type"] for out in schema["outputs"]}
        assert output_types == EXPECTED_OUTPUT_CLASS_TYPES

    def test_detects_named_output_node(self, api_workflow):
        schema = workflow_runner.detect_schema(api_workflow)
        found = {out["slug"]: out for out in schema["outputs"]}
        assert "demo-video-1" in found
        assert found["demo-video-1"]["node_id"] == "923"
        assert found["demo-video-1"]["output_type"] == "video"

    def test_no_inputs_without_slugs(self, api_workflow):
        schema = workflow_runner.detect_schema(api_workflow)
        assert schema["inputs"] == []


class TestInjectInputs:
    def test_injects_string_inputs(self, api_workflow):
        workflow_runner.inject_inputs(api_workflow, {
            "client-name": "Tesla",
            "client-market": "electric vehicles",
        })
        assert api_workflow["968"]["inputs"]["string"] == "Tesla"
        assert api_workflow["969"]["inputs"]["string"] == "electric vehicles"

    def test_injects_into_all_matching_titles(self, api_workflow):
        """When multiple nodes share a title, inject into all of them."""
        workflow_runner.inject_inputs(api_workflow, {
            "client-region": "north america",
        })
        assert api_workflow["933"]["inputs"]["string"] == "north america"
        assert api_workflow["984"]["inputs"]["string"] == "north america"

    def test_schema_based_injection_targets_exact_node(self, api_workflow):
        """With schema_inputs, only the specified node_id is targeted."""
        schema_inputs = [{"node_id": "933", "slug": "client-region"}]
        original_984 = api_workflow["984"]["inputs"]["string"]

        workflow_runner.inject_inputs(
            api_workflow,
            {"client-region": "north america"},
            schema_inputs=schema_inputs,
        )
        assert api_workflow["933"]["inputs"]["string"] == "north america"
        assert api_workflow["984"]["inputs"]["string"] == original_984

    def test_injects_batch_index(self, api_workflow):
        workflow_runner.inject_inputs(api_workflow, {"avatar-select": 3})
        assert api_workflow["977"]["inputs"]["batch_index"] == 3

    def test_skips_missing_slugs(self, api_workflow):
        original = copy.deepcopy(api_workflow)
        workflow_runner.inject_inputs(api_workflow, {"nonexistent-input": "value"})
        assert api_workflow == original

    def test_skips_empty_values(self, api_workflow):
        original_name = api_workflow["968"]["inputs"]["string"]
        workflow_runner.inject_inputs(api_workflow, {"client-name": ""})
        assert api_workflow["968"]["inputs"]["string"] == original_name


class TestPruneToOutputs:
    def test_fixture_is_already_pruned(self, api_workflow):
        """The fixture is already the dep tree for node 923, so pruning
        to 923 should return the same number of nodes."""
        pruned = workflow_runner.prune_to_outputs(api_workflow, {"923"})
        assert len(pruned) == 312
        assert "923" in pruned

    def test_pruned_contains_all_dependencies(self, api_workflow):
        """Every link reference in pruned nodes points to another pruned node."""
        pruned = workflow_runner.prune_to_outputs(api_workflow, {"923"})
        for node_id, node in pruned.items():
            for key, val in node.get("inputs", {}).items():
                if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                    assert val[0] in pruned, (
                        f"Node {node_id} input '{key}' references {val[0]} "
                        f"which is not in pruned set"
                    )

    def test_prune_to_subset_reduces(self, api_workflow):
        """Pruning to an intermediate node should yield fewer than 312 nodes."""
        # Node 692 (NS Create Video) is an intermediate — should have fewer deps
        pruned = workflow_runner.prune_to_outputs(api_workflow, {"692"})
        assert 0 < len(pruned) < 312
        assert "692" in pruned

    def test_prune_nonexistent_output_is_empty(self, api_workflow):
        pruned = workflow_runner.prune_to_outputs(api_workflow, {"99999"})
        assert len(pruned) == 0

    def test_prune_preserves_no_dangling_refs(self, api_workflow):
        """After pruning to a subset, all link references remain valid."""
        pruned = workflow_runner.prune_to_outputs(api_workflow, {"692"})
        for node_id, node in pruned.items():
            for key, val in node.get("inputs", {}).items():
                if isinstance(val, list) and len(val) == 2 and isinstance(val[0], str):
                    assert val[0] in pruned, (
                        f"Dangling ref: node {node_id}.{key} -> {val[0]}"
                    )


class TestPrepareWorkflow:
    def test_full_pipeline_with_pruning(self):
        result = workflow_runner.prepare_workflow(
            FIXTURE_PATH,
            input_data={"client-name": "TestCorp"},
            output_slugs=["demo-video-1"],
        )
        # demo-video-1 is the whole fixture, so same count
        assert len(result) == 312
        assert result["968"]["inputs"]["string"] == "TestCorp"
        assert "923" in result

    def test_no_output_slugs_returns_full_workflow(self):
        result = workflow_runner.prepare_workflow(
            FIXTURE_PATH,
            input_data={"client-name": "TestCorp"},
        )
        assert len(result) == 312
        assert result["968"]["inputs"]["string"] == "TestCorp"

    def test_unknown_output_slug_returns_full_workflow(self):
        """If the output slug doesn't match any output node, no pruning occurs."""
        result = workflow_runner.prepare_workflow(
            FIXTURE_PATH,
            input_data={},
            output_slugs=["nonexistent-output"],
        )
        assert len(result) == 312
