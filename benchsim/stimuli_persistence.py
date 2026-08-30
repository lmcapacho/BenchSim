"""Persist and restore supported stimulus steps for regenerable testbenches."""

import json
import os
import re
from pathlib import Path


COMMENT_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
DECL_RE = re.compile(r"\b(?:reg|logic|integer)\b([^;]*);", re.IGNORECASE)
IDENT_RE = re.compile(r"\b[_a-zA-Z][_a-zA-Z0-9]*\b")
ASSIGN_RE = re.compile(r"^([_a-zA-Z][_a-zA-Z0-9]*)\s*=\s*(.+)$")
DELAY_RE = re.compile(r"^#\s*(\([^\r\n;]+\)|[^\s;]+)\s*(.*)$")


class StimuliPersistence:
    """Read/write ordered stimulus steps and restore them after TB regeneration."""

    FILE_NAME = "benchsim.stimuli.json"

    @classmethod
    def stimuli_path_for_tb(cls, tb_path):
        """Return sibling JSON path used to persist stimuli for a TB file."""
        return str(Path(tb_path).resolve().with_name(cls.FILE_NAME))

    @classmethod
    def has_store(cls, tb_path):
        """Return whether a persisted stimuli JSON already exists for this TB."""
        return os.path.isfile(cls.stimuli_path_for_tb(tb_path))

    @staticmethod
    def _strip_comments(text):
        return COMMENT_RE.sub("", text)

    @classmethod
    def _find_initial_block(cls, content):
        match = re.search(r"\binitial\b\s+begin", content)
        if not match:
            return None

        body_start = match.end()
        token_re = re.compile(r"\bbegin\b|\bend\b", re.IGNORECASE)
        depth = 1
        for token in token_re.finditer(content, body_start):
            if token.group(0).lower() == "begin":
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    return {
                        "body_start": body_start,
                        "body_end": token.start(),
                    }
        return None

    @classmethod
    def parse_steps(cls, content):
        """Parse supported ordered stimulus steps from the first initial block."""
        block = cls._find_initial_block(content)
        if not block:
            return None

        body = cls._strip_comments(content[block["body_start"]:block["body_end"]])
        steps = []
        for raw_statement in body.split(";"):
            statement = raw_statement.strip()
            if not statement or statement.startswith("$"):
                continue
            if statement.startswith("#"):
                delay_match = DELAY_RE.match(statement)
                if not delay_match:
                    continue
                delay_value, trailing_statement = delay_match.groups()
                steps.append({"kind": "delay", "time": delay_value})
                assign_match = ASSIGN_RE.match(trailing_statement.strip())
                if assign_match:
                    steps.append(
                        {
                            "kind": "assign",
                            "signal": assign_match.group(1),
                            "value": assign_match.group(2).strip(),
                        }
                    )
                continue
            assign_match = ASSIGN_RE.match(statement)
            if assign_match:
                steps.append(
                    {
                        "kind": "assign",
                        "signal": assign_match.group(1),
                        "value": assign_match.group(2).strip(),
                    }
                )
        return steps

    @classmethod
    def _extract_valid_signals(cls, content):
        """Return declared assignable names visible in the TB body."""
        names = set()
        cleaned = cls._strip_comments(content)
        for match in DECL_RE.finditer(cleaned):
            tail = re.sub(r"\[[^\]]+\]", " ", match.group(1))
            tail = re.sub(r"=\s*[^,;]+", " ", tail)
            for name in IDENT_RE.findall(tail):
                if name.lower() in {"signed", "unsigned"}:
                    continue
                names.add(name)
        return names

    @staticmethod
    def _load_json(stimuli_path):
        if not os.path.isfile(stimuli_path):
            return []
        try:
            with open(stimuli_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, json.JSONDecodeError):
            return []
        steps = data.get("steps", [])
        return steps if isinstance(steps, list) else []

    @staticmethod
    def _save_json(stimuli_path, steps):
        data = {
            "version": 1,
            "steps": steps,
        }
        with open(stimuli_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

    @classmethod
    def persist_from_tb_text(cls, tb_path, content):
        """Update JSON with the current ordered stimulus steps from TB text."""
        steps = cls.parse_steps(content)
        if steps is None:
            return False
        valid_signals = cls._extract_valid_signals(content)
        filtered = []
        for step in steps:
            if step.get("kind") == "assign" and step.get("signal") not in valid_signals:
                continue
            filtered.append(step)
        cls._save_json(cls.stimuli_path_for_tb(tb_path), filtered)
        return True

    @classmethod
    def initialize_from_tb_text(cls, tb_path, content):
        """Create the JSON only when it does not exist yet."""
        if cls.has_store(tb_path):
            return False
        return cls.persist_from_tb_text(tb_path, content)

    @staticmethod
    def _line_is_supported_stimulus(line):
        clean = re.sub(r"//.*$", "", line).strip()
        if not clean:
            return False
        statements = [part.strip() for part in clean.split(";") if part.strip()]
        if not statements:
            return False
        for statement in statements:
            if statement.startswith("#"):
                continue
            if ASSIGN_RE.match(statement):
                continue
            return False
        return True

    @classmethod
    def _render_steps(cls, steps, indent):
        lines = []
        for step in steps:
            if step.get("kind") == "delay":
                lines.append(f"{indent}#{step['time']};\n")
            elif step.get("kind") == "assign":
                lines.append(f"{indent}{step['signal']} = {step['value']};\n")
        return "".join(lines)

    @classmethod
    def _inject_steps(cls, content, steps):
        block = cls._find_initial_block(content)
        if not block:
            return content

        body = content[block["body_start"]:block["body_end"]]
        lines = body.splitlines(keepends=True)
        finish_index = None
        for index, line in enumerate(lines):
            if "$finish" in line:
                finish_index = index
                break

        before_finish = lines if finish_index is None else lines[:finish_index]
        after_finish = [] if finish_index is None else lines[finish_index:]
        kept_lines = [line for line in before_finish if not cls._line_is_supported_stimulus(line)]

        indent = "        "
        for line in kept_lines:
            stripped = line.lstrip()
            if stripped:
                indent = line[: len(line) - len(stripped)]
                break

        rendered = cls._render_steps(steps, indent)
        if kept_lines and kept_lines[-1].strip() and rendered:
            kept_lines.append("\n")
        new_body = "".join(kept_lines) + rendered
        if after_finish and new_body and not new_body.endswith("\n"):
            new_body += "\n"
        new_body += "".join(after_finish)
        return content[:block["body_start"]] + new_body + content[block["body_end"]:]

    @classmethod
    def restore_into_tb_text(cls, tb_path, content, *, force_store=False):
        """Restore persisted stimuli when a regenerated TB arrives without them."""
        current_steps = cls.parse_steps(content)
        if current_steps is None:
            return content, False, 0, 0

        stored_steps = cls._load_json(cls.stimuli_path_for_tb(tb_path))
        if not stored_steps:
            return content, False, 0, 0

        if current_steps and not force_store:
            return content, False, len(current_steps), 0

        valid_signals = cls._extract_valid_signals(content)
        restored_steps = []
        dropped_count = 0
        for step in stored_steps:
            if step.get("kind") == "assign" and step.get("signal") not in valid_signals:
                dropped_count += 1
                continue
            restored_steps.append(step)

        if not restored_steps:
            return content, False, 0, dropped_count

        updated_content = cls._inject_steps(content, restored_steps)
        return updated_content, updated_content != content, len(restored_steps), dropped_count
