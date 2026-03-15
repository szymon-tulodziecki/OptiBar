"""
gui_algobar.py
Uruchomienie:  python gui_algobar.py
"""
import sys, json, csv, argparse
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt, QRectF, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QPainterPath

# ── Dane surowców ──────────────────────────────────────────────────────────────
ING = {
    "izolat": {"label": "Izolat serwatki",     "protein": 0.90, "fat": 0.00, "price": 18.00, "min": 10, "max": 40, "color": "#1565C0"},
    "pasta":  {"label": "Pasta orzechowa",     "protein": 0.25, "fat": 0.50, "price":  6.00, "min": 15, "max": 40, "color": "#BF360C"},
    "syrop":  {"label": "Syrop ryżowy",        "protein": 0.00, "fat": 0.00, "price":  2.50, "min": 15, "max": 35, "color": "#1B5E20"},
    "quinoa": {"label": "Ekspandowana quinoa", "protein": 0.14, "fat": 0.06, "price":  5.50, "min":  5, "max": 25, "color": "#4A148C"},
}
KEYS        = list(ING.keys())
MIN_PROTEIN = 20.0
MAX_FAT     = 20.0
BAR_WEIGHT  = 100.0

def calc(r):
    cost = prot = fat = 0.0
    for k in KEYS:
        cost += r[k] * ING[k]["price"] / 100.0
        prot += r[k] * ING[k]["protein"]
        fat  += r[k] * ING[k]["fat"]
    total = sum(r[k] for k in KEYS)
    ok = (prot >= MIN_PROTEIN and fat <= MAX_FAT
          and abs(total - BAR_WEIGHT) <= 0.5
          and all(ING[k]["min"] <= r[k] <= ING[k]["max"] for k in KEYS))
    return {"cost": cost, "protein": prot, "fat": fat, "total": total, "ok": ok}

# ── Styl ───────────────────────────────────────────────────────────────────────
SS = """
QMainWindow, QWidget { background: #F5F5F5; color: #212121; font-family: Segoe UI; font-size: 13px; }
QTabWidget::pane { border: 1px solid #BDBDBD; background: #FFFFFF; }
QTabBar::tab { background: #EEEEEE; color: #757575; padding: 10px 26px; font-size: 12px; font-weight: 600; border-bottom: 3px solid transparent; }
QTabBar::tab:selected { background: #FFFFFF; color: #1565C0; border-bottom: 3px solid #1565C0; }
QTabBar::tab:hover:!selected { background: #E0E0E0; color: #212121; }
QPushButton { background: #1565C0; color: white; border: none; border-radius: 4px; padding: 8px 20px; font-size: 12px; font-weight: 600; }
QPushButton:hover { background: #1976D2; }
QPushButton:pressed { background: #0D47A1; }
QScrollBar:vertical { background: #F5F5F5; width: 8px; }
QScrollBar::handle:vertical { background: #BDBDBD; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTableWidget { background: #FFFFFF; color: #212121; border: 1px solid #BDBDBD; gridline-color: #E0E0E0; }
QHeaderView::section { background: #1565C0; color: white; padding: 8px 12px; border: none; font-size: 11px; font-weight: 700; }
QTableWidget::item:selected { background: #BBDEFB; color: #212121; }
QLabel { color: #212121; }
"""

# ── Karta statystyki ───────────────────────────────────────────────────────────
class Card(QWidget):
    def __init__(self, title, value, unit="", color="#1565C0", note="", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(150)
        l = QVBoxLayout(self)
        l.setContentsMargins(16, 12, 16, 12)
        l.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet("color:#757575; font-size:10px; font-weight:700;")
        l.addWidget(t)
        row = QHBoxLayout(); row.setSpacing(4)
        self.v = QLabel(value)
        self.v.setStyleSheet(f"color:{color}; font-size:26px; font-weight:800;")
        row.addWidget(self.v)
        if unit:
            u = QLabel(unit)
            u.setStyleSheet("color:#9E9E9E; font-size:12px; margin-top:8px;")
            row.addWidget(u, 0, Qt.AlignBottom)
        row.addStretch()
        l.addLayout(row)
        if note:
            n = QLabel(note)
            n.setStyleSheet("color:#9E9E9E; font-size:10px;")
            l.addWidget(n)

    def set(self, v, color=None):
        self.v.setText(v)
        if color:
            self.v.setStyleSheet(f"color:{color}; font-size:26px; font-weight:800;")

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#E0E0E0"), 1))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5), 8, 8)
        p.end()
        super().paintEvent(e)


# ── Wskaźnik makro ─────────────────────────────────────────────────────────────
class Wskaznik(QWidget):
    def __init__(self, title, val, limit, unit, higher_is_worse, parent=None):
        super().__init__(parent)
        self.limit = limit; self.hiw = higher_is_worse; self.unit = unit
        self.setFixedHeight(74)
        l = QVBoxLayout(self); l.setContentsMargins(14,8,14,8); l.setSpacing(3)
        top = QHBoxLayout()
        tl = QLabel(title)
        tl.setStyleSheet("color:#757575; font-size:11px; font-weight:700;")
        top.addWidget(tl); top.addStretch()
        lim_str = f"{'maks' if higher_is_worse else 'min'} {limit:.0f} {unit}"
        ll = QLabel(lim_str)
        ll.setStyleSheet("color:#9E9E9E; font-size:10px;")
        top.addWidget(ll)
        l.addLayout(top)
        self.val_lbl = QLabel()
        self.val_lbl.setStyleSheet("font-size:20px; font-weight:800;")
        l.addWidget(self.val_lbl)
        self.update_val(val)

    def update_val(self, v):
        ok = (v <= self.limit) if self.hiw else (v >= self.limit)
        color = "#2E7D32" if ok else "#C62828"
        self.val_lbl.setStyleSheet(f"color:{color}; font-size:20px; font-weight:800;")
        self.val_lbl.setText(f"{v:.2f} {self.unit}")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#E0E0E0"),1)); p.setBrush(QColor("#FAFAFA"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5), 6, 6)
        p.end(); super().paintEvent(e)


# ── KLUCZOWY WIDGET: składnik z paskiem porównania + suwak w jednym ────────────
#
#  ┌─────────────────────────────────────────────────────────────────────┐
#  │ Izolat serwatki                              Optimum: 10.0 g        │
#  │ ████████░░░░░░░░░░░░░░░░░░░░░░░░░  ← niebieski = optimum HS        │
#  │ ████████████░░░░░░░░░░░░░░░░░░░░░  ← kolor składnika = twoja        │
#  │ [10g]  ────────────●──────────  [40g]        Twoja: 22.5 g  +12.5g │
#  └─────────────────────────────────────────────────────────────────────┘

class IngControl(QWidget):
    """
    Jeden widget na składnik.
    Górna część: dwa paski (optimum HS + twoja wartość) — wizualne porównanie.
    Dolna część: suwak do zmiany wartości + limity min/max.
    """
    def __init__(self, key, opt_val, init_val, on_change, parent=None):
        super().__init__(parent)
        self.key     = key
        self.opt     = opt_val
        self.current = init_val
        self.lo      = ING[key]["min"]
        self.hi      = ING[key]["max"]
        self.color   = ING[key]["color"]
        self.cb      = on_change
        self.setMinimumHeight(130)
        self.setMaximumHeight(130)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 6, 0, 4)
        outer.setSpacing(8)

        # Paski rysowane jako custom widget (górna część)
        self.bars_widget = _Bars(self.key, self.opt, self.current)
        self.bars_widget.setFixedHeight(60)
        outer.addWidget(self.bars_widget)

        # Suwak (dolna część)
        sl_row = QHBoxLayout()
        sl_row.setContentsMargins(0, 2, 0, 0)
        sl_row.setSpacing(8)

        lo_lbl = QLabel(f"{self.lo} g")
        lo_lbl.setStyleSheet("color:#9E9E9E; font-size:10px;")
        lo_lbl.setFixedWidth(30)
        lo_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        sl_row.addWidget(lo_lbl)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(self.lo * 10), int(self.hi * 10))
        self.slider.setValue(int(self.current * 10))
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height:5px; background:#BDBDBD; border-radius:2px; }}
            QSlider::sub-page:horizontal {{ background:{self.color}; border-radius:2px; }}
            QSlider::handle:horizontal {{
                width:16px; height:16px; margin:-5px 0;
                background:{self.color}; border-radius:8px; border:2px solid white;
            }}
        """)
        self.slider.valueChanged.connect(self._on_slide)
        sl_row.addWidget(self.slider, 1)

        hi_lbl = QLabel(f"{self.hi} g")
        hi_lbl.setStyleSheet("color:#9E9E9E; font-size:10px;")
        hi_lbl.setFixedWidth(30)
        sl_row.addWidget(hi_lbl)

        outer.addLayout(sl_row)

    def _on_slide(self, v):
        self.current = v / 10.0
        self.bars_widget.set_current(self.current)
        self.cb(self.key, self.current)

    def reset(self):
        self.current = self.opt
        self.slider.blockSignals(True)
        self.slider.setValue(int(self.opt * 10))
        self.slider.blockSignals(False)
        self.bars_widget.set_current(self.opt)


class _Bars(QWidget):
    """Rysuje dwa paski: optimum HS (szary/niebieski) i bieżący (kolor składnika)."""
    def __init__(self, key, opt, current, parent=None):
        super().__init__(parent)
        self.key     = key
        self.opt     = opt
        self.current = current
        self.lo      = ING[key]["min"]
        self.hi      = ING[key]["max"]
        self.color   = ING[key]["color"]

    def set_current(self, v):
        self.current = v
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()

        # Kolumny:  [nazwa 210] [etykieta 72] [pasek ...] [wartość 150]
        NW = 210   # szerokość nazwy składnika
        EW = 72    # szerokość etykiety (Optimum / Twoja)
        VW = 150   # szerokość wartości po prawej
        BH = 18    # wysokość paska
        bx = NW + EW
        bw = W - NW - EW - VW - 8
        rng = self.hi - self.lo

        def frac(v):
            return max(0.0, min(1.0, (v - self.lo) / rng))

        diff = self.current - self.opt
        if abs(diff) <= 1.5:
            user_color = QColor("#2E7D32")
        elif abs(diff) <= 5.0:
            user_color = QColor("#F57C00")
        else:
            user_color = QColor("#C62828")

        # Wiersz 1: Optimum HS
        y1 = 4

        # Nazwa składnika (span obu wierszy, wyśrodkowana)
        p.setPen(QColor(self.color))
        p.setFont(QFont("Segoe UI", 12, QFont.Bold))
        p.drawText(0, 0, NW, H, Qt.AlignVCenter | Qt.AlignLeft, ING[self.key]["label"])

        # Etykieta "Optimum"
        p.setPen(QColor("#1565C0"))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(NW, y1, EW - 4, BH, Qt.AlignVCenter | Qt.AlignRight, "Optimum")

        # Pasek Optimum
        p.setPen(Qt.NoPen); p.setBrush(QColor("#E3F2FD"))
        p.drawRoundedRect(QRectF(bx, y1, bw, BH), BH/2, BH/2)
        fw1 = bw * frac(self.opt)
        if fw1 > 0:
            p.setBrush(QColor("#1565C0"))
            p.drawRoundedRect(QRectF(bx, y1, fw1, BH), BH/2, BH/2)

        # Wartość Optimum
        p.setPen(QColor("#1565C0"))
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(bx + bw + 6, y1, VW, BH, Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self.opt:.1f} g")

        # Wiersz 2: Twoja wartość
        y2 = y1 + BH + 6

        # Etykieta "Twoja"
        p.setPen(user_color)
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(NW, y2, EW - 4, BH, Qt.AlignVCenter | Qt.AlignRight, "Twoja")

        # Pasek Twoja
        p.setPen(Qt.NoPen); p.setBrush(QColor("#F5F5F5"))
        p.drawRoundedRect(QRectF(bx, y2, bw, BH), BH/2, BH/2)
        fw2 = bw * frac(self.current)
        if fw2 > 0:
            p.setBrush(user_color)
            p.drawRoundedRect(QRectF(bx, y2, fw2, BH), BH/2, BH/2)

        # Wartość Twoja + różnica
        sign = "+" if diff >= 0 else ""
        p.setPen(user_color)
        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(bx + bw + 6, y2, VW, BH, Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self.current:.1f} g  ({sign}{diff:.1f})")

        p.end()


# ── Wykres zbieżności ─────────────────────────────────────────────────────────
class Wykres(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data; self._n = 0
        self._step = max(1, len(data) // 80)
        self._t = QTimer(self); self._t.timeout.connect(self._tick)
        self.setMinimumHeight(260)
        QTimer.singleShot(300, self.replay)

    def replay(self):
        self._n = 0; self._t.start(16)

    def _tick(self):
        self._n = min(len(self.data), self._n + self._step * 5)
        self.update()
        if self._n >= len(self.data): self._t.stop()

    def paintEvent(self, e):
        if not self.data: return
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        W, H = self.width(), self.height()
        PL, PR, PT, PB = 72, 20, 20, 42
        sub  = self.data[:max(1, self._n)]
        ymin = min(sub) * 0.998
        ymax = max(sub[:1]) * 1.002 if sub else ymin + 1
        cw = W - PL - PR; ch = H - PT - PB

        p.setPen(Qt.NoPen); p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(0, 0, W, H, 8, 8)
        p.setPen(QPen(QColor("#E0E0E0"), 1))
        p.drawRoundedRect(QRectF(0,0,W,H).adjusted(.5,.5,-.5,-.5), 8, 8)

        def px(i, v):
            x = PL + (i / max(len(self.data)-1, 1)) * cw
            y = PT + ch - (v - ymin) / max(ymax - ymin, 1e-9) * ch
            return x, y

        p.setFont(QFont("Segoe UI", 8))
        for gi in range(5):
            gy = PT + gi * ch / 4
            p.setPen(QPen(QColor("#EEEEEE"), 1))
            p.drawLine(PL, int(gy), W - PR, int(gy))
            val = ymax - gi * (ymax - ymin) / 4
            p.setPen(QColor("#9E9E9E"))
            p.drawText(0, int(gy)-7, PL-4, 14, Qt.AlignRight|Qt.AlignVCenter, f"{val:.4f}")

        if len(sub) >= 2:
            path = QPainterPath()
            x0, y0 = px(0, sub[0])
            path.moveTo(x0, PT+ch); path.lineTo(x0, y0)
            for i in range(1, len(sub)):
                xi, yi = px(i, sub[i]); path.lineTo(xi, yi)
            xn, _ = px(len(sub)-1, sub[-1])
            path.lineTo(xn, PT+ch); path.closeSubpath()
            grad = QLinearGradient(0, PT, 0, PT+ch)
            c1 = QColor("#1565C0"); c1.setAlpha(40)
            c2 = QColor("#1565C0"); c2.setAlpha(0)
            grad.setColorAt(0, c1); grad.setColorAt(1, c2)
            p.setPen(Qt.NoPen); p.setBrush(grad); p.drawPath(path)

            line = QPainterPath()
            x0, y0 = px(0, sub[0]); line.moveTo(x0, y0)
            for i in range(1, len(sub)):
                xi, yi = px(i, sub[i]); line.lineTo(xi, yi)
            p.setPen(QPen(QColor("#1565C0"), 2)); p.setBrush(Qt.NoBrush)
            p.drawPath(line)

        p.setPen(QPen(QColor("#BDBDBD"), 1))
        p.drawLine(PL, PT, PL, PT+ch); p.drawLine(PL, PT+ch, W-PR, PT+ch)
        p.setFont(QFont("Segoe UI", 8)); p.setPen(QColor("#9E9E9E"))
        for ti in range(6):
            idx = int(ti * len(self.data) / 5)
            tx = PL + (idx / max(len(self.data)-1, 1)) * cw
            p.drawText(int(tx)-25, PT+ch+8, 50, 14, Qt.AlignHCenter, f"{idx:,}")
        p.drawText(PL, PT+ch+24, cw, 14, Qt.AlignHCenter, "Iteracja")
        p.save(); p.translate(14, PT+ch//2); p.rotate(-90)
        p.drawText(-40, -5, 80, 14, Qt.AlignHCenter, "Koszt [PLN]"); p.restore()
        p.end()


# ── Zakładka 1: Wynik + porównanie ze suwakami ─────────────────────────────────
class TabWynik(QWidget):
    def __init__(self, hs, best_rnd, parent=None):
        super().__init__(parent)
        self.opt = hs["best_recipe"]
        self.m   = calc(self.opt)
        rnd_keys = {k: best_rnd[k] for k in KEYS if k in best_rnd} if best_rnd else {}
        self.rnd = rnd_keys if rnd_keys else {k: ING[k]["min"] for k in KEYS}
        self.usr = dict(self.opt)
        self._build()

    def _build(self):
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame)
        ol = QVBoxLayout(self); ol.setContentsMargins(0,0,0,0); ol.addWidget(sa)
        root = QWidget(); sa.setWidget(root)
        L = QVBoxLayout(root); L.setContentsMargins(28, 24, 28, 28); L.setSpacing(20)

        # ── Tytuł ──────────────────────────────────────────────
        h = QLabel("Wynik optymalny — Harmony Search")
        h.setStyleSheet("color:#1565C0; font-size:18px; font-weight:800;")
        L.addWidget(h)

        # ── Karty statystyk HS ────────────────────────────────
        rnd_m   = calc(self.rnd)
        saved   = rnd_m["cost"] - self.m["cost"]
        saved_p = saved / rnd_m["cost"] * 100 if rnd_m["cost"] else 0
        fc      = "#2E7D32" if self.m["ok"] else "#C62828"

        row1 = QHBoxLayout(); row1.setSpacing(10)
        self.c_cost = Card("Koszt optymalny",   f"{self.m['cost']:.4f}", "PLN/100g", "#1565C0")
        self.c_prot = Card("Białko",            f"{self.m['protein']:.2f}", "g", "#1565C0", f"min {MIN_PROTEIN:.0f} g")
        self.c_fat  = Card("Tłuszcz",           f"{self.m['fat']:.2f}", "g",    "#BF360C", f"max {MAX_FAT:.0f} g")
        self.c_save = Card("Oszczędność vs MC", f"{saved:.4f}", "PLN",           "#2E7D32", f"−{saved_p:.1f}% taniej")
        self.c_feas = Card("Spełnia ograniczenia", "TAK" if self.m["ok"] else "NIE", "", fc)
        for c in [self.c_cost, self.c_prot, self.c_fat, self.c_save, self.c_feas]:
            row1.addWidget(c)
        L.addLayout(row1)

        L.addWidget(self._sep())

        # ── Tabela składu ──────────────────────────────────────
        L.addWidget(self._lbl("Skład optymalnej receptury"))
        tbl = QTableWidget(len(KEYS)+1, 5)
        tbl.setHorizontalHeaderLabels(["Składnik", "Masa [g]", "Białko [g]", "Tłuszcz [g]", "Koszt [PLN]"])
        tbl.verticalHeader().setVisible(False)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.setMaximumHeight(182)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tot = [0.0]*4
        for ri, k in enumerate(KEYS):
            m2 = ING[k]; v = self.opt[k]
            pr = v*m2["protein"]; fa = v*m2["fat"]; co = v*m2["price"]/100
            tot[0]+=v; tot[1]+=pr; tot[2]+=fa; tot[3]+=co
            for ci, txt in enumerate([m2["label"], f"{v:.2f}", f"{pr:.2f}", f"{fa:.2f}", f"{co:.4f}"]):
                it = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignCenter if ci else Qt.AlignVCenter|Qt.AlignLeft)
                if ci == 0: it.setForeground(QColor(m2["color"]))
                tbl.setItem(ri, ci, it)
        for ci, txt in enumerate(["RAZEM", f"{tot[0]:.2f}", f"{tot[1]:.2f}", f"{tot[2]:.2f}", f"{tot[3]:.4f}"]):
            it = QTableWidgetItem(txt)
            it.setTextAlignment(Qt.AlignCenter)
            it.setForeground(QColor("#1565C0"))
            f2 = QFont(); f2.setBold(True); it.setFont(f2)
            tbl.setItem(len(KEYS), ci, it)
        L.addWidget(tbl)

        L.addWidget(self._sep())

        # ── Porównanie + suwaki — ZINTEGROWANE ────────────────
        L.addWidget(self._lbl("Zmień skład i porównaj z optimum"))
        info = QLabel(
            "Górny pasek (niebieski) = optimum HS.   "
            "Dolny pasek = Twoja wartość.   "
            "Przeciągnij suwak aby zmienić ilość składnika."
        )
        info.setStyleSheet("color:#757575; font-size:11px;")
        info.setWordWrap(True)
        L.addWidget(info)

        self.controls = {}
        for k in KEYS:
            ctrl = IngControl(k, self.opt[k], self.usr[k], self._change)
            self.controls[k] = ctrl
            L.addWidget(ctrl)
            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color:#EEEEEE;")
            L.addWidget(sep)

        # ── Wyniki Twojej receptury na żywo ───────────────────
        L.addWidget(self._lbl("Wyniki Twojej receptury — aktualizacja na żywo"))

        wsk_row = QHBoxLayout(); wsk_row.setSpacing(10)
        self.w_prot = Wskaznik("Białko",       self.m["protein"], MIN_PROTEIN, "g",   False)
        self.w_fat  = Wskaznik("Tłuszcz",      self.m["fat"],     MAX_FAT,     "g",   True)
        self.w_cost = Wskaznik("Koszt",        self.m["cost"],    99,          "PLN", True)
        self.w_mass = Wskaznik("Masa łączna",  self.m["total"],   100.5,       "g",   True)
        for w in [self.w_prot, self.w_fat, self.w_cost, self.w_mass]:
            wsk_row.addWidget(w)
        L.addLayout(wsk_row)

        mu = calc(self.usr)
        diff = mu["cost"] - self.m["cost"]
        sign = "+" if diff >= 0 else ""
        fc2  = "#2E7D32" if mu["ok"] else "#C62828"

        row2 = QHBoxLayout(); row2.setSpacing(10)
        self.u_cost = Card("Twój koszt",        f"{mu['cost']:.4f}",    "PLN/100g", "#F57C00")
        self.u_prot = Card("Twoje białko",      f"{mu['protein']:.2f}", "g",        "#1565C0",  f"min {MIN_PROTEIN:.0f} g")
        self.u_fat  = Card("Twój tłuszcz",     f"{mu['fat']:.2f}",     "g",        "#BF360C",  f"max {MAX_FAT:.0f} g")
        self.u_diff = Card("Różnica do optimum", f"{sign}{diff:.4f}",   "PLN",
                           "#C62828" if diff > 0 else "#2E7D32")
        self.u_feas = Card("Ograniczenia",      "TAK" if mu["ok"] else "NIE", "", fc2)
        for c in [self.u_cost, self.u_prot, self.u_fat, self.u_diff, self.u_feas]:
            row2.addWidget(c)
        L.addLayout(row2)

        br = QHBoxLayout(); br.addStretch()
        rb = QPushButton("Resetuj do wartości optymalnych")
        rb.clicked.connect(self._reset)
        br.addWidget(rb)
        L.addLayout(br)
        L.addStretch()

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("color:#E0E0E0;"); return f

    def _lbl(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("color:#424242; font-size:12px; font-weight:700;")
        return l

    def _change(self, key, val):
        self.usr[key] = val
        mu   = calc(self.usr)
        diff = mu["cost"] - self.m["cost"]
        sign = "+" if diff >= 0 else ""
        self.w_prot.update_val(mu["protein"])
        self.w_fat.update_val(mu["fat"])
        self.w_cost.update_val(mu["cost"])
        self.w_mass.update_val(mu["total"])
        self.u_cost.set(f"{mu['cost']:.4f}", "#F57C00")
        self.u_prot.set(f"{mu['protein']:.2f}",
                        "#1565C0" if mu["protein"] >= MIN_PROTEIN else "#C62828")
        self.u_fat.set(f"{mu['fat']:.2f}",
                       "#BF360C" if mu["fat"] <= MAX_FAT else "#C62828")
        self.u_diff.set(f"{sign}{diff:.4f}", "#C62828" if diff > 0 else "#2E7D32")
        fc = "#2E7D32" if mu["ok"] else "#C62828"
        self.u_feas.set("TAK" if mu["ok"] else "NIE", fc)

    def _reset(self):
        self.usr = dict(self.opt)
        for k in KEYS:
            self.controls[k].reset()
        m = self.m
        self.w_prot.update_val(m["protein"]); self.w_fat.update_val(m["fat"])
        self.w_cost.update_val(m["cost"]);    self.w_mass.update_val(m["total"])
        self.u_cost.set(f"{m['cost']:.4f}", "#F57C00")
        self.u_prot.set(f"{m['protein']:.2f}", "#1565C0")
        self.u_fat.set(f"{m['fat']:.2f}", "#BF360C")
        self.u_diff.set("0.0000", "#2E7D32")
        self.u_feas.set("TAK", "#2E7D32")


# ── Zakładka 2: Zbieżność ─────────────────────────────────────────────────────
class TabZbieznosc(QWidget):
    def __init__(self, hs, parent=None):
        super().__init__(parent)
        conv = hs.get("zbieznosc", hs.get("convergence", [])); params = hs.get("parametry", hs.get("params", {}))
        L = QVBoxLayout(self); L.setContentsMargins(28,22,28,22); L.setSpacing(16)
        h = QLabel("Zbieżność algorytmu Harmony Search")
        h.setStyleSheet("color:#1565C0; font-size:18px; font-weight:800;")
        L.addWidget(h)

        pr = QHBoxLayout(); pr.setSpacing(10)
        for sym, desc in [("HMS","pamięć harmonii"),("HMCR","uwzgl. pamięci"),
                           ("PAR","korekta dźwięku"),("BW","pasmo"),("NI","iteracji")]:
            f = QFrame()
            f.setStyleSheet("background:#FFFFFF; border:1px solid #E0E0E0; border-radius:6px;")
            cl = QVBoxLayout(f); cl.setContentsMargins(14,10,14,10); cl.setSpacing(2)
            sl = QLabel(sym); sl.setStyleSheet("color:#1565C0;font-size:15px;font-weight:800;")
            vl = QLabel(str(params.get(sym, "—"))); vl.setStyleSheet("color:#212121;font-size:13px;")
            dl = QLabel(desc); dl.setStyleSheet("color:#9E9E9E;font-size:9px;")
            cl.addWidget(sl); cl.addWidget(vl); cl.addWidget(dl)
            pr.addWidget(f)
        L.addLayout(pr)

        if conv:
            sr = QHBoxLayout(); sr.setSpacing(10)
            for title, val, unit, color in [
                ("Koszt startowy", f"{conv[0]:.4f}",  "PLN", "#C62828"),
                ("Koszt końcowy",  f"{conv[-1]:.4f}", "PLN", "#2E7D32"),
                ("Poprawa",        f"{conv[0]-conv[-1]:.4f}", "PLN", "#E65100"),
                ("Redukcja",       f"{(1-conv[-1]/conv[0])*100:.1f}", "%", "#1565C0"),
            ]:
                sr.addWidget(Card(title, val, unit, color))
            L.addLayout(sr)

        self.wyk = Wykres(conv); L.addWidget(self.wyk, 1)
        br = QHBoxLayout(); br.addStretch()
        btn = QPushButton("Odtwórz animację"); btn.clicked.connect(self.wyk.replay)
        br.addWidget(btn); L.addLayout(br)


# ── Zakładka 3: Monte Carlo ───────────────────────────────────────────────────
class TabMC(QWidget):
    def __init__(self, csv_path, hs_cost, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path; self.hs_cost = hs_cost
        L = QVBoxLayout(self); L.setContentsMargins(28,22,28,22); L.setSpacing(14)
        h = QLabel("Monte Carlo — receptury.csv")
        h.setStyleSheet("color:#1565C0; font-size:18px; font-weight:800;")
        L.addWidget(h)
        self.sr = QHBoxLayout(); L.addLayout(self.sr)
        self.tbl = QTableWidget(); self.tbl.setAlternatingRowColors(True)
        L.addWidget(self.tbl, 1)
        br = QHBoxLayout()
        btn = QPushButton("Wczytaj receptury.csv"); btn.clicked.connect(self._load)
        br.addWidget(btn); br.addStretch(); L.addLayout(br)
        if csv_path and Path(csv_path).exists(): self._load(csv_path)

    def _load(self, path=None):
        if not path or isinstance(path, bool):
            path, _ = QFileDialog.getOpenFileName(self, "receptury.csv", "", "CSV (*.csv)")
        if not path: return
        try:
            with open(path, encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            if not rows: return
            headers = list(rows[0].keys()); display = rows[:3000]
            self.tbl.setColumnCount(len(headers)); self.tbl.setRowCount(len(display))
            self.tbl.setHorizontalHeaderLabels(headers)
            self.tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            cc = headers.index("koszt_PLN") if "koszt_PLN" in headers else -1
            fc = headers.index("spelnia_ograniczenia") if "spelnia_ograniczenia" in headers else -1
            fr = [r for r in rows if r.get("spelnia_ograniczenia") == "1"]
            costs = [float(r["koszt_PLN"]) for r in fr if r.get("koszt_PLN")]
            mc = min(costs) if costs else None
            for ri, row in enumerate(display):
                isf = row.get("spelnia_ograniczenia") == "1"
                for ci, key in enumerate(headers):
                    it = QTableWidgetItem(row[key])
                    it.setTextAlignment(Qt.AlignCenter)
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                    if fc == ci:
                        it.setForeground(QColor("#2E7D32" if row[key]=="1" else "#C62828"))
                    if cc == ci and isf and mc:
                        try:
                            if abs(float(row[key]) - mc) < 0.0001:
                                it.setForeground(QColor("#E65100"))
                                it.setBackground(QColor("#FFF3E0"))
                        except: pass
                    self.tbl.setItem(ri, ci, it)
            while self.sr.count():
                w = self.sr.takeAt(0)
                if w.widget(): w.widget().deleteLater()
            for title, val, unit, color in [
                ("Prób łącznie",  f"{len(rows):,}",  "",    "#1565C0"),
                ("Spełnia ogr.",  f"{len(fr):,}",    "",    "#2E7D32"),
                ("% spełnia",     f"{len(fr)/len(rows)*100:.1f}", "%", "#F57C00"),
                ("Min koszt MC",  f"{mc:.4f}" if mc else "—", "PLN", "#C62828"),
                ("Koszt HS",      f"{self.hs_cost:.4f}", "PLN", "#2E7D32"),
                ("Różnica",       f"{mc-self.hs_cost:.4f}" if mc else "—", "PLN", "#1565C0"),
            ]:
                self.sr.addWidget(Card(title, val, unit, color))
        except Exception as ex:
            QMessageBox.warning(self, "Błąd", str(ex))


# ── Główne okno ───────────────────────────────────────────────────────────────
class App(QMainWindow):
    def __init__(self, jp, cp):
        super().__init__()
        self.setWindowTitle("ALGO-BAR — Optymalizacja receptury batona")
        self.resize(1280, 860); self.setStyleSheet(SS)
        self.jp = jp; self.cp = cp; self.hs = None; self.rnd = None
        self._load(); self._build()

    def _load(self):
        if self.jp and Path(self.jp).exists():
            with open(self.jp, encoding="utf-8") as f:
                self.hs = json.load(f)
        if self.cp and Path(self.cp).exists():
            try:
                best = None; bc = float("inf")
                with open(self.cp, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if row.get("spelnia_ograniczenia") == "1":
                            c = float(row.get("koszt_PLN", 999))
                            if c < bc: bc = c; best = row
                if best:
                    self.rnd = {k: float(best.get(k+"_g", 0)) for k in KEYS}
            except: pass

    def _build(self):
        cw = QWidget(); self.setCentralWidget(cw)
        root = QVBoxLayout(cw); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        hdr = QWidget(); hdr.setFixedHeight(50)
        hdr.setStyleSheet("background:#1565C0;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(24,0,24,0)
        logo = QLabel("ALGO-BAR")
        logo.setStyleSheet("color:white; font-size:16px; font-weight:900; letter-spacing:3px;")
        hl.addWidget(logo)
        sub = QLabel("Optymalizacja receptury — Harmony Search")
        sub.setStyleSheet("color:#BBDEFB; font-size:11px;")
        hl.addWidget(sub); hl.addStretch()
        btn = QPushButton("Wczytaj wynik_hs.json")
        btn.setStyleSheet("background:white; color:#1565C0; font-weight:700; border-radius:4px; padding:6px 16px;")
        btn.clicked.connect(self._open); hl.addWidget(btn)
        root.addWidget(hdr)

        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1); self._fill()

    def _fill(self):
        self.tabs.clear()
        if self.hs:
            self.tabs.addTab(TabWynik(self.hs, self.rnd), "Wynik optymalny + porównanie")
            self.tabs.addTab(TabZbieznosc(self.hs), "Zbieżność algorytmu")
        else:
            w = QWidget(); l = QVBoxLayout(w); l.setAlignment(Qt.AlignCenter)
            msg = QLabel("Brak danych.\n\nUruchom:\n  python hs_algobar.py\n\nlub wczytaj plik JSON.")
            msg.setStyleSheet("color:#9E9E9E; font-size:13px;"); msg.setAlignment(Qt.AlignCenter)
            l.addWidget(msg); self.tabs.addTab(w, "Wynik optymalny + porównanie")
        hc = self.hs.get("best_cost", 0.0) if self.hs else 0.0
        self.tabs.addTab(TabMC(self.cp, hc), "Monte Carlo")

    def _open(self):
        p, _ = QFileDialog.getOpenFileName(self, "wynik_hs.json", "", "JSON (*.json)")
        if p: self.jp = p; self._load(); self._fill()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", default="wynik_hs.json")
    p.add_argument("--csv",  default="receptury.csv")
    a = p.parse_args()
    app = QApplication(sys.argv)
    win = App(a.json, a.csv); win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()