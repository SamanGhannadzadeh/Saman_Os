#!/usr/bin/env python3
# Saman Notes — simple notes in ~/.local/share/saman-notes/
import os
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

DIR = os.path.expanduser("~/.local/share/saman-notes")
os.makedirs(DIR, exist_ok=True)

class Notes(Gtk.Window):
    def __init__(self):
        super().__init__(title="یادداشت سامان")
        self.set_default_size(640, 420)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.current = None
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(paned)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        left.set_margin_top(8); left.set_margin_start(8)
        self.store = Gtk.ListStore(str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.append_column(Gtk.TreeViewColumn("یادداشت‌ها", Gtk.CellRendererText(), text=0))
        self.tree.get_selection().connect("changed", self.on_select)
        sw = Gtk.ScrolledWindow()
        sw.add(self.tree)
        left.pack_start(sw, True, True, 0)
        nb = Gtk.Button(label="یادداشت تازه")
        nb.connect("clicked", self.new_note)
        left.pack_start(nb, False, False, 0)
        db = Gtk.Button(label="حذف")
        db.connect("clicked", self.del_note)
        left.pack_start(db, False, False, 0)
        paned.pack1(left, False, False)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.set_margin_top(8); right.set_margin_end(8)
        self.view = Gtk.TextView()
        self.view.set_wrap_mode(Gtk.WrapMode.WORD)
        sw2 = Gtk.ScrolledWindow()
        sw2.add(self.view)
        right.pack_start(sw2, True, True, 0)
        sb = Gtk.Button(label="ذخیره")
        sb.get_style_context().add_class("suggested-action")
        sb.connect("clicked", self.save)
        right.pack_start(sb, False, False, 0)
        paned.pack2(right, True, False)
        self.reload()

    def reload(self):
        self.store.clear()
        for f in sorted(os.listdir(DIR)):
            if f.endswith(".txt"):
                self.store.append([f[:-4]])

    def path(self, name):
        return os.path.join(DIR, name + ".txt")

    def on_select(self, sel):
        model, it = sel.get_selected()
        if not it:
            return
        self.current = model[it][0]
        try:
            txt = open(self.path(self.current), encoding="utf-8").read()
        except Exception:
            txt = ""
        self.view.get_buffer().set_text(txt)

    def new_note(self, _b):
        d = Gtk.MessageDialog(self, 0, Gtk.MessageType.QUESTION,
                              Gtk.ButtonsType.OK_CANCEL, "نام یادداشت:")
        e = Gtk.Entry()
        d.get_content_area().pack_start(e, False, False, 0)
        d.show_all()
        if d.run() == Gtk.ResponseType.OK and e.get_text().strip():
            name = e.get_text().strip()
            open(self.path(name), "w").close()
            self.reload()
        d.destroy()

    def save(self, _b):
        if not self.current:
            self.new_note(_b)
            return
        buf = self.view.get_buffer()
        txt = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        open(self.path(self.current), "w", encoding="utf-8").write(txt)

    def del_note(self, _b):
        if self.current:
            try:
                os.remove(self.path(self.current))
            except Exception:
                pass
            self.current = None
            self.view.get_buffer().set_text("")
            self.reload()

if __name__ == "__main__":
    w = Notes()
    w.connect("destroy", Gtk.main_quit)
    w.show_all()
    Gtk.main()
