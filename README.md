# DNF 像素格斗 · H5 Demo

用 **DNF 客户端解包的真实 2D 精灵素材**做的横版手操打怪小游戏，纯 Canvas + 原生 JS，无框架、无运行时依赖，可双击打开或直接嵌入 H5 页面。

![type](https://img.shields.io/badge/type-H5%20game-orange) ![deps](https://img.shields.io/badge/deps-none-green) ![build](https://img.shields.io/badge/build-Python3-blue)

## 试玩

打开 `dist/dnf-pixel-battle.html` 即可（单文件，素材已全部 base64 内联，无需服务器）。

- **A / D** 或 **← / →**：移动
- **X**：普通攻击
- **Z**：技能（有冷却）
- **C / W / ↑**：跳跃
- 手机：点屏幕下方虚拟按钮

## 内容

- 角色：DNF 鬼剑士（待机 / 普攻 / 技能 / 受击 四套动作）
- 关卡 1：哥布林
- 关卡 2：牛头王 萨乌塔（BOSS）
- 系统：血条、伤害飘字、连击 COMBO、顿帧震屏、技能 CD、胜负结算

## 扫荡挂机模式（冒烟进度条）

`dist/dnf-sweep-idle.html` 是扫荡挂机玩法：选副本 → 自动扫荡 → 进度条推进时**喷出刀剑粒子**，速度档位越高越密（x1 / x2 / x4），每轮结算金币和经验。

```bash
python scripts/build_sweep.py   # 重新生成
```

三个副本：幽暗密林（哥布林）、雷鸣废墟、格拉卡（牛头王萨乌塔）。战斗画面与角色用的都是上面同一批真实 DNF 素材。

## 接入 H5

把成品 HTML 放到站点目录，用 iframe 嵌入：

```html
<iframe src="dnf-pixel-battle.html"
        style="width:100%;height:100vh;border:0"></iframe>
```

素材全部内联在文件内部，同源部署即可，不请求任何外部图片。

## 目录结构

```
.
├── assets/                 # 从 DNF 客户端解包出的原始 PNG 帧
│   ├── player/             # 鬼剑士（210 帧）
│   ├── goblin/             # 哥布林（17 帧）
│   ├── boss/               # 牛头王萨乌塔（33 帧）
│   └── bg.png              # 森林地图背景
├── scripts/build.py        # 构建脚本：把素材内联成单文件 HTML
├── dist/
│   └── dnf-pixel-battle.html   # 成品（可直接用）
└── README.md
```

## 重新构建

只改了素材或战斗逻辑后，重新生成成品：

```bash
python scripts/build.py
```

仅用 Python 3 标准库，无第三方依赖。

## 素材来源与版权

精灵图素材提取自开源项目 [`v-star0719/U3D_MiniDNF`](https://github.com/v-star0719/U3D_MiniDNF) 中导出的 DNF 客户端资源，画面版权归 **Neople / 腾讯** 所有。

> 本项目仅用于个人学习与技术研究，**禁止商用或公开分发素材**。如需商业使用，请替换为自有版权素材。

## License

代码部分 MIT；素材版权见上。
