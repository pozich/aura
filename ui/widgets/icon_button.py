from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QPushButton


class CircleIconButton(QPushButton):
    """Кнопка-кружок с иконкой, нарисованной вручную через QPainter — не зависит от
    того, есть ли в системе шрифт с цветными эмодзи/спецсимволами (⏹▶⏸←→ на части
    систем попросту не рендерились — тот же корень проблемы, что был с текстом вкладок)."""

    def __init__(self, icon: str, size: int = 22, parent=None):
        super().__init__(parent)
        self._icon = icon  # "close" | "tag" | "play" | "pause" | "stop" | "prev" | "next"
        self.setFixedSize(size, size)
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

    def set_icon(self, icon: str):
        self._icon = icon
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        cx, cy = rect.center().x(), rect.center().y()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Qt.GlobalColor.black)
        painter.setOpacity(0.85 if self.underMouse() else 0.6)
        painter.drawEllipse(rect)
        painter.setOpacity(1.0)

        pen = QPen(Qt.GlobalColor.white)
        pen.setWidthF(max(1.4, rect.width() * 0.09))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._icon == "close":
            margin = rect.width() * 0.28
            painter.drawLine(
                QPointF(rect.left() + margin, rect.top() + margin),
                QPointF(rect.right() - margin, rect.bottom() - margin),
            )
            painter.drawLine(
                QPointF(rect.right() - margin, rect.top() + margin),
                QPointF(rect.left() + margin, rect.bottom() - margin),
            )

        elif self._icon == "tag":
            tag_rect = rect.adjusted(
                rect.width() * 0.2, rect.height() * 0.3, -rect.width() * 0.2, -rect.height() * 0.3
            )
            painter.drawRoundedRect(tag_rect, 2, 2)
            hole_radius = rect.width() * 0.05
            hole_center = QPointF(tag_rect.left() + hole_radius * 1.6, tag_rect.center().y())
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(hole_center, hole_radius, hole_radius)

        elif self._icon in ("prev", "next"):
            r = rect.width() * 0.22
            sign = -1 if self._icon == "prev" else 1
            painter.drawLine(QPointF(cx - sign * r * 0.6, cy - r), QPointF(cx + sign * r * 0.6, cy))
            painter.drawLine(QPointF(cx + sign * r * 0.6, cy), QPointF(cx - sign * r * 0.6, cy + r))

        elif self._icon == "play":
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(Qt.PenStyle.NoPen)
            w = rect.width() * 0.32
            h = rect.height() * 0.36
            triangle = QPolygonF(
                [QPointF(cx - w * 0.4, cy - h), QPointF(cx - w * 0.4, cy + h), QPointF(cx + w * 0.8, cy)]
            )
            painter.drawPolygon(triangle)

        elif self._icon == "pause":
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(Qt.PenStyle.NoPen)
            bar_w = rect.width() * 0.14
            bar_h = rect.height() * 0.5
            gap = rect.width() * 0.1
            painter.drawRect(QRectF(cx - gap - bar_w, cy - bar_h / 2, bar_w, bar_h))
            painter.drawRect(QRectF(cx + gap, cy - bar_h / 2, bar_w, bar_h))

        elif self._icon == "stop":
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(Qt.PenStyle.NoPen)
            s = rect.width() * 0.34
            painter.drawRoundedRect(QRectF(cx - s / 2, cy - s / 2, s, s), 1, 1)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)
