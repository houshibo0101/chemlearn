# .hou 晶胞文件格式

`.hou` 是 ChemLearn 晶胞编辑器使用的 JSON 文件，网页版和 Windows 桌面版共用同一格式。

```json
{
  "format": "hou-crystal",
  "version": 1,
  "name": "NaCl 晶胞",
  "lattice": {
    "a": 5.64,
    "b": 5.64,
    "c": 5.64,
    "alpha": 90,
    "beta": 90,
    "gamma": 90
  },
  "atoms": [
    { "element": "Na", "x": 0, "y": 0, "z": 0 },
    { "element": "Cl", "x": 0.5, "y": 0.5, "z": 0.5 }
  ],
  "view": { "rx": 20, "ry": -28, "zoom": 1 }
}
```

## 字段说明

- `format`：固定为 `hou-crystal`
- `version`：当前为 `1`
- `name`：晶胞名称
- `lattice`：晶胞参数，长度单位 Å，角度单位 °
- `atoms`：原子列表，`x/y/z` 是分数坐标，通常为 0–1
- `element`：元素符号，如 Na、Cl、C
- `view`：保存时的 3D 视角，仅用于打开时恢复，不影响结构

## 使用

- 网页：题库管理 → 上传题目 → 画晶胞 → 打开 `.hou`
- 桌面：双击 `HouCrystalEditor.exe` → 打开 `.hou` / 保存 `.hou`
- 网页画完晶胞后点「插入到题目」，会生成图片保存到题目图片字段
- 桌面版适合离线编辑和批量整理 `.hou` 文件
