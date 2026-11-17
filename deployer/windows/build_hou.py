#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包独立晶胞编辑器 HouCrystalEditor.exe"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
WORK = os.path.join(HERE, "build_hou")
SPEC = os.path.join(HERE, "build_hou")

os.makedirs(OUT, exist_ok=True)
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean", "--onefile", "--windowed",
    "--name", "HouCrystalEditor",
    "--icon", os.path.join(HERE, "app.ico"),
    "--distpath", OUT,
    "--workpath", WORK,
    "--specpath", SPEC,
    "--add-data", "%s%s." % (os.path.join(HERE, "elements.json"), os.pathsep),
    "--hidden-import", "tkinter",
    "--hidden-import", "tkinter.ttk",
    "--hidden-import", "tkinter.filedialog",
    "--hidden-import", "tkinter.messagebox",
    os.path.join(HERE, "hou_editor.py"),
]
print(" ".join(cmd))
raise SystemExit(subprocess.call(cmd, cwd=HERE))
