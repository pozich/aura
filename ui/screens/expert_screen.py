from __future__ import annotations

from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCompleter,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.expert_pipeline import (
    MIN_ALTERNATIVES,
    MIN_CRITERIA,
    MIN_EXPERTS,
    ExpertEvaluationError,
    run_evaluation,
)
from core.gemini_worker import ask_expert_judgment_async
from data.db import list_books
from data.expert_db import (
    add_alternative,
    add_alternative_score,
    add_criteria_judgment,
    add_criterion,
    add_expert,
    create_session,
    delete_alternative,
    delete_criterion,
    delete_expert,
    get_session,
    list_alternative_scores,
    list_alternatives,
    list_criteria,
    list_criteria_judgments,
    list_experts,
    list_results,
    list_sessions,
    replace_alternative_scores,
    replace_criteria_judgments,
    update_session,
)
from ui.widgets.icon_button import CircleIconButton
from ui.widgets.modal import ModalOverlay

ROW_HEIGHT = 36


def _row_header(table: QTableWidget, stretch: bool = True) -> None:
    if stretch:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    else:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.horizontalHeader().setMinimumSectionSize(140)
        table.horizontalHeader().setDefaultSectionSize(160)
    table.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-family: Georgia, serif; font-size: 16px;")
    return label


def _step_header(number: str, title: str, hint: str) -> QVBoxLayout:
    header = QVBoxLayout()
    header.setSpacing(2)
    title_label = QLabel(f"{number}. {title}")
    title_label.setStyleSheet("font-family: Georgia, serif; font-size: 15px; font-weight: 600;")
    hint_label = QLabel(hint)
    hint_label.setProperty("role", "muted")
    hint_label.setWordWrap(True)
    header.addWidget(title_label)
    header.addWidget(hint_label)
    return header


def _card(inner_layout) -> QFrame:
    frame = QFrame()
    frame.setProperty("role", "card")
    frame.setLayout(inner_layout)
    inner_layout.setContentsMargins(16, 14, 16, 14)
    inner_layout.setSpacing(10)
    return frame


def _spinbox(low: float, high: float, default: float) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(low, high)
    box.setDecimals(2)
    box.setSingleStep(0.5)
    box.setValue(default)
    return box


class HistoryModal(ModalOverlay):
    def __init__(self, on_select, parent=None):
        super().__init__("История сессий", parent)
        self._on_select = on_select
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._handle_item)
        self.content_layout.addWidget(self.list_widget)

    def refresh(self):
        self.list_widget.clear()
        for row in list_sessions():
            item = QListWidgetItem(f"{row['title']} — {row['created_at']}")
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.list_widget.addItem(item)

    def _handle_item(self, item: QListWidgetItem):
        session_id = item.data(Qt.ItemDataRole.UserRole)
        self.hide()
        self._on_select(session_id)


class ExpertScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._session_id: int | None = None
        self._criteria: list = []
        self._alternatives: list = []
        self._experts: list = []

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Название сессии")
        self.title_input.editingFinished.connect(self._save_session_meta)

        self.problem_input = QLineEdit()
        self.problem_input.setPlaceholderText("Проблема, которую решаем")
        self.problem_input.editingFinished.connect(self._save_session_meta)

        new_session_button = QPushButton("Новая сессия")
        new_session_button.clicked.connect(self._new_session)

        history_button = QPushButton("История")
        history_button.clicked.connect(self._open_history)

        header_row = QHBoxLayout()
        header_row.addWidget(self.title_input, 1)
        header_row.addWidget(self.problem_input, 2)
        header_row.addWidget(new_session_button)
        header_row.addWidget(history_button)

        intro_label = QLabel(
            "Сравните несколько альтернатив по критериям с участием нескольких экспертов — "
            "приложение посчитает веса критериев (метод AHP), ранжирует альтернативы и "
            "объяснит рекомендацию сработавшими правилами."
        )
        intro_label.setProperty("role", "muted")
        intro_label.setWordWrap(True)

        self.criteria_table = QTableWidget(0, 3)
        self.criteria_table.setHorizontalHeaderLabels(["Критерий", "Вес", ""])
        _row_header(self.criteria_table)
        self.criteria_table.setMaximumHeight(140)

        self.criteria_input = QLineEdit()
        self.criteria_input.setPlaceholderText("Название критерия")
        add_criterion_button = QPushButton("+ критерий")
        add_criterion_button.clicked.connect(self._add_criterion)

        self.alternatives_table = QTableWidget(0, 2)
        self.alternatives_table.setHorizontalHeaderLabels(["Альтернатива", ""])
        _row_header(self.alternatives_table)
        self.alternatives_table.setMaximumHeight(140)

        self.alternative_input = QLineEdit()
        self.alternative_input.setPlaceholderText("Название альтернативы (или начните вводить книгу из библиотеки)")
        self._book_by_label: dict[str, int] = {}
        self.alternative_completer = QCompleter()
        self.alternative_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.alternative_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.alternative_input.setCompleter(self.alternative_completer)
        self._refresh_book_completer()
        add_alternative_button = QPushButton("+ альтернатива")
        add_alternative_button.clicked.connect(self._add_alternative)

        self.experts_table = QTableWidget(0, 2)
        self.experts_table.setHorizontalHeaderLabels(["Эксперт", ""])
        _row_header(self.experts_table)
        self.experts_table.setMaximumHeight(140)

        self.expert_input = QLineEdit()
        self.expert_input.setPlaceholderText("Имя эксперта")
        add_expert_button = QPushButton("+ эксперт")
        add_expert_button.clicked.connect(self._add_expert)

        self._gemini_expert_thread = None
        self.add_gemini_expert_button = QPushButton("+ Gemini-эксперт")
        self.add_gemini_expert_button.clicked.connect(self._add_gemini_expert)

        self.judgments_table = QTableWidget(0, 0)
        _row_header(self.judgments_table, stretch=False)
        self.judgments_table.verticalHeader().setMinimumWidth(180)

        self.scores_table = QTableWidget(0, 0)
        _row_header(self.scores_table, stretch=False)
        self.scores_table.verticalHeader().setMinimumWidth(120)

        grids_tabs = QTabWidget()
        grids_tabs.addTab(self.judgments_table, "Шаг 4 · Сравнение критериев")
        grids_tabs.addTab(self.scores_table, "Шаг 5 · Оценки альтернатив (0-10)")
        grids_tabs.setMaximumHeight(240)

        self.progress_label = QLabel()
        self.progress_label.setProperty("role", "muted")
        self.progress_label.setWordWrap(True)

        self.calculate_button = QPushButton("Шаг 6 · Рассчитать")
        self.calculate_button.setProperty("role", "accent")
        self.calculate_button.setToolTip(
            f"Нужно минимум {MIN_CRITERIA} критерия, {MIN_ALTERNATIVES} альтернативы и {MIN_EXPERTS} эксперта"
        )
        self.calculate_button.clicked.connect(self._calculate)

        self.results_table = QTableWidget(0, 3)
        self.results_table.setHorizontalHeaderLabels(["Альтернатива", "Балл", "Ранг"])
        _row_header(self.results_table)
        self.results_table.setMaximumHeight(180)

        self.explanation = QTextEdit()
        self.explanation.setReadOnly(True)
        self.explanation.setPlaceholderText(
            "Здесь появится рекомендация: веса критериев, коэффициент согласованности "
            "и правила, которые сработали."
        )

        criteria_panel = QVBoxLayout()
        criteria_panel.addLayout(
            _step_header("1", "Критерии", f"Минимум {MIN_CRITERIA} — по ним будете сравнивать альтернативы")
        )
        criteria_panel.addWidget(self.criteria_table)
        criteria_add_row = QHBoxLayout()
        criteria_add_row.addWidget(self.criteria_input, 1)
        criteria_add_row.addWidget(add_criterion_button)
        criteria_panel.addLayout(criteria_add_row)

        alternatives_panel = QVBoxLayout()
        alternatives_panel.addLayout(
            _step_header("2", "Альтернативы", f"Минимум {MIN_ALTERNATIVES} — варианты, из которых выбираем")
        )
        alternatives_panel.addWidget(self.alternatives_table)
        alternative_add_row = QHBoxLayout()
        alternative_add_row.addWidget(self.alternative_input, 1)
        alternative_add_row.addWidget(add_alternative_button)
        alternatives_panel.addLayout(alternative_add_row)

        experts_panel = QVBoxLayout()
        experts_panel.addLayout(
            _step_header("3", "Эксперты", f"Минимум {MIN_EXPERTS} — люди и/или Gemini, каждый оценивает сам")
        )
        experts_panel.addWidget(self.experts_table)
        expert_add_row = QHBoxLayout()
        expert_add_row.addWidget(self.expert_input, 1)
        expert_add_row.addWidget(add_expert_button)
        experts_panel.addLayout(expert_add_row)
        experts_panel.addWidget(self.add_gemini_expert_button)

        entities_row = QHBoxLayout()
        entities_row.addWidget(_card(criteria_panel), 1)
        entities_row.addWidget(_card(alternatives_panel), 1)
        entities_row.addWidget(_card(experts_panel), 1)

        grids_panel = QVBoxLayout()
        grids_panel.addWidget(_section_title("Сравнения и оценки экспертов"))
        grids_panel.addWidget(grids_tabs)
        grids_panel.addWidget(self.progress_label)
        grids_panel.addWidget(self.calculate_button)

        left_column = QVBoxLayout()
        left_column.addLayout(entities_row)
        left_column.addWidget(_card(grids_panel))
        left_column.addStretch()

        results_panel = QVBoxLayout()
        results_panel.addWidget(_section_title("Результат и рекомендация"))
        results_panel.addWidget(self.results_table)
        results_panel.addWidget(self.explanation, 1)

        right_column = QVBoxLayout()
        right_column.addWidget(_card(results_panel), 1)

        main_row = QHBoxLayout()
        main_row.addLayout(left_column, 3)
        main_row.addLayout(right_column, 2)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(24, 16, 24, 16)
        outer_layout.setSpacing(12)
        outer_layout.addLayout(header_row)
        outer_layout.addWidget(intro_label)
        outer_layout.addLayout(main_row, 1)

        self.history_modal = HistoryModal(self._load_session, self)

        self._new_session()

    def _update_progress(self):
        parts = [
            f"Критериев {len(self._criteria)}/{MIN_CRITERIA}",
            f"Альтернатив {len(self._alternatives)}/{MIN_ALTERNATIVES}",
            f"Экспертов {len(self._experts)}/{MIN_EXPERTS}",
        ]
        ready = (
            len(self._criteria) >= MIN_CRITERIA
            and len(self._alternatives) >= MIN_ALTERNATIVES
            and len(self._experts) >= MIN_EXPERTS
        )
        suffix = " — можно рассчитывать" if ready else " — добавьте ещё, чтобы рассчитать"
        self.progress_label.setText(" · ".join(parts) + suffix)
        self.calculate_button.setEnabled(ready)

    def _save_session_meta(self):
        if self._session_id is None:
            return
        update_session(self._session_id, self.title_input.text().strip() or "Без названия", self.problem_input.text().strip())

    def _new_session(self):
        self._session_id = create_session("Новая сессия", "")
        self.title_input.setText("Новая сессия")
        self.problem_input.setText("")
        self._criteria = []
        self._alternatives = []
        self._experts = []
        self._rebuild_criteria_table()
        self._rebuild_alternatives_table()
        self._rebuild_experts_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()
        self.results_table.setRowCount(0)
        self.explanation.setPlainText("")

    def _open_history(self):
        self.history_modal.refresh()
        self.history_modal.show_modal()

    def _load_session(self, session_id: int):
        self._session_id = session_id
        row = get_session(session_id)
        if row is not None:
            self.title_input.setText(row["title"])
            self.problem_input.setText(row["problem_statement"])
        self._criteria = list(list_criteria(session_id))
        self._alternatives = list(list_alternatives(session_id))
        self._experts = list(list_experts(session_id))
        self._rebuild_criteria_table()
        self._rebuild_alternatives_table()
        self._rebuild_experts_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()
        self._refresh_results_table()

    def _add_criterion(self):
        name = self.criteria_input.text().strip()
        if not name:
            return
        add_criterion(self._session_id, name)
        self.criteria_input.clear()
        self._criteria = list(list_criteria(self._session_id))
        self._rebuild_criteria_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()

    def _remove_criterion(self, criterion_id: int):
        delete_criterion(criterion_id)
        self._criteria = list(list_criteria(self._session_id))
        self._rebuild_criteria_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()

    def _refresh_book_completer(self):
        self._book_by_label = {}
        labels = []
        for book in list_books():
            label = f"{book['title']} — {book['author']}" if book["author"] else book["title"]
            self._book_by_label[label] = book["id"]
            labels.append(label)
        self.alternative_completer.setModel(QStringListModel(labels, self.alternative_completer))

    def _add_alternative(self):
        name = self.alternative_input.text().strip()
        if not name:
            return
        book_id = self._book_by_label.get(name)
        add_alternative(self._session_id, name, book_id=book_id)
        self.alternative_input.clear()
        self._alternatives = list(list_alternatives(self._session_id))
        self._rebuild_alternatives_table()
        self._rebuild_scores_grid()

    def _remove_alternative(self, alternative_id: int):
        delete_alternative(alternative_id)
        self._alternatives = list(list_alternatives(self._session_id))
        self._rebuild_alternatives_table()
        self._rebuild_scores_grid()

    def _add_expert(self):
        name = self.expert_input.text().strip()
        if not name:
            return
        add_expert(self._session_id, name)
        self.expert_input.clear()
        self._experts = list(list_experts(self._session_id))
        self._rebuild_experts_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()

    def _remove_expert(self, expert_id: int):
        delete_expert(expert_id)
        self._experts = list(list_experts(self._session_id))
        self._rebuild_experts_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()

    def _add_gemini_expert(self):
        if self._gemini_expert_thread is not None:
            return
        if len(self._criteria) < 2 or not self._alternatives:
            QMessageBox.information(
                self, "Нужны данные", "Сначала добавьте минимум 2 критерия и хотя бы одну альтернативу."
            )
            return
        self.add_gemini_expert_button.setEnabled(False)
        self.add_gemini_expert_button.setText("Gemini оценивает…")
        self._gemini_expert_thread = ask_expert_judgment_async(
            [c["name"] for c in self._criteria],
            [a["name"] for a in self._alternatives],
            self.problem_input.text().strip(),
            self._on_gemini_expert_ready,
            self._on_gemini_expert_error,
            parent=self,
        )

    def _reset_gemini_expert_button(self):
        self._gemini_expert_thread = None
        self.add_gemini_expert_button.setEnabled(True)
        self.add_gemini_expert_button.setText("+ Gemini-эксперт")

    def _on_gemini_expert_ready(self, result: dict):
        self._reset_gemini_expert_button()
        if not result:
            QMessageBox.warning(self, "Gemini не ответил", "Не удалось получить оценку от Gemini-эксперта.")
            return

        expert_id = add_expert(self._session_id, "Gemini-эксперт")
        self._experts = list(list_experts(self._session_id))

        name_to_criterion_id = {c["name"]: c["id"] for c in self._criteria}
        for (a, b), value in result.get("judgments", {}).items():
            if a in name_to_criterion_id and b in name_to_criterion_id:
                add_criteria_judgment(expert_id, name_to_criterion_id[a], name_to_criterion_id[b], value)

        name_to_alternative_id = {a["name"]: a["id"] for a in self._alternatives}
        for alt_name, by_criterion in result.get("scores", {}).items():
            alternative_id = name_to_alternative_id.get(alt_name)
            if alternative_id is None:
                continue
            for criterion_name, score in by_criterion.items():
                criterion_id = name_to_criterion_id.get(criterion_name)
                if criterion_id is not None:
                    add_alternative_score(expert_id, alternative_id, criterion_id, score)

        self._rebuild_experts_table()
        self._rebuild_judgments_grid()
        self._rebuild_scores_grid()

    def _on_gemini_expert_error(self, message: str):
        self._reset_gemini_expert_button()
        QMessageBox.warning(self, "Ошибка", message)

    def _rebuild_criteria_table(self):
        self.criteria_table.setRowCount(len(self._criteria))
        for row, criterion in enumerate(self._criteria):
            self.criteria_table.setItem(row, 0, QTableWidgetItem(criterion["name"]))
            weight = criterion["weight"]
            weight_text = f"{weight:.3f}" if weight is not None else "—"
            self.criteria_table.setItem(row, 1, QTableWidgetItem(weight_text))
            button = CircleIconButton("close", size=20)
            button.clicked.connect(lambda _checked=False, cid=criterion["id"]: self._remove_criterion(cid))
            self.criteria_table.setCellWidget(row, 2, button)
        self._update_progress()

    def _rebuild_alternatives_table(self):
        self.alternatives_table.setRowCount(len(self._alternatives))
        for row, alternative in enumerate(self._alternatives):
            self.alternatives_table.setItem(row, 0, QTableWidgetItem(alternative["name"]))
            button = CircleIconButton("close", size=20)
            button.clicked.connect(lambda _checked=False, aid=alternative["id"]: self._remove_alternative(aid))
            self.alternatives_table.setCellWidget(row, 1, button)
        self._update_progress()

    def _rebuild_experts_table(self):
        self.experts_table.setRowCount(len(self._experts))
        for row, expert in enumerate(self._experts):
            self.experts_table.setItem(row, 0, QTableWidgetItem(expert["name"]))
            button = CircleIconButton("close", size=20)
            button.clicked.connect(lambda _checked=False, eid=expert["id"]: self._remove_expert(eid))
            self.experts_table.setCellWidget(row, 1, button)
        self._update_progress()

    def _existing_judgment_value(self, expert_id: int, a_id: int, b_id: int, rows) -> float:
        for r in rows:
            if r["expert_id"] != expert_id:
                continue
            if r["criterion_a_id"] == a_id and r["criterion_b_id"] == b_id:
                return r["value"]
            if r["criterion_a_id"] == b_id and r["criterion_b_id"] == a_id:
                return 1.0 / r["value"] if r["value"] else 1.0
        return 1.0

    def _rebuild_judgments_grid(self):
        pairs = [
            (self._criteria[i], self._criteria[j])
            for i in range(len(self._criteria))
            for j in range(i + 1, len(self._criteria))
        ]
        self.judgments_table.setRowCount(len(pairs))
        self.judgments_table.setColumnCount(len(self._experts))
        self.judgments_table.setHorizontalHeaderLabels([e["name"] for e in self._experts])
        self.judgments_table.setVerticalHeaderLabels(
            [f"{a['name']} / {b['name']}" for a, b in pairs]
        )

        existing = list(list_criteria_judgments(self._session_id)) if self._session_id else []

        for row, (a, b) in enumerate(pairs):
            for col, expert in enumerate(self._experts):
                value = self._existing_judgment_value(expert["id"], a["id"], b["id"], existing)
                box = _spinbox(1.0 / 9.0, 9.0, value)
                self.judgments_table.setCellWidget(row, col, box)

    def _existing_score_value(self, expert_id: int, alt_id: int, criterion_id: int, rows) -> float:
        for r in rows:
            if (
                r["expert_id"] == expert_id
                and r["alternative_id"] == alt_id
                and r["criterion_id"] == criterion_id
            ):
                return r["score"]
        return 5.0

    def _rebuild_scores_grid(self):
        columns = [
            (index, expert, criterion)
            for index, expert in enumerate(self._experts)
            for criterion in self._criteria
        ]
        self.scores_table.setRowCount(len(self._alternatives))
        self.scores_table.setColumnCount(len(columns))
        self.scores_table.setHorizontalHeaderLabels(
            [f"Э{index + 1} / {c['name']}" for index, _e, c in columns]
        )
        self.scores_table.setVerticalHeaderLabels([a["name"] for a in self._alternatives])

        existing = list(list_alternative_scores(self._session_id)) if self._session_id else []

        for row, alternative in enumerate(self._alternatives):
            for col, (_index, expert, criterion) in enumerate(columns):
                value = self._existing_score_value(expert["id"], alternative["id"], criterion["id"], existing)
                box = _spinbox(0.0, 10.0, value)
                self.scores_table.setCellWidget(row, col, box)

    def _persist_grids(self):
        judgment_rows = []
        pairs = [
            (self._criteria[i], self._criteria[j])
            for i in range(len(self._criteria))
            for j in range(i + 1, len(self._criteria))
        ]
        for row, (a, b) in enumerate(pairs):
            for col, expert in enumerate(self._experts):
                box = self.judgments_table.cellWidget(row, col)
                if box is not None:
                    judgment_rows.append((expert["id"], a["id"], b["id"], box.value()))
        replace_criteria_judgments(self._session_id, judgment_rows)

        score_rows = []
        columns = [(expert, criterion) for expert in self._experts for criterion in self._criteria]
        for row, alternative in enumerate(self._alternatives):
            for col, (expert, criterion) in enumerate(columns):
                box = self.scores_table.cellWidget(row, col)
                if box is not None:
                    score_rows.append((expert["id"], alternative["id"], criterion["id"], box.value()))
        replace_alternative_scores(self._session_id, score_rows)

    def _calculate(self):
        self._persist_grids()
        try:
            result = run_evaluation(self._session_id)
        except ExpertEvaluationError as exc:
            QMessageBox.warning(self, "Недостаточно данных", str(exc))
            return

        self._criteria = list(list_criteria(self._session_id))
        self._rebuild_criteria_table()
        self._refresh_results_table()
        self._show_explanation(result)

    def _refresh_results_table(self):
        rows = list(list_results(self._session_id))
        self.results_table.setRowCount(len(rows))
        for row, r in enumerate(rows):
            self.results_table.setItem(row, 0, QTableWidgetItem(r["alternative_name"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(f"{r['score']:.2f}"))
            self.results_table.setItem(row, 2, QTableWidgetItem(str(r["rank"])))

        if rows:
            fired = (rows[0]["triggered_rules"] or "").splitlines()
            weights = {c["name"]: c["weight"] for c in self._criteria if c["weight"] is not None}
            self._show_explanation(
                {
                    "ranked": [(r["alternative_name"], r["score"]) for r in rows],
                    "weights": weights,
                    "cr": None,
                    "fired_rules": fired,
                }
            )

    def _show_explanation(self, result: dict):
        lines = []
        if result["ranked"]:
            top_name, top_score = result["ranked"][0]
            lines.append(f"Рекомендуется: {top_name} (балл {top_score:.2f})")
        lines.append("")
        lines.append("Веса критериев:")
        for name, weight in result["weights"].items():
            lines.append(f"  {name}: {weight:.3f}")
        if result.get("cr") is not None:
            lines.append("")
            lines.append(f"Коэффициент согласованности (CR): {result['cr']:.3f}")
        if result["fired_rules"]:
            lines.append("")
            lines.append("Сработавшие правила:")
            for rule in result["fired_rules"]:
                lines.append(f"  • {rule}")
        self.explanation.setPlainText("\n".join(lines))
