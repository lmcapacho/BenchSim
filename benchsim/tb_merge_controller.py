"""Three-way merge support for externally regenerated testbenches."""

import difflib
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MergeResult:
    """Result of attempting to merge local and external testbench changes."""

    content: str
    conflict_count: int = 0

    @property
    def merged(self):
        """Return whether the merge completed without manual resolution."""
        return self.conflict_count == 0


class TBMergeController:
    """Persist snapshots and safely merge regenerated testbench files."""

    FILE_NAME = "benchsim.state.json"

    @classmethod
    def state_path_for_tb(cls, tb_path):
        return Path(tb_path).resolve().with_name(cls.FILE_NAME)

    @staticmethod
    def _tb_key(tb_path):
        return Path(tb_path).resolve().name

    @classmethod
    def _read_state(cls, tb_path):
        state_path = cls.state_path_for_tb(tb_path)
        if not state_path.is_file():
            return {"version": 1, "testbenches": {}}
        try:
            with open(state_path, "r", encoding="utf-8") as file:
                state = json.load(file)
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "testbenches": {}}
        if not isinstance(state, dict):
            return {"version": 1, "testbenches": {}}
        if not isinstance(state.get("testbenches"), dict):
            state["testbenches"] = {}
        state["version"] = 1
        return state

    @classmethod
    def _write_state(cls, tb_path, state):
        state_path = cls.state_path_for_tb(tb_path)
        temp_path = state_path.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8", newline="") as file:
            json.dump(state, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, state_path)

    @classmethod
    def ensure_snapshot(cls, tb_path, content):
        """Create a baseline snapshot only for testbenches not seen before."""
        state = cls._read_state(tb_path)
        key = cls._tb_key(tb_path)
        if key in state["testbenches"]:
            return
        state["testbenches"][key] = {"base": content, "local": content}
        cls._write_state(tb_path, state)

    @classmethod
    def record_saved(cls, tb_path, content):
        """Record the local version while retaining the external merge baseline."""
        state = cls._read_state(tb_path)
        key = cls._tb_key(tb_path)
        snapshot = state["testbenches"].get(key)
        base = snapshot.get("base") if isinstance(snapshot, dict) else None
        state["testbenches"][key] = {
            "base": base if isinstance(base, str) else content,
            "local": content,
        }
        cls._write_state(tb_path, state)

    @classmethod
    def merge_external(cls, tb_path, external_content, *, local_content=None):
        """Merge an external file with the last known local testbench snapshot."""
        state = cls._read_state(tb_path)
        key = cls._tb_key(tb_path)
        snapshot = state["testbenches"].get(key)
        if not isinstance(snapshot, dict):
            state["testbenches"][key] = {"base": external_content, "local": external_content}
            cls._write_state(tb_path, state)
            return MergeResult(external_content)

        base = snapshot.get("base")
        local = snapshot.get("local")
        if not isinstance(base, str) or not isinstance(local, str):
            state["testbenches"][key] = {"base": external_content, "local": external_content}
            cls._write_state(tb_path, state)
            return MergeResult(external_content)

        if isinstance(local_content, str):
            local = local_content

        result = cls._merge_text(base, local, external_content)
        if result.merged:
            state["testbenches"][key] = {"base": external_content, "local": result.content}
            cls._write_state(tb_path, state)
        return result

    @staticmethod
    def _changes(base_lines, other_lines):
        matcher = difflib.SequenceMatcher(a=base_lines, b=other_lines, autojunk=False)
        return [
            (start, end, other_lines[other_start:other_end])
            for tag, start, end, other_start, other_end in matcher.get_opcodes()
            if tag != "equal"
        ]

    @staticmethod
    def _render_region(base_lines, start, end, changes):
        rendered = []
        cursor = start
        for change_start, change_end, replacement in changes:
            rendered.extend(base_lines[cursor:change_start])
            rendered.extend(replacement)
            cursor = change_end
        rendered.extend(base_lines[cursor:end])
        return rendered

    @classmethod
    def _merge_text(cls, base, local, external):
        if local == base:
            return MergeResult(external)
        if external == base or external == local:
            return MergeResult(local)

        base_lines = base.splitlines(keepends=True)
        local_changes = cls._changes(base_lines, local.splitlines(keepends=True))
        external_changes = cls._changes(base_lines, external.splitlines(keepends=True))
        local_index = 0
        external_index = 0
        cursor = 0
        merged = []
        conflicts = 0

        while local_index < len(local_changes) or external_index < len(external_changes):
            next_local = local_changes[local_index] if local_index < len(local_changes) else None
            next_external = external_changes[external_index] if external_index < len(external_changes) else None
            starts = [change[0] for change in (next_local, next_external) if change is not None]
            start = min(starts)
            merged.extend(base_lines[cursor:start])

            local_group = []
            external_group = []
            end = start

            def collect(changes, index, group):
                nonlocal end
                while index < len(changes):
                    change = changes[index]
                    overlaps = change[0] == start if end == start else change[0] < end
                    if not overlaps:
                        break
                    group.append(change)
                    end = max(end, change[1])
                    index += 1
                return index

            local_index = collect(local_changes, local_index, local_group)
            external_index = collect(external_changes, external_index, external_group)
            while True:
                previous_end = end
                local_index = collect(local_changes, local_index, local_group)
                external_index = collect(external_changes, external_index, external_group)
                if end == previous_end:
                    break

            local_region = cls._render_region(base_lines, start, end, local_group)
            external_region = cls._render_region(base_lines, start, end, external_group)
            if not local_group:
                merged.extend(external_region)
            elif not external_group:
                merged.extend(local_region)
            elif local_region == external_region:
                merged.extend(local_region)
            else:
                conflicts += 1
                # Preserve local text in the editor and leave the external change pending.
                merged.extend(local_region)
            cursor = end

        merged.extend(base_lines[cursor:])
        return MergeResult("".join(merged), conflicts)
