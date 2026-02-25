"""Controller for compile/runtime problem parsing and clickable console navigation."""

import html
import os
import re
from pathlib import Path


class ProblemsController:
    """Parse stderr problem lines, render links, and resolve click jumps."""

    def __init__(self, *, console_widget, translate, language_getter):
        self.console = console_widget
        self._tr = translate
        self._language_getter = language_getter
        self.problem_index = {}

    def reset(self):
        self.problem_index = {}

    def parse_from_stderr(self, stderr_text, folder_path):
        if not stderr_text:
            return []

        problems = []
        pattern = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+)(?::(?P<col>\d+))?:\s*(?P<msg>.+)$")
        for raw_line in stderr_text.splitlines():
            line = raw_line.strip()
            match = pattern.match(line)
            if not match:
                continue

            file_token = match.group("file").strip().strip("\"'`")
            line_number = int(match.group("line"))
            col_value = match.group("col")
            column_number = int(col_value) if col_value else 1
            message = match.group("msg").strip()

            file_path = Path(file_token)
            if not file_path.is_absolute():
                file_path = Path(folder_path) / file_path

            problems.append(
                {
                    "file": str(file_path.resolve()),
                    "line": line_number,
                    "col": column_number,
                    "message": message,
                }
            )
        return problems

    def append_problems(self, messages, folder_path):
        all_problems = []
        for message in messages:
            data = message.get("data", {})
            stderr_text = data.get("stderr", "")
            if not stderr_text:
                continue
            all_problems.extend(self.parse_from_stderr(stderr_text, folder_path))

        if not all_problems:
            return

        lang = self._language_getter()
        self.console.append(f"<b>{self._tr('problems_count', lang, count=len(all_problems))}</b>")
        for index, problem in enumerate(all_problems, start=1):
            token = f"p{index}"
            self.problem_index[token] = problem
            location = (
                f"{html.escape(os.path.basename(problem['file']))}:"
                f"{problem['line']}:{problem['col']}"
            )
            message = html.escape(problem["message"])
            self.console.append(f'<a href="problem://{token}">{location}</a>  {message}')

    def resolve_link(self, url_text):
        if not url_text.startswith("problem://"):
            return None
        token = url_text.replace("problem://", "", 1)
        return self.problem_index.get(token)

    def append_jump_unavailable(self, file_path):
        lang = self._language_getter()
        self.console.append(
            self._tr("problems_jump_unavailable", lang, file=os.path.basename(file_path))
        )
