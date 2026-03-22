"""
gui_algobar.py  — Interaktywny baton składnikowy
Uruchomienie:  python gui_algobar.py [--json wynik_hs.json]
"""
import sys, json, argparse
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QFileDialog,
)
from PyQt5.QtCore import Qt, QRectF, QTimer, QPointF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QPainterPath, QCursor

ING = {
    "izolat": {"label": "Izolat serwatki",     "protein": 0.90, "fat": 0.00, "price": 18.00, "min": 10, "max": 40, "color": "#1976D2"},
    "pasta":  {"label": "Pasta orzechowa",     "protein": 0.25, "fat": 0.50, "price":  6.00, "min": 15, "max": 40, "color": "#D84315"},
    "syrop":  {"label": "Syrop ryżowy",        "protein": 0.00, "fat": 0.00, "price":  2.50, "min": 15, "max": 35, "color": "#388E3C"},
    "quinoa": {"label": "Ekspandowana quinoa", "protein": 0.14, "fat": 0.06, "price":  5.50, "min":  5, "max": 25, "color": "#7B1FA2"},
}
KEYS        = list(ING.keys())
MIN_PROTEIN = 20.0
MAX_FAT     = 20.0
BAR_WEIGHT  = 100.0
DRAG_ZONE   = 10

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

SS = """
QMainWindow, QWidget { background:#1A1A2E; color:#E0E0E0; font-family:'Segoe UI'; font-size:13px; }
QScrollArea { border:none; }
QPushButton {
    background:#1976D2; color:white; border:none; border-radius:6px;
    padding:9px 22px; font-size:12px; font-weight:700; letter-spacing:0.5px;
}
QPushButton:hover  { background:#1E88E5; }
QPushButton:pressed{ background:#1565C0; }
QPushButton#reset  { background:#37474F; }
QPushButton#reset:hover { background:#455A64; }
QPushButton#load   { background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.18); color:white; }
QPushButton#load:hover { background:rgba(255,255,255,0.16); }
QLabel { color:#E0E0E0; }
"""

class Card(QWidget):
    def __init__(self, title, value, unit="", color="#1976D2", note="", parent=None):
        super().__init__(parent)
        self.setMinimumWidth(130)
        l = QVBoxLayout(self); l.setContentsMargins(16,12,16,12); l.setSpacing(3)
        t = QLabel(title); t.setStyleSheet("color:#78909C;font-size:10px;font-weight:700;letter-spacing:.5px;")
        l.addWidget(t)
        row = QHBoxLayout(); row.setSpacing(4)
        self.v = QLabel(value)
        self.v.setStyleSheet(f"color:{color};font-size:24px;font-weight:800;")
        row.addWidget(self.v)
        if unit:
            u = QLabel(unit); u.setStyleSheet("color:#546E7A;font-size:11px;margin-top:6px;")
            row.addWidget(u, 0, Qt.AlignBottom)
        row.addStretch(); l.addLayout(row)
        if note:
            n = QLabel(note); n.setStyleSheet("color:#546E7A;font-size:10px;")
            l.addWidget(n)

    def set(self, v, color=None):
        self.v.setText(v)
        if color: self.v.setStyleSheet(f"color:{color};font-size:24px;font-weight:800;")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#263238"),1)); p.setBrush(QColor("#16213E"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),10,10)
        p.end(); super().paintEvent(e)


class BarWidget(QWidget):
    """
    Prostokąt podzielony na kolorowe segmenty.
    Przeciąganie granicy między segmentami zmienia ilości — suma zawsze 100 g.
    """
    changed = pyqtSignal(dict)

    BAR_H   = 120
    LABEL_H = 80

    def __init__(self, recipe: dict, parent=None):
        super().__init__(parent)
        self.recipe   = {k: recipe[k] for k in KEYS}
        self._drag    = None
        self._drag_x0 = 0
        self._fracs0  = []
        self.setMinimumHeight(self.BAR_H + self.LABEL_H + 24)
        self.setMouseTracking(True)

    @property
    def _bar_rect(self):
        m = 24
        return QRectF(m, 18, self.width() - 2*m, self.BAR_H)

    def _fracs(self):
        total = sum(self.recipe[k] for k in KEYS)
        total = max(total, 0.001)
        return [self.recipe[k] / total for k in KEYS]

    def _dividers_px(self):
        br = self._bar_rect
        fracs = self._fracs()
        xs = []
        acc = 0.0
        for f in fracs[:-1]:
            acc += f
            xs.append(br.left() + acc * br.width())
        return xs

    def _near_divider(self, x):
        for i, dx in enumerate(self._dividers_px()):
            if abs(x - dx) <= DRAG_ZONE:
                return i
        return None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            idx = self._near_divider(e.x())
            if idx is not None:
                self._drag    = idx
                self._drag_x0 = e.x()
                self._fracs0  = self._fracs()

    def mouseMoveEvent(self, e):
        if self._drag is None:
            near = self._near_divider(e.x())
            self.setCursor(QCursor(Qt.SplitHCursor if near is not None else Qt.ArrowCursor))
            return

        br  = self._bar_rect
        dx  = e.x() - self._drag_x0
        df  = dx / br.width()
        idx = self._drag
        fracs = list(self._fracs0)

        new_left  = fracs[idx]   + df
        new_right = fracs[idx+1] - df
        left_g  = new_left  * BAR_WEIGHT
        right_g = new_right * BAR_WEIGHT
        kl = KEYS[idx]; kr = KEYS[idx+1]

        if (left_g  < ING[kl]["min"] or left_g  > ING[kl]["max"] or
            right_g < ING[kr]["min"] or right_g > ING[kr]["max"]):
            return

        fracs[idx]   = new_left
        fracs[idx+1] = new_right
        for i, k in enumerate(KEYS):
            self.recipe[k] = fracs[i] * BAR_WEIGHT
        self.update()
        self.changed.emit(dict(self.recipe))

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.setCursor(QCursor(Qt.ArrowCursor))

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        br = self._bar_rect
        fracs = self._fracs()
        radius = 16

        # Cień
        shadow = QRectF(br).adjusted(4, 8, 4, 8)
        p.setPen(Qt.NoPen); p.setBrush(QColor(0,0,0,80))
        p.drawRoundedRect(shadow, radius, radius)

        # Segmenty
        x = br.left()
        for i, k in enumerate(KEYS):
            seg_w = fracs[i] * br.width()
            seg_r = QRectF(x, br.top(), seg_w, br.height())
            col   = QColor(ING[k]["color"])

            grad = QLinearGradient(0, br.top(), 0, br.bottom())
            grad.setColorAt(0, col.lighter(140))
            grad.setColorAt(0.5, col)
            grad.setColorAt(1, col.darker(140))
            p.setPen(Qt.NoPen); p.setBrush(grad)

            # Path con angoli arrotondati solo ai bordi
            full_path = QPainterPath()
            full_path.addRoundedRect(
                QRectF(br.left(), br.top(), br.width(), br.height()),
                radius, radius
            )
            clip = QPainterPath()
            clip.addRect(seg_r)
            p.drawPath(full_path.intersected(clip))

            # Shine
            shine = QLinearGradient(0, br.top(), 0, br.top() + br.height()*0.45)
            shine.setColorAt(0, QColor(255,255,255,55))
            shine.setColorAt(1, QColor(255,255,255,0))
            p.setBrush(shine)
            shine_clip = QPainterPath()
            shine_clip.addRect(QRectF(x, br.top(), seg_w, br.height()*0.45))
            p.drawPath(full_path.intersected(shine_clip))

            # Tekst wewnątrz
            if seg_w > 52:
                p.setPen(QColor(255,255,255,230))
                p.setFont(QFont("Segoe UI", 11, QFont.Bold))
                p.drawText(seg_r, Qt.AlignCenter, f"{self.recipe[k]:.1f}g")

            x += seg_w

        # Uchwyty granicy
        divs = self._dividers_px()
        for dx in divs:
            cy = br.center().y()
            # Linia przerywana
            p.setPen(QPen(QColor(255,255,255,100), 2, Qt.DashLine))
            p.drawLine(int(dx), int(br.top())+3, int(dx), int(br.bottom())-3)
            # Kółko
            p.setPen(Qt.NoPen); p.setBrush(QColor(255,255,255,240))
            p.drawEllipse(QPointF(dx, cy), 11, 11)
            # Strzałki
            p.setPen(QPen(QColor("#263238"), 2))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(int(dx)-11, int(cy)-11, 22, 22, Qt.AlignCenter, "⟺")

        # Etykiety pod batonem
        x = br.left()
        ly = int(br.bottom()) + 12
        for i, k in enumerate(KEYS):
            seg_w = fracs[i] * br.width()
            cx = x + seg_w / 2
            col = QColor(ING[k]["color"])

            # Kreska łącząca
            p.setPen(QPen(col.lighter(150), 1, Qt.DotLine))
            p.drawLine(int(cx), int(br.bottom())+2, int(cx), ly+2)

            lw = max(seg_w, 90)
            lx = cx - lw/2

            p.setPen(col.lighter(160))
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(QRectF(lx, ly, lw, 18), Qt.AlignHCenter, ING[k]["label"])

            p.setPen(QColor("#78909C"))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRectF(lx, ly+19, lw, 15), Qt.AlignHCenter,
                       f"{self.recipe[k]:.1f} g  ·  {fracs[i]*100:.0f}%")

            x += seg_w

        p.end()


class Wskaznik(QWidget):
    def __init__(self, title, val, limit, unit, higher_is_worse, parent=None):
        super().__init__(parent)
        self.limit = limit; self.hiw = higher_is_worse; self.unit = unit
        self.setFixedHeight(70)
        l = QVBoxLayout(self); l.setContentsMargins(14,8,14,8); l.setSpacing(3)
        top = QHBoxLayout()
        tl = QLabel(title); tl.setStyleSheet("color:#78909C;font-size:11px;font-weight:700;")
        top.addWidget(tl); top.addStretch()
        lim_str = f"{'maks' if higher_is_worse else 'min'} {limit:.0f} {unit}"
        ll = QLabel(lim_str); ll.setStyleSheet("color:#546E7A;font-size:10px;")
        top.addWidget(ll); l.addLayout(top)
        self.val_lbl = QLabel()
        self.val_lbl.setStyleSheet("font-size:20px;font-weight:800;")
        l.addWidget(self.val_lbl)
        self.update_val(val)

    def update_val(self, v):
        ok = (v <= self.limit) if self.hiw else (v >= self.limit)
        color = "#66BB6A" if ok else "#EF5350"
        self.val_lbl.setStyleSheet(f"color:{color};font-size:20px;font-weight:800;")
        self.val_lbl.setText(f"{v:.2f} {self.unit}")

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#263238"),1)); p.setBrush(QColor("#16213E"))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),8,8)
        p.end(); super().paintEvent(e)


class Wykres(QWidget):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data; self._n = 0
        self._step = max(1, len(data) // 80)
        self._t = QTimer(self); self._t.timeout.connect(self._tick)
        self.setMinimumHeight(240)
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
        ymin = min(sub)*0.998; ymax = max(sub[:1])*1.002 if sub else ymin+1
        cw = W-PL-PR; ch = H-PT-PB

        p.setPen(Qt.NoPen); p.setBrush(QColor("#16213E"))
        p.drawRoundedRect(0,0,W,H,10,10)
        p.setPen(QPen(QColor("#263238"),1))
        p.drawRoundedRect(QRectF(0,0,W,H).adjusted(.5,.5,-.5,-.5),10,10)

        def px(i,v):
            x=PL+(i/max(len(self.data)-1,1))*cw
            y=PT+ch-(v-ymin)/max(ymax-ymin,1e-9)*ch
            return x,y

        p.setFont(QFont("Segoe UI",8))
        for gi in range(5):
            gy=PT+gi*ch/4
            p.setPen(QPen(QColor("#263238"),1))
            p.drawLine(PL,int(gy),W-PR,int(gy))
            val=ymax-gi*(ymax-ymin)/4
            p.setPen(QColor("#546E7A"))
            p.drawText(0,int(gy)-7,PL-4,14,Qt.AlignRight|Qt.AlignVCenter,f"{val:.4f}")

        if len(sub)>=2:
            path=QPainterPath()
            x0,y0=px(0,sub[0]); path.moveTo(x0,PT+ch); path.lineTo(x0,y0)
            for i in range(1,len(sub)):
                xi,yi=px(i,sub[i]); path.lineTo(xi,yi)
            xn,_=px(len(sub)-1,sub[-1]); path.lineTo(xn,PT+ch); path.closeSubpath()
            grad=QLinearGradient(0,PT,0,PT+ch)
            c1=QColor("#1976D2"); c1.setAlpha(60)
            c2=QColor("#1976D2"); c2.setAlpha(0)
            grad.setColorAt(0,c1); grad.setColorAt(1,c2)
            p.setPen(Qt.NoPen); p.setBrush(grad); p.drawPath(path)

            line=QPainterPath()
            x0,y0=px(0,sub[0]); line.moveTo(x0,y0)
            for i in range(1,len(sub)):
                xi,yi=px(i,sub[i]); line.lineTo(xi,yi)
            p.setPen(QPen(QColor("#42A5F5"),2)); p.setBrush(Qt.NoBrush)
            p.drawPath(line)

        p.setPen(QPen(QColor("#37474F"),1))
        p.drawLine(PL,PT,PL,PT+ch); p.drawLine(PL,PT+ch,W-PR,PT+ch)
        p.setFont(QFont("Segoe UI",8)); p.setPen(QColor("#546E7A"))
        for ti in range(6):
            idx=int(ti*len(self.data)/5)
            tx=PL+(idx/max(len(self.data)-1,1))*cw
            p.drawText(int(tx)-25,PT+ch+8,50,14,Qt.AlignHCenter,f"{idx:,}")
        p.drawText(PL,PT+ch+24,cw,14,Qt.AlignHCenter,"Iteracja")
        p.save(); p.translate(14,PT+ch//2); p.rotate(-90)
        p.drawText(-40,-5,80,14,Qt.AlignHCenter,"Koszt [PLN]"); p.restore()
        p.end()


class MainView(QWidget):
    def __init__(self, hs, parent=None):
        super().__init__(parent)
        self.hs    = hs
        self.opt   = hs["best_recipe"] if hs else {k: BAR_WEIGHT/len(KEYS) for k in KEYS}
        self.opt_m = calc(self.opt)
        self._build()

    def _build(self):
        sa = QScrollArea(); sa.setWidgetResizable(True)
        ol = QVBoxLayout(self); ol.setContentsMargins(0,0,0,0); ol.addWidget(sa)
        root = QWidget(); sa.setWidget(root)
        L = QVBoxLayout(root); L.setContentsMargins(32,28,32,32); L.setSpacing(22)

        title = QLabel("ALGO-BAR  —  Interaktywna receptura")
        title.setStyleSheet("color:#42A5F5;font-size:20px;font-weight:900;letter-spacing:2px;")
        L.addWidget(title)

        if self.hs:
            L.addWidget(self._lbl("Wynik Harmony Search"))
            r1 = QHBoxLayout(); r1.setSpacing(10)
            fc = "#66BB6A" if self.opt_m["ok"] else "#EF5350"
            r1.addWidget(Card("Koszt optymalny", f"{self.opt_m['cost']:.4f}","PLN/100g","#42A5F5"))
            r1.addWidget(Card("Białko",          f"{self.opt_m['protein']:.2f}","g","#66BB6A",f"min {MIN_PROTEIN:.0f} g"))
            r1.addWidget(Card("Tłuszcz",         f"{self.opt_m['fat']:.2f}","g","#EF9A9A",f"max {MAX_FAT:.0f} g"))
            r1.addWidget(Card("Ograniczenia",    "TAK" if self.opt_m["ok"] else "NIE","",fc))
            L.addLayout(r1)

        L.addWidget(self._sep())

        # BATON
        L.addWidget(self._lbl("Twoja receptura — przeciągnij granicę ⟺ między składnikami"))
        hint = QLabel("Chwyć białe kółko ⟺ i przesuń w bok — suma zawsze wynosi 100 g. Limity min/max są pilnowane automatycznie.")
        hint.setStyleSheet("color:#546E7A;font-size:11px;")
        hint.setWordWrap(True)
        L.addWidget(hint)

        self.bar = BarWidget(dict(self.opt))
        self.bar.changed.connect(self._on_change)
        L.addWidget(self.bar)

        L.addWidget(self._sep())

        # Wskaźniki
        L.addWidget(self._lbl("Parametry na żywo"))
        wrow = QHBoxLayout(); wrow.setSpacing(10)
        m = calc(self.opt)
        self.w_prot = Wskaznik("Białko",      m["protein"], MIN_PROTEIN, "g",  False)
        self.w_fat  = Wskaznik("Tłuszcz",     m["fat"],     MAX_FAT,     "g",  True)
        self.w_cost = Wskaznik("Koszt",       m["cost"],    99,          "PLN",False)
        self.w_mass = Wskaznik("Masa łączna", m["total"],   100.5,       "g",  True)
        for w in [self.w_prot, self.w_fat, self.w_cost, self.w_mass]:
            wrow.addWidget(w)
        L.addLayout(wrow)

        # Karty użytkownika
        r2 = QHBoxLayout(); r2.setSpacing(10)
        fc2 = "#66BB6A" if m["ok"] else "#EF5350"
        self.c_cost = Card("Mój koszt",    f"{m['cost']:.4f}",    "PLN/100g","#FFA726")
        self.c_prot = Card("Moje białko",  f"{m['protein']:.2f}", "g","#42A5F5", f"min {MIN_PROTEIN:.0f} g")
        self.c_fat  = Card("Mój tłuszcz", f"{m['fat']:.2f}",     "g","#EF9A9A", f"max {MAX_FAT:.0f} g")
        self.c_feas = Card("Ograniczenia", "TAK" if m["ok"] else "NIE","",fc2)
        cards = [self.c_cost, self.c_prot, self.c_fat]
        if self.hs:
            diff = m["cost"] - self.opt_m["cost"]
            sign = "+" if diff >= 0 else ""
            self.c_diff = Card("Vs optimum", f"{sign}{diff:.4f}","PLN",
                               "#EF5350" if diff>0 else "#66BB6A")
            cards.append(self.c_diff)
        cards.append(self.c_feas)
        for c in cards: r2.addWidget(c)
        L.addLayout(r2)

        # Przyciski
        br = QHBoxLayout(); br.addStretch()
        if self.hs:
            rb = QPushButton("↺  Resetuj do optimum HS")
            rb.setObjectName("reset"); rb.clicked.connect(self._reset)
            br.addWidget(rb)
        L.addLayout(br)

        # Zbieżność
        if self.hs:
            conv   = self.hs.get("zbieznosc", self.hs.get("convergence",[]))
            params = self.hs.get("parametry", self.hs.get("params",{}))
            if conv:
                L.addWidget(self._sep())
                L.addWidget(self._lbl("Zbieżność algorytmu Harmony Search"))
                pr = QHBoxLayout(); pr.setSpacing(8)
                for sym, desc in [("HMS","pamięć"),("HMCR","uwzgl."),
                                   ("PAR","korekta"),("BW","pasmo"),("NI","iteracji")]:
                    f = QFrame()
                    f.setStyleSheet("background:#16213E;border:1px solid #263238;border-radius:6px;")
                    cl = QVBoxLayout(f); cl.setContentsMargins(12,8,12,8); cl.setSpacing(1)
                    sl = QLabel(sym); sl.setStyleSheet("color:#42A5F5;font-size:14px;font-weight:800;")
                    vl = QLabel(str(params.get(sym,"—"))); vl.setStyleSheet("color:#E0E0E0;font-size:12px;")
                    dl = QLabel(desc); dl.setStyleSheet("color:#546E7A;font-size:9px;")
                    cl.addWidget(sl); cl.addWidget(vl); cl.addWidget(dl)
                    pr.addWidget(f)
                L.addLayout(pr)

                sr = QHBoxLayout(); sr.setSpacing(10)
                for t2,v2,u2,c2 in [
                    ("Start",   f"{conv[0]:.4f}",          "PLN","#EF5350"),
                    ("Koniec",  f"{conv[-1]:.4f}",         "PLN","#66BB6A"),
                    ("Poprawa", f"{conv[0]-conv[-1]:.4f}", "PLN","#FFA726"),
                    ("Redukcja",f"{(1-conv[-1]/conv[0])*100:.1f}","%","#42A5F5"),
                ]:
                    sr.addWidget(Card(t2,v2,u2,c2))
                L.addLayout(sr)

                self.wyk = Wykres(conv); L.addWidget(self.wyk,1)
                btnr = QHBoxLayout(); btnr.addStretch()
                btnw = QPushButton("▶  Odtwórz animację"); btnw.clicked.connect(self.wyk.replay)
                btnr.addWidget(btnw); L.addLayout(btnr)

        L.addStretch()

    def _on_change(self, recipe):
        m = calc(recipe)
        self.w_prot.update_val(m["protein"])
        self.w_fat.update_val(m["fat"])
        self.w_cost.update_val(m["cost"])
        self.w_mass.update_val(m["total"])
        self.c_cost.set(f"{m['cost']:.4f}","#FFA726")
        self.c_prot.set(f"{m['protein']:.2f}","#42A5F5" if m["protein"]>=MIN_PROTEIN else "#EF5350")
        self.c_fat.set(f"{m['fat']:.2f}","#EF9A9A" if m["fat"]<=MAX_FAT else "#EF5350")
        fc = "#66BB6A" if m["ok"] else "#EF5350"
        self.c_feas.set("TAK" if m["ok"] else "NIE", fc)
        if self.hs:
            diff = m["cost"] - self.opt_m["cost"]
            sign = "+" if diff>=0 else ""
            self.c_diff.set(f"{sign}{diff:.4f}","#EF5350" if diff>0 else "#66BB6A")

    def _reset(self):
        self.bar.recipe = dict(self.opt)
        self.bar.update()
        self._on_change(self.opt)

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("background:#263238;max-height:1px;"); return f

    def _lbl(self, txt):
        l = QLabel(txt)
        l.setStyleSheet("color:#90A4AE;font-size:11px;font-weight:700;letter-spacing:.5px;")
        return l


class App(QMainWindow):
    def __init__(self, jp):
        super().__init__()
        self.setWindowTitle("ALGO-BAR — Optymalizacja receptury batona")
        self.resize(1100, 820); self.setStyleSheet(SS)
        self.jp = jp; self.hs = None
        self._load(); self._build()

    def _load(self):
        if self.jp and Path(self.jp).exists():
            with open(self.jp, encoding="utf-8") as f:
                self.hs = json.load(f)

    def _build(self):
        cw = QWidget(); self.setCentralWidget(cw)
        root = QVBoxLayout(cw); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        hdr = QWidget(); hdr.setFixedHeight(52)
        hdr.setStyleSheet("background:#0D1B2A;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(28,0,28,0)
        logo = QLabel("ALGO-BAR")
        logo.setStyleSheet("color:#42A5F5;font-size:17px;font-weight:900;letter-spacing:4px;")
        hl.addWidget(logo)
        sub = QLabel("Optymalizacja receptury • Harmony Search")
        sub.setStyleSheet("color:#37474F;font-size:11px;margin-left:16px;")
        hl.addWidget(sub); hl.addStretch()
        btn = QPushButton("  Wczytaj wynik_hs.json")
        btn.setObjectName("load"); btn.clicked.connect(self._open)
        hl.addWidget(btn)
        root.addWidget(hdr)

        self.vc = QWidget()
        vl = QVBoxLayout(self.vc); vl.setContentsMargins(0,0,0,0)
        self.mv = MainView(self.hs)
        vl.addWidget(self.mv)
        root.addWidget(self.vc,1)

    def _open(self):
        p, _ = QFileDialog.getOpenFileName(self,"wynik_hs.json","","JSON (*.json)")
        if not p: return
        self.jp = p; self._load()
        layout = self.vc.layout()
        old = layout.takeAt(0)
        if old and old.widget(): old.widget().deleteLater()
        self.mv = MainView(self.hs); layout.addWidget(self.mv)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", default="wynik_hs.json")
    a = p.parse_args()
    app = QApplication(sys.argv)
    win = App(a.json); win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()