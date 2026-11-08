from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation
from PySide6.QtWidgets import QFrame, QWidget


class Carousel(QFrame):
    """Горизонтальная карусель слотов фиксированной ширины — активный индекс всегда
    по центру видимой зоны, соседи уезжают в стороны и обрезаются границей виджета.
    Ровно та механика, что в Figma: translateX(W/2 - (i+0.5)*slot) с анимацией."""

    def __init__(self, slot_width: int, height: int, parent=None):
        super().__init__(parent)
        self.slot_width = slot_width
        self.setFixedHeight(height)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.track = QWidget(self)
        self.track.setFixedHeight(height)

        self._items: list[QWidget] = []
        self._index = 0
        self._animation = QPropertyAnimation(self.track, b"pos")
        self._animation.setDuration(280)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def set_items(self, widgets: list[QWidget]):
        for old in self._items:
            old.setParent(None)
            old.deleteLater()
        self._items = widgets
        self.track.setFixedWidth(max(len(widgets), 1) * self.slot_width)
        for k, w in enumerate(widgets):
            w.setParent(self.track)
            # до первого show() непривязанный виджет отдаёт дефолтный top-level размер
            # (например 480 в высоту) вместо реального — adjustSize() пересчитывает его
            # по sizeHint с учётом уже выставленных ограничений (fixedWidth и т.п.)
            w.adjustSize()
            w.move(
                k * self.slot_width + (self.slot_width - w.width()) // 2,
                (self.height() - w.height()) // 2,
            )
            w.show()
        self._index = min(self._index, max(len(widgets) - 1, 0))
        self._reposition(animate=False)

    def set_index(self, index: int, animate: bool = True):
        if not self._items:
            return
        self._index = max(0, min(index, len(self._items) - 1))
        self._reposition(animate=animate)

    def index(self) -> int:
        return self._index

    def items(self) -> list[QWidget]:
        return list(self._items)

    def _reposition(self, animate: bool):
        target_x = self.width() // 2 - int((self._index + 0.5) * self.slot_width)
        if animate:
            self._animation.stop()
            self._animation.setStartValue(self.track.pos())
            self._animation.setEndValue(QPoint(target_x, 0))
            self._animation.start()
        else:
            self.track.move(target_x, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition(animate=False)
