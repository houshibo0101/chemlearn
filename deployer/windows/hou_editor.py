#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hou 晶胞编辑器（独立 Windows 桌面版）

与网页共用 .hou 格式：
    {
      "format": "hou-crystal", "version": 1, "name": "...",
      "lattice": {"a":..., "b":..., "c":..., "alpha":..., "beta":..., "gamma":...},
      "atoms": [{"element":"Na","x":0,"y":0,"z":0}],
      "view": {"rx":20,"ry":-28,"zoom":1}
    }

运行：python hou_editor.py
打包：python build_hou.py
"""
import json
import math
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_NAME = "Hou 晶胞编辑器"
VERSION = "1.0.0"
FORMAT = "hou-crystal"

COLORS = {
    "H": "#f8fafc", "C": "#334155", "N": "#2563eb", "O": "#ef4444",
    "F": "#22c55e", "Na": "#a855f7", "Mg": "#84cc16", "Al": "#94a3b8",
    "Si": "#64748b", "P": "#f97316", "S": "#eab308", "Cl": "#16a34a",
    "K": "#7c3aed", "Ca": "#0ea5e9", "Fe": "#b45309", "Cu": "#b06a3c",
    "Zn": "#71717a", "Cs": "#f59e0b", "Ba": "#14b8a6",
}
RADII = {"H": .075, "F": .075, "Cl": .075, "O": .075, "N": .075,
         "Na": .12, "Mg": .12, "K": .12, "Ca": .12, "Cs": .14, "Ba": .14}
CORNERS = [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
           [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]]
FACES = [[.5, .5, 0], [.5, .5, 1], [.5, 0, .5], [.5, 1, .5], [0, .5, .5], [1, .5, .5]]
EDGES = [[.5, 0, 0], [.5, 1, 0], [.5, 0, 1], [.5, 1, 1],
         [0, .5, 0], [1, .5, 0], [0, .5, 1], [1, .5, 1],
         [0, 0, .5], [1, 0, .5], [0, 1, .5], [1, 1, .5]]
INNER = [[.25, .25, .25], [.75, .75, .25], [.75, .25, .75], [.25, .75, .75]]
CELL_EDGES = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
              (0, 4), (1, 5), (2, 6), (3, 7)]


def element_color(element):
    return COLORS.get(str(element or "").strip(), "#64748b")


def element_radius(element):
    return RADII.get(str(element or "").strip(), .1)


def lattice_vectors(lat):
    al, be, ga = (math.radians(float(lat[k])) for k in ("alpha", "beta", "gamma"))
    a = [float(lat["a"]), 0.0, 0.0]
    b = [float(lat["b"]) * math.cos(ga), float(lat["b"]) * math.sin(ga), 0.0]
    cx = float(lat["c"]) * math.cos(be)
    cy = float(lat["c"]) * math.cos(al) - float(lat["c"]) * math.cos(be) * math.cos(ga)
    cy /= max(math.sin(ga), 1e-6)
    cz = math.sqrt(max(0.0, float(lat["c"]) ** 2 - cx ** 2 - cy ** 2))
    return a, b, [cx, cy, cz]


def cartesian(frac, vec):
    x, y, z = frac
    return [x * vec[0][i] + y * vec[1][i] + z * vec[2][i] for i in range(3)]


def rotate(p, rx, ry):
    x, y, z = p
    sr, cr = math.sin(math.radians(ry)), math.cos(math.radians(ry))
    x1, z1 = x * cr + z * sr, -x * sr + z * cr
    sx, cx = math.sin(math.radians(rx)), math.cos(math.radians(rx))
    return [x1, y * cx - z1 * sx, y * sx + z1 * cx]


class HouEditor:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME}  v{VERSION}")
        self.root.geometry("1180x820")
        self.root.minsize(900, 640)

        self.name_var = tk.StringVar(value="晶胞结构")
        self.preset_var = tk.StringVar(value="立方晶胞")
        self.template_var = tk.StringVar(value="简单立方")
        self.lat_vars = {k: tk.StringVar(value=v) for k, v in
                         {"a": "4", "b": "4", "c": "4", "alpha": "90", "beta": "90", "gamma": "90"}.items()}
        self.element_var = tk.StringVar(value="Na")
        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        self.z_var = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="拖动旋转 · 滚轮缩放")

        self.atoms = []
        self.rx, self.ry, self.zoom = 20.0, -28.0, 1.0
        self.drag = None
        self.font = ("Microsoft YaHei", 9)
        self.font_bold = ("Microsoft YaHei", 10, "bold")

        self._build_ui()
        self.root.configure(bg="#f8fafc")
        self.apply_template()
        self.root.after(180, self.render)
        self.root.bind("<Configure>", lambda e: self.render() if e.widget is self.root else None)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        top = tk.Frame(self.root, bg="#ffffff", padx=12, pady=9)
        top.pack(fill="x")
        tk.Label(top, text="名称", bg="#ffffff", font=self.font).pack(side="left")
        tk.Entry(top, textvariable=self.name_var, width=18, font=self.font).pack(side="left", padx=(5, 14))
        tk.Button(top, text="保存 .hou", command=self.save_hou, bg="#4f46e5", fg="white",
                  relief="flat", padx=12, pady=4, font=self.font).pack(side="left", padx=4)
        tk.Button(top, text="打开 .hou", command=self.open_hou, relief="flat",
                  padx=12, pady=4, font=self.font).pack(side="left", padx=4)
        tk.Button(top, text="重置视角", command=self.reset_view, relief="flat",
                  padx=12, pady=4, font=self.font).pack(side="left", padx=4)
        tk.Label(top, text="左键拖动旋转 · 滚轮缩放", bg="#ffffff",
                 fg="#94a3b8", font=self.font).pack(side="left", padx=12)

        body = tk.Frame(self.root, bg="#f8fafc")
        body.pack(fill="both", expand=True, padx=10, pady=10)
        left = tk.Frame(body, bg="#ffffff", width=365, padx=10, pady=10)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="晶胞参数", bg="#ffffff", fg="#4f46e5",
                 font=self.font_bold, anchor="w").pack(fill="x")
        preset = ttk.Combobox(left, textvariable=self.preset_var, state="readonly",
                              values=["立方晶胞", "六方晶胞", "自定义"], width=15)
        preset.pack(fill="x", pady=(5, 7))
        preset.bind("<<ComboboxSelected>>", lambda e: self.apply_preset())

        grid = tk.Frame(left, bg="#ffffff")
        grid.pack(fill="x")
        labels = [("a (Å)", "a"), ("b (Å)", "b"), ("c (Å)", "c"),
                  ("α (°)", "alpha"), ("β (°)", "beta"), ("γ (°)", "gamma")]
        for i, (label, key) in enumerate(labels):
            row, col = divmod(i, 2)
            tk.Label(grid, text=label, bg="#ffffff", fg="#64748b", font=self.font).grid(
                row=row, column=col * 2, sticky="w", padx=(0, 4), pady=3)
            tk.Entry(grid, textvariable=self.lat_vars[key], width=7, font=self.font).grid(
                row=row, column=col * 2 + 1, sticky="w", padx=(0, 10), pady=3)
        tk.Button(left, text="应用晶胞参数", command=self.apply_lattice, relief="flat",
                  bg="#eef2ff", fg="#4338ca", pady=4, font=self.font).pack(fill="x", pady=7)

        tk.Label(left, text="原子模板", bg="#ffffff", fg="#4f46e5",
                 font=self.font_bold, anchor="w").pack(fill="x")
        tpl = tk.Frame(left, bg="#ffffff")
        tpl.pack(fill="x", pady=(5, 8))
        ttk.Combobox(tpl, textvariable=self.template_var, state="readonly",
                     values=["不加载", "简单立方", "体心立方", "面心立方", "NaCl 型", "CsCl 型", "金刚石"],
                     width=14).pack(side="left", fill="x", expand=True)
        tk.Button(tpl, text="应用", command=self.apply_template, relief="flat",
                  padx=10, font=self.font).pack(side="left", padx=5)

        tk.Label(left, text="原子坐标（分数坐标 0–1）", bg="#ffffff", fg="#4f46e5",
                 font=self.font_bold, anchor="w").pack(fill="x")
        table = tk.Frame(left, bg="#ffffff")
        table.pack(fill="both", expand=True, pady=(6, 6))
        cols = ("element", "x", "y", "z")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", height=11)
        for col, title, width in (("element", "元素", 60), ("x", "x", 65), ("y", "y", 65), ("z", "z", 65)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="center")
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.load_selected_atom())

        add = tk.Frame(left, bg="#ffffff")
        add.pack(fill="x", pady=(0, 5))
        tk.Label(add, text="元素", bg="#ffffff", font=self.font).pack(side="left")
        tk.Entry(add, textvariable=self.element_var, width=4, font=self.font).pack(side="left", padx=3)
        for key, var in (("x", self.x_var), ("y", self.y_var), ("z", self.z_var)):
            tk.Label(add, text=key, bg="#ffffff", fg="#94a3b8", font=self.font).pack(side="left")
            tk.Entry(add, textvariable=var, width=5, font=self.font).pack(side="left", padx=2)
        tk.Button(add, text="添加", command=self.add_atom, relief="flat",
                  bg="#4f46e5", fg="white", padx=8, font=self.font).pack(side="left", padx=4)

        actions = tk.Frame(left, bg="#ffffff")
        actions.pack(fill="x")
        tk.Button(actions, text="更新选中", command=self.update_selected_atom,
                  relief="flat", font=self.font).pack(side="left", padx=(0, 5))
        tk.Button(actions, text="删除选中", command=self.remove_selected_atom,
                  relief="flat", fg="#dc2626", font=self.font).pack(side="left")
        self.count_label = tk.Label(actions, text="共 0 个原子", bg="#ffffff",
                                    fg="#94a3b8", font=self.font)
        self.count_label.pack(side="right")

        right = tk.Frame(body, bg="#ffffff", highlightthickness=1, highlightbackground="#e2e8f0")
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.canvas = tk.Canvas(right, bg="#ffffff", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_drag_start)
        self.canvas.bind("<B1-Motion>", self.on_drag_move)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "drag", None))
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self.zoom_by(1.08))
        self.canvas.bind("<Button-5>", lambda e: self.zoom_by(.92))
        tk.Label(self.root, textvariable=self.status_var, bg="#f8fafc", fg="#94a3b8",
                 anchor="w", font=self.font).pack(fill="x", padx=14, pady=(0, 8))

    # -------------------------------------------------------------- lattice
    def read_lattice(self):
        try:
            lat = {k: float(v.get()) for k, v in self.lat_vars.items()}
        except ValueError:
            messagebox.showerror(APP_NAME, "晶胞参数必须是数字")
            return None
        if min(lat["a"], lat["b"], lat["c"]) <= 0 or not all(20 <= lat[k] <= 160 for k in ("alpha", "beta", "gamma")):
            messagebox.showerror(APP_NAME, "晶胞参数范围不正确")
            return None
        return lat

    def apply_lattice(self):
        if self.read_lattice():
            self.render()

    def apply_preset(self):
        kind = self.preset_var.get()
        if kind == "立方晶胞":
            for k in ("alpha", "beta", "gamma"):
                self.lat_vars[k].set("90")
        elif kind == "六方晶胞":
            self.lat_vars["b"].set(self.lat_vars["a"].get())
            self.lat_vars["alpha"].set("90")
            self.lat_vars["beta"].set("90")
            self.lat_vars["gamma"].set("120")
        self.render()

    def apply_template(self):
        kind = self.template_var.get()
        if kind == "不加载":
            return
        if kind == "简单立方":
            atoms = [("C", *p) for p in CORNERS]
        elif kind == "体心立方":
            atoms = [("C", *p) for p in CORNERS] + [("C", .5, .5, .5)]
        elif kind == "面心立方":
            atoms = [("C", *p) for p in CORNERS + FACES]
        elif kind == "NaCl 型":
            atoms = [("Cl", *p) for p in CORNERS + FACES] + [("Na", *p) for p in EDGES] + [("Na", .5, .5, .5)]
        elif kind == "CsCl 型":
            atoms = [("Cl", *p) for p in CORNERS] + [("Cs", .5, .5, .5)]
        else:
            atoms = [("C", *p) for p in CORNERS + FACES + INNER]
        self.atoms = [{"element": e, "x": x, "y": y, "z": z} for e, x, y, z in atoms]
        self.refresh_tree()
        self.render()

    # ---------------------------------------------------------------- atoms
    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, atom in enumerate(self.atoms):
            self.tree.insert("", "end", iid=str(i), values=(
                atom["element"], f"{atom['x']:.3f}", f"{atom['y']:.3f}", f"{atom['z']:.3f}"))
        self.count_label.config(text=f"共 {len(self.atoms)} 个原子")

    def load_selected_atom(self):
        sel = self.tree.selection()
        if not sel:
            return
        atom = self.atoms[int(sel[0])]
        self.element_var.set(atom["element"])
        self.x_var.set(f"{atom['x']:g}")
        self.y_var.set(f"{atom['y']:g}")
        self.z_var.set(f"{atom['z']:g}")

    def read_atom_fields(self):
        element = self.element_var.get().strip()
        if not element:
            messagebox.showerror(APP_NAME, "请输入元素符号")
            return None
        try:
            x, y, z = float(self.x_var.get()), float(self.y_var.get()), float(self.z_var.get())
        except ValueError:
            messagebox.showerror(APP_NAME, "坐标必须是数字")
            return None
        return {"element": element, "x": x, "y": y, "z": z}

    def add_atom(self):
        atom = self.read_atom_fields()
        if not atom:
            return
        self.atoms.append(atom)
        self.refresh_tree()
        self.tree.selection_set(str(len(self.atoms) - 1))
        self.render()

    def update_selected_atom(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(APP_NAME, "请先在列表中选择一个原子")
            return
        atom = self.read_atom_fields()
        if not atom:
            return
        self.atoms[int(sel[0])] = atom
        self.refresh_tree()
        self.tree.selection_set(sel[0])
        self.render()

    def remove_selected_atom(self):
        sel = self.tree.selection()
        if not sel:
            return
        for i in sorted((int(x) for x in sel), reverse=True):
            self.atoms.pop(i)
        self.refresh_tree()
        self.render()

    # ----------------------------------------------------------------- view
    def reset_view(self):
        self.rx, self.ry, self.zoom = 20.0, -28.0, 1.0
        self.render()

    def on_drag_start(self, event):
        self.drag = (event.x, event.y, self.rx, self.ry)

    def on_drag_move(self, event):
        if not self.drag:
            return
        x0, y0, rx0, ry0 = self.drag
        self.ry = ry0 + (event.x - x0) * .55
        self.rx = max(-89, min(89, rx0 - (event.y - y0) * .55))
        self.render()

    def on_wheel(self, event):
        self.zoom_by(1.08 if event.delta > 0 else .92)

    def zoom_by(self, factor):
        self.zoom = max(.35, min(3.0, self.zoom * factor))
        self.render()

    def render(self):
        c = self.canvas
        if not c:
            return
        c.delete("all")
        w, h = max(300, c.winfo_width()), max(300, c.winfo_height())
        lat = self.read_lattice()
        if not lat:
            return
        vec = lattice_vectors(lat)
        corners = [cartesian(p, vec) for p in CORNERS]
        center = [sum(p[i] for p in corners) / 8 for i in range(3)]
        rel = [[p[i] - center[i] for i in range(3)] for p in corners]
        radius = max(1.0, max(math.sqrt(sum(v * v for v in p)) for p in rel))
        scale = min(w, h) * .38 / radius * self.zoom
        cx, cy = w / 2, h / 2

        def proj(p):
            q = rotate(p, self.rx, self.ry)
            return cx + q[0] * scale, cy - q[1] * scale, q[2]

        pts = [proj(p) for p in rel]
        for i, j in CELL_EDGES:
            c.create_line(pts[i][0], pts[i][1], pts[j][0], pts[j][1], fill="#94a3b8", width=1.6)

        # 晶胞轴
        origin = proj([-center[i] for i in range(3)])
        for vec_i, label, color in ((vec[0], "a", "#6366f1"), (vec[1], "b", "#10b981"), (vec[2], "c", "#f59e0b")):
            p = proj([vec_i[i] - center[i] for i in range(3)])
            c.create_line(origin[0], origin[1], p[0], p[1], fill=color, width=2)
            c.create_text(p[0] + 8, p[1] - 7, text=label, fill=color, font=self.font_bold)

        items = []
        for atom in self.atoms:
            p = cartesian([atom["x"], atom["y"], atom["z"]], vec)
            items.append((proj([p[i] - center[i] for i in range(3)]), atom))
        items.sort(key=lambda item: item[0][2])
        for (sx, sy, _), atom in items:
            r = max(4, min(17, element_radius(atom["element"]) * scale * 1.15))
            c.create_oval(sx - r, sy - r, sx + r, sy + r,
                          fill=element_color(atom["element"]), outline="#0f172a", width=1.2)
            if r >= 6:
                c.create_text(sx, sy, text=str(atom["element"]),
                              fill="#ffffff" if atom["element"] in ("H", "C") else "#102033",
                              font=("Microsoft YaHei", max(7, min(11, int(r)))))

        c.create_text(14, h - 14, text="拖动旋转 · 滚轮缩放", anchor="w", fill="#94a3b8", font=self.font)

    # ----------------------------------------------------------------- file
    def save_hou(self):
        lat = self.read_lattice()
        if not lat:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".hou", filetypes=[("Hou 晶胞", "*.hou")],
            initialfile=f"{self.name_var.get() or 'crystal'}.hou")
        if not path:
            return
        data = {
            "format": FORMAT, "version": 1, "name": self.name_var.get().strip() or "晶胞结构",
            "lattice": lat,
            "atoms": [{"element": str(a["element"]).strip() or "C",
                       "x": a["x"], "y": a["y"], "z": a["z"]} for a in self.atoms],
            "view": {"rx": self.rx, "ry": self.ry, "zoom": self.zoom},
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_var.set(f"已保存：{os.path.basename(path)}")
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"保存失败：{exc}")

    def open_hou(self):
        path = filedialog.askopenfilename(filetypes=[("Hou 晶胞", "*.hou"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("format") != FORMAT:
                raise ValueError("不是 .hou 晶胞文件")
            lat = data.get("lattice") or {}
            for k in self.lat_vars:
                if k in lat:
                    self.lat_vars[k].set(str(lat[k]))
            self.name_var.set(str(data.get("name") or "晶胞结构"))
            self.atoms = [{"element": str(a.get("element") or "C"),
                           "x": float(a.get("x") or 0), "y": float(a.get("y") or 0),
                           "z": float(a.get("z") or 0)} for a in (data.get("atoms") or [])]
            view = data.get("view") or {}
            self.rx = float(view.get("rx", 20))
            self.ry = float(view.get("ry", -28))
            self.zoom = float(view.get("zoom", 1))
            self.refresh_tree()
            self.render()
            self.status_var.set(f"已打开：{os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"打开失败：{exc}")


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except tk.TclError:
        pass
    HouEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
