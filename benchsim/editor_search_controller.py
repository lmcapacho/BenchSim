"""Controller for editor find/replace interactions."""


class EditorSearchController:
    """Encapsulates find/replace UI behavior for the editor."""

    def __init__(
        self,
        *,
        editor,
        search_bar,
        find_label,
        find_input,
        replace_label,
        replace_input,
        case_checkbox,
        whole_word_checkbox,
        find_prev_button,
        find_next_button,
        replace_button,
        replace_all_button,
        close_search_button,
        status_label,
        save_button,
        translate,
    ):
        self.editor = editor
        self.search_bar = search_bar
        self.find_label = find_label
        self.find_input = find_input
        self.replace_label = replace_label
        self.replace_input = replace_input
        self.case_checkbox = case_checkbox
        self.whole_word_checkbox = whole_word_checkbox
        self.find_prev_button = find_prev_button
        self.find_next_button = find_next_button
        self.replace_button = replace_button
        self.replace_all_button = replace_all_button
        self.close_search_button = close_search_button
        self.status_label = status_label
        self.save_button = save_button
        self._tr = translate

    def apply_language(self):
        self.find_label.setText(self._tr("editor_find_label"))
        self.replace_label.setText(self._tr("editor_replace_label"))
        self.find_input.setPlaceholderText(self._tr("editor_find_placeholder"))
        self.replace_input.setPlaceholderText(self._tr("editor_replace_placeholder"))
        self.case_checkbox.setText(self._tr("editor_case_sensitive"))
        self.whole_word_checkbox.setText(self._tr("editor_whole_word"))
        self.find_prev_button.setText(self._tr("editor_find_prev"))
        self.find_next_button.setText(self._tr("editor_find_next"))
        self.replace_button.setText(self._tr("editor_replace"))
        self.replace_all_button.setText(self._tr("editor_replace_all"))
        self.close_search_button.setToolTip(self._tr("editor_close_search"))

    def show_find_bar(self):
        self.search_bar.show()
        self.replace_input.hide()
        self.replace_label.hide()
        self.replace_button.hide()
        self.replace_all_button.hide()
        if self.editor.hasSelectedText():
            selected = self.editor.selectedText().replace("\n", "")
            if selected:
                self.find_input.setText(selected)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def show_replace_bar(self):
        self.search_bar.show()
        self.replace_input.show()
        self.replace_label.show()
        self.replace_button.show()
        self.replace_all_button.show()
        if self.editor.hasSelectedText():
            selected = self.editor.selectedText().replace("\n", "")
            if selected:
                self.find_input.setText(selected)
        self.find_input.setFocus()
        self.find_input.selectAll()

    def hide_search_bar(self):
        if self.search_bar.isVisible():
            self.search_bar.hide()
            self.editor.setFocus()

    def _find(self, forward=True):
        query = self.find_input.text()
        if not query:
            self.status_label.setText(self._tr("editor_find_empty"))
            return False

        found = self.editor.find_text(
            query,
            forward=forward,
            case_sensitive=self.case_checkbox.isChecked(),
            whole_word=self.whole_word_checkbox.isChecked(),
            wrap=True,
        )
        if not found:
            self.status_label.setText(self._tr("editor_not_found", query=query))
        return found

    def find_next(self):
        self.show_find_bar()
        self._find(forward=True)

    def find_prev(self):
        self.show_find_bar()
        self._find(forward=False)

    def replace_current(self):
        self.show_replace_bar()
        query = self.find_input.text()
        if not query:
            self.status_label.setText(self._tr("editor_find_empty"))
            return

        selected = self.editor.selectedText()
        case_sensitive = self.case_checkbox.isChecked()
        matches = selected == query if case_sensitive else selected.lower() == query.lower()
        if not matches:
            if not self._find(forward=True):
                return

        replaced = self.editor.replace_current(self.replace_input.text())
        if not replaced:
            self.status_label.setText(self._tr("editor_replace_none"))
            return
        self.status_label.setText(self._tr("editor_replace_done"))
        self.save_button.setEnabled(True)
        self.find_next()

    def replace_all(self):
        self.show_replace_bar()
        query = self.find_input.text()
        if not query:
            self.status_label.setText(self._tr("editor_find_empty"))
            return
        count = self.editor.replace_all(
            query,
            self.replace_input.text(),
            case_sensitive=self.case_checkbox.isChecked(),
            whole_word=self.whole_word_checkbox.isChecked(),
        )
        self.status_label.setText(self._tr("editor_replace_all_done", count=count))
        if count > 0:
            self.save_button.setEnabled(True)
