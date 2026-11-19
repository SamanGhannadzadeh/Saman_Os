#!/usr/bin/env python3
# Saman Calculator — a clean GTK calculator (safe AST evaluation).
import ast, math, operator
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
       ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Mod: operator.mod, ast.Pow: operator.pow,
       ast.USub: operator.neg, ast.UAdd: operator.pos}

def ev(node):
    if isinstance(node, ast.Expression):
        return ev(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](ev(node.left), ev(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](ev(node.operand))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "sqrt" and len(node.args) == 1):
        return math.sqrt(ev(node.args[0]))
    raise ValueError("bad expression")

class Calc(Gtk.Window):
    def __init__(self):
        super().__init__(title="ماشین‌حساب سامان")
        self.set_default_size(300, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        v.set_margin_top(12); v.set_margin_bottom(12)
        v.set_margin_start(12); v.set_margin_end(12)
        self.add(v)
        self.entry = Gtk.Entry()
        self.entry.set_alignment(1.0)
        self.entry.set_text("0")
        self.entry.connect("activate", lambda *_: self.equals())
        v.pack_start(self.entry, False, False, 0)
        grid = Gtk.Grid()
        grid.set_row_spacing(6); grid.set_column_spacing(6)
        grid.set_row_homogeneous(True); grid.set_column_homogeneous(True)
        v.pack_start(grid, True, True, 0)
        keys = ["C", "⌫", "(", ")", "√",
                "7", "8", "9", "÷", "%",
                "4", "5", "6", "×", "−",
                "1", "2", "3", "+", "^",
                "0", ".", "=", "", ""]
        for i, k in enumerate(keys):
            if not k:
                continue
            b = Gtk.Button(label=k)
            if k == "=":
                b.get_style_context().add_class("suggested-action")
            b.connect("clicked", self.press, k)
            grid.attach(b, i % 5, i // 5, 1, 1)
        self.fresh = True

    def press(self, _btn, k):
        t = self.entry.get_text()
        if k == "C":
            self.entry.set_text("0"); self.fresh = True; return
        if k == "⌫":
            self.entry.set_text(t[:-1] or "0"); return
        if k == "=":
            self.equals(); return
        sym = {"÷": "/", "×": "*", "−": "-", "√": "sqrt("}.get(k, k)
        if self.fresh and (k.isdigit() or k == "."):
            self.entry.set_text(sym)
        elif self.fresh and k in "(√":
            self.entry.set_text(sym)
        else:
            self.entry.set_text(t + sym)
        self.fresh = False

    def equals(self):
        try:
            r = ev(ast.parse(self.entry.get_text(), mode="eval"))
            if isinstance(r, float) and r.is_integer():
                r = int(r)
            self.entry.set_text(str(r))
        except Exception:
            self.entry.set_text("خطا")
        self.fresh = True

if __name__ == "__main__":
    w = Calc()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
