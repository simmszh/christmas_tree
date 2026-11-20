# 圣诞粒子树 · 3D Interactive Particle Christmas Tree

用 Python 程序化生成一棵由 **15,518 颗粒子**组成的 3D 圣诞树，并输出一个可离线运行的单文件 HTML。  
拖拽旋转、滚轮缩放、点击许愿，还有落雪、极光/玫瑰/冰蓝三套灯光色系与电影感 Bloom 辉光。

![场景预览](preview.png)

> 上图是真实 WebGL 场景的无头渲染截帧（不含 HTML 界面）；界面与交互在浏览器中体验。

## 快速开始

只需要 **Python 3.9+**，无第三方依赖：

```bash
python christmas_tree.py
```

脚本会生成 `christmas_tree.html`，并用默认浏览器打开。  
如果浏览器没有自动打开，直接双击 `christmas_tree.html` 即可；它是一个完全自包含的文件，不需要联网。

也可以自定义粒子数量和随机种子：

```bash
python christmas_tree.py --particles 18000 --seed 42
```

## 交互

| 操作 | 效果 |
| --- | --- |
| 拖拽 | 环绕观察圣诞树 |
| 滚轮 / 双指捏合 | 拉近 / 拉远 |
| 点击画面 | 向星愿爆发粒子，许下愿望 |
| 自动旋转 | 暂停 / 恢复缓慢环绕 |
| 落雪 | 开关雪花 |
| 光色 | 极光 → 玫瑰 → 冰蓝循环切换 |
| 重置视角 | 飞回初始机位 |

键盘快捷键：`Space` 自动旋转、`S` 落雪、`P` 切换色系、`R` 重置视角。

## 参数

```text
--particles N   树叶粒子数量，默认 12500，最少 2000
--seed N        随机种子，默认 20261224
--output PATH   输出 HTML 路径
--no-open       生成后不自动打开浏览器
```

粒子构成：

- **12,570** 树叶 / 松针粒子
- **1,550** 螺旋灯带
- **148** 发光挂饰
- **1,250** 地面雪光粒子
- 另外实时生成 1,700 片飘雪、1,450 颗远景星、175 只环绕萤火

## 文件结构

```text
christmas_tree.py     粒子生成、HTML 组装与启动入口
web/
  template.html       页面骨架
  style.css           界面样式
  scene.js            Three.js 场景、着色器与交互
vendor/               Three.js r128 及官方示例（MIT）
christmas_tree.html   生成后的单文件成品（可直接打开）
preview.png           实际 WebGL 渲染截帧
```

`web/` 与 `vendor/` 只在重新生成时需要；`christmas_tree.html` 已经把 CSS、JavaScript、Three.js 和全部粒子数据内联，方便单独分享。

## 想自己改

- **配色 / 机位 / 辉光**：编辑 `web/scene.js` 中的 `PALETTES`、`computeLayout()`、`UnrealBloomPass` 参数。
- **树形 / 粒子分布 / 挂饰**：编辑 `christmas_tree.py` 中的 `build_foliage()`、`build_garland()`、`build_ornaments()`。
- 修改 `web/` 下的文件后，重新运行 `python christmas_tree.py` 即可更新 `christmas_tree.html`。

## 说明

- 渲染使用 WebGL（Three.js r128），建议开启浏览器硬件加速。
- 若浏览器禁止自动打开本地文件，可直接打开生成的 HTML，或运行 `python -m http.server` 后访问。
- Three.js 及官方示例脚本来自 [three.js](https://threejs.org/)，遵循 MIT License。
