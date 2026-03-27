import json
import os
import pytest

from util.pipeline_state import PipelineState


class TestPipelineState:
    def test_start_run_creates_file(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()

        assert os.path.exists(state_file)
        with open(state_file) as f:
            data = json.load(f)
        assert data["started_at"] is not None

    def test_mark_stage_persists(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()
        state.mark_stage("url_retrieval", "completed", output_dir="temp/urls")

        # Reload from disk
        state2 = PipelineState(state_file)
        assert state2.is_completed("url_retrieval")

    def test_is_completed_false_for_missing(self, tmp_path):
        state = PipelineState(str(tmp_path / ".pipeline_state.json"))
        assert not state.is_completed("url_retrieval")

    def test_is_completed_false_for_failed(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()
        state.mark_stage("url_retrieval", "failed")
        assert not state.is_completed("url_retrieval")

    def test_get_resume_point_first_incomplete(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()
        state.mark_stage("url_retrieval", "completed")
        state.mark_stage("datasource_capture", "completed")

        assert state.get_resume_point() == "deep_dive"

    def test_get_resume_point_none_when_all_done(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()
        for stage in ["url_retrieval", "datasource_capture", "deep_dive", "qa_generation", "conversation_conversion"]:
            state.mark_stage(stage, "completed")

        assert state.get_resume_point() is None

    def test_has_previous_run(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        assert not state.has_previous_run()

        state.start_run()
        assert state.has_previous_run()

    def test_get_completed_stages(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()
        state.mark_stage("url_retrieval", "completed")
        state.mark_stage("datasource_capture", "completed")
        state.mark_stage("deep_dive", "failed")

        completed = state.get_completed_stages()
        assert completed == ["url_retrieval", "datasource_capture"]

    def test_clear_removes_file(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        state = PipelineState(state_file)
        state.start_run()
        assert os.path.exists(state_file)

        state.clear()
        assert not os.path.exists(state_file)
        assert not state.has_previous_run()

    def test_handles_corrupt_state_file(self, tmp_path):
        state_file = str(tmp_path / ".pipeline_state.json")
        with open(state_file, "w") as f:
            f.write("not json {{{")

        state = PipelineState(state_file)
        assert not state.has_previous_run()
