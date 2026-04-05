import os
import json
from datetime import datetime

from util.file_utils import atomic_write_json
from util.utilities import get_logger

log = get_logger(__name__)

ALL_STAGES = [
    "url_retrieval",
    "datasource_capture",
    "deep_dive",
    "qa_generation",
    "conversation_conversion",
]


class PipelineState:
    """Tracks pipeline execution state for resumability."""

    def __init__(self, state_file: str = ".pipeline_state.json"):
        self.state_file = state_file
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                log.warning(f"Could not load pipeline state: {e}")
        return {"started_at": None, "stages": {}}

    def _save(self):
        atomic_write_json(self.state_file, self.state)

    def start_run(self):
        """Start a fresh pipeline run."""
        self.state = {"started_at": datetime.now().isoformat(), "stages": {}}
        self._save()

    def mark_stage(self, stage: str, status: str, **kwargs):
        """Mark a stage with a status and optional metadata."""
        self.state["stages"][stage] = {"status": status, **kwargs}
        self._save()

    def is_completed(self, stage: str) -> bool:
        """Check if a stage has been completed."""
        return self.state.get("stages", {}).get(stage, {}).get("status") == "completed"

    def get_resume_point(self) -> str | None:
        """Returns the first non-completed stage, or None if all done."""
        for stage in ALL_STAGES:
            if not self.is_completed(stage):
                return stage
        return None

    def has_previous_run(self) -> bool:
        """Check if there's a previous run to resume."""
        return bool(self.state.get("started_at"))

    def get_completed_stages(self) -> list[str]:
        """Return list of completed stage names."""
        return [
            stage for stage in ALL_STAGES
            if self.is_completed(stage)
        ]

    def clear(self):
        """Remove state file and reset."""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        self.state = {"started_at": None, "stages": {}}
