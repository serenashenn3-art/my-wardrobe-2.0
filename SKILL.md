---
name: my-wardrobe
description: "我的衣橱2.0——衣橱单品拍照建档、棚拍级展示、搭配卡生成与二手回收管理。当用户拍摄或上传衣服、裤子、裙子、鞋子、包包、帽子、首饰等穿搭单品照片,希望批量抠图建档(支持一次上传30件)、AI美化去皱、棚拍级展示、分类浏览(种类/季节/品牌)、拖拽生成搭配卡、二手出售或捐赠回收时使用。触发词:我的衣橱、搭配卡、穿搭卡、OOTD、今日穿搭、单品抠图、衣橱、衣帽间、outfit、wardrobe、搭配样式卡、帮我搭配、穿搭拼贴、回收、二手出售、捐赠、批量上传。"
---

# 我的衣橱 2.0 (My Wardrobe)· 搭配样式卡 + 衣橱管理

把用户的单品照片变成棚拍级展示图,在 Web 应用中分类浏览、拖拽搭配、
一键生成杂志拼贴风搭配卡,并支持二手出售与捐赠回收。

视觉基准:`assets/reference-xhs-card.jpg`(小红书竖版)与
`assets/reference-card.jpeg`(经典带标签版)。

## 架构概览

```
my-wardrobe/
├── SKILL.md                     # 技能入口(本文件)
├── wardrobe.schema.json         # wardrobe.json 数据 schema
├── wardrobe.example.json        # 最小示例数据
├── app/
│   └── wardrobe-app.html        # 衣橱管理 Web 应用(5 大功能页)
├── scripts/
│   ├── remove_bg.py             # rembg 本地抠图(批量+单张异常捕获)
│   ├── beautify_item.py         # OpenCV 频率分离去皱(RGBA 校验)
│   ├── make_studio_cards.py     # 棚拍级单品图(输入/输出目录分离)
│   ├── make_contact_sheet.py    # 预览墙生成(4列网格)
│   ├── compose_card_xhs.py      # 小红书 9:16 搭配卡(水印误伤检测)
│   └── compose_card.py          # 经典 3:4 带标签搭配卡
├── references/
│   ├── categories.md            # 槽位/分类/搭配规则/冲突解决策略
│   └── style-guide.md           # 视觉规范 + 棚拍级处理管线
├── constraints/
│   └── rules.md                 # 全局约束(数据/图像/预览墙/回收)
├── examples/
│   ├── spec-sample.json         # 搭配卡 spec 示例
│   ├── bulk-upload-workflow.md  # 批量上传工作流示例
│   └── outfit-card-workflow.md  # 搭配卡生成工作流示例
└── assets/                      # 参考图
```

## 数据模型

所有单品数据存储在 `wardrobe.json` 中, 结构遵循
[`wardrobe.schema.json`](wardrobe.schema.json)(JSON Schema),
最小示例见 [`wardrobe.example.json`](wardrobe.example.json)。

必填字段: `id`, `photo`, `slot`, `label`, `color`, `style`, `seasons`, `file`, `source`
可选字段: `brand`, `features`, `note`

## 两条数据流

### 数据流 A: AI 录入(Agent 端处理)

用户通过对话上传照片, Agent 执行完整处理管线:

```
照片 → 识别字段 → rembg抠图(remove_bg.py) → 美化去皱(beautify_item.py)
    → 棚拍级card(make_studio_cards.py) → 预览墙(make_contact_sheet.py)
    → 写入 wardrobe.json
```

- Agent 识别 slot/label/color/style/seasons/brand/features 等字段
- 抠图存为透明底 PNG 到 `items/`
- 美化后的单品图存到 `closet-studio/`
- 所有元数据写入 `wardrobe.json`, 需符合 `wardrobe.schema.json`

### 数据流 B: Web 应用录入(用户端自助)

用户在浏览器中打开 `app/wardrobe-app.html` 自主操作:

```
浏览器选照片 → 自动创建卡片(默认 slot=accessory, seasons=[四季])
    → 用户手动修改分类/品牌/季节 → 可移至回收
```

- 上传的照片以 base64 嵌入, 不经过 Python 脚本
- 用户可手动修改 slot(下拉选择)、品牌(可编辑文本)、季节(标签)
- 无品牌时显示「未知品牌」, 可手动输入
- 搭配卡画布支持拖拽/缩放/置顶/移除, 导出 PNG
- 回收页支持二手出售(输入价格)和捐赠(选机构)

**两条流的区别**: 数据流 A 由 Agent 全自动处理(含抠图、美化、棚拍级展示),
输出棚拍级单品图;数据流 B 由用户在浏览器中半自动操作(上传后手动调整),
不含 AI 处理。两条流的数据最终都汇总到 `wardrobe.json`。

## Web 应用(`app/wardrobe-app.html`)

一个自包含的 HTML 文件,浏览器直接打开即可使用,无需安装任何依赖。

### 五大功能页

| 页签 | 功能 | 说明 |
|------|------|------|
| 分类浏览 | 按种类+季节浏览 | 按 slot 分组,季节筛选(春/夏/秋/冬/四季),可修改分类、删除单品、移至回收 |
| 品牌浏览 | 按品牌分类 | 有品牌归品牌组,无品牌归「未知品牌」组,可手动输入品牌名 |
| 搭配卡 | 拖拽式搭配生成 | 左侧单品库选品,画布上拖拽摆位、缩放、置顶、移除,底部输入标题,一键导出 PNG |
| 展示墙 | 全单品展示墙 | 4 列网格按种类排列,统一奶油米色背景 |
| 回收 | 二手出售/捐赠 | 将不穿的衣服标记为出售(输入原价+售价+成色+渠道)或捐赠(选机构) |

### 批量上传

- 支持一次上传最多 **30 件**单品
- 上传后自动创建卡片,可后续修改分类、品牌、季节
- 上传进度条实时显示

### 回收功能

- **二手出售**:输入原价、出售价格、成色(全新~6成新)、渠道(闲鱼/转转/朋友圈等)
- **捐赠**:选择捐赠机构(爱心衣救/白鲸鱼/飞蚂蚁等)
- 顶部汇总:出售总数 + 预计总收入
- 可随时移回衣橱

## 工作流

### 1. 录入单品(AI 录入流)

对用户上传的每张单品照片(支持批量,一次最多 30 件):

1. 识别槽位与档案字段(slot / label / color / style / seasons / brand / features),
   规则见 [references/categories.md](references/categories.md)
   - seasons 为数组,取值 春/夏/秋/冬/四季,一件可多季
   - brand 为可选字段,识别不出时留空(不编造品牌名)
   - features 为可选数组,记录单品特征(面料、领型、五金件等)
2. 抠图:
   - 先试 `python3 scripts/remove_bg.py <照片> -d items/`(需 `pip install rembg`)
   - 批量处理时单张失败不中断后续, 失败项在 stderr 输出
   - 不可用时走备选方案,见 [references/style-guide.md](references/style-guide.md)「抠图备选」
3. 抠图存为透明底 PNG,统一放进工作目录的 `items/`
4. **美化(去皱板正)**:让拍出来的衣服褶皱少、整洁板正,呈电商 catalog 质感
   - 首选 **AI 重绘**(效果好一个量级):用图像生成工具 image-to-image,
     透明底 + 1:1,prompt 模板:

     ```
     Professional e-commerce flat-lay product photo of the exact same
     {单品描述} from the reference image, faithfully preserving its color,
     print pattern, and silhouette. Neatly pressed, no wrinkles, symmetrical
     flat lay on transparent background, soft studio lighting, high detail.
     ```

     注意:
     - 单品形态易漂移时(连衣裙/连体裤等)在 prompt 里写死结构
     - 遇到限流(HTTP 424)就 sleep 20–30 秒后重试
     - **逐件审查**重绘结果与原图的保真度
   - 无 AI 重绘能力时回退本地脚本(仅处理 RGBA/透明底 PNG):

     ```bash
     python3 scripts/beautify_item.py items/item1.png -o items/item1.png
     ```

5. **棚拍级单品图生成**:将美化后的单品统一封装为棚拍级展示图
   - 1500×1500 奶油米色(#F5F1E8)画布,8% 内边距
   - AI 平铺图输入目录(`--flat-dir`)与 card 输出目录(`--outdir`)分离
   - 优先使用 AI 平铺图(-flat.jpg),用 rembg 精准去背景
   - 无 AI 平铺图时回退到 rembg 抠图 + 棚拍增强管线
   - 自动裁切 AI 水印(底部 6%)、去白边光晕、边缘羽化、阴影压制、自动色阶
   - 底部添加品牌名(有品牌,粗体)或「品类·样式」标签(无品牌,常规)

     ```bash
     # 输入: wardrobe.json, items/, closet-studio/(AI平铺图)
     # 输出: closet-studio/(*-card.png)
     python3 scripts/make_studio_cards.py wardrobe.json
     ```

6. **预览墙生成**:将所有单品 card 图排列成 4 列网格预览墙

     ```bash
     python3 scripts/make_contact_sheet.py wardrobe.json
     ```

7. 向用户回报清单:每件一行「slot · label · 文件名」

### 2. 编辑单品

已录入的单品可随时修改:

| 修改项 | 方式 | 工具 |
|--------|------|------|
| slot 分类 | AI 对话 / Web 应用下拉选择 | 对话 or `app/wardrobe-app.html` |
| 品牌名 | AI 对话 / Web 应用文本输入 | 对话 or `app/wardrobe-app.html` |
| 季节标签 | AI 对话 / Web 应用标签切换 | 对话 or `app/wardrobe-app.html` |
| label 描述 | AI 对话修改 wardrobe.json | `wardrobe.json` |
| features 特征 | AI 对话追加/修改 | `wardrobe.json` |
| 重新抠图 | 重跑 remove_bg.py | `python3 scripts/remove_bg.py <照片> -d items/` |
| 重新美化 | 重跑 beautify_item.py | `python3 scripts/beautify_item.py items/<file> --strength 0.9` |
| 重新生成 card | 重跑 make_studio_cards.py | `python3 scripts/make_studio_cards.py wardrobe.json` |
| 删除单品 | Web 应用删除按钮 / AI 对话 | `app/wardrobe-app.html` or 编辑 `wardrobe.json` |

编辑后需重跑受影响的脚本(美化 → card → 预览墙)以更新展示图。

### 3. Web 应用管理

打开 `app/wardrobe-app.html` 进行可视化管理:
- **分类浏览**:按种类+季节筛选,修改分类、删除、移至回收
- **品牌浏览**:按品牌分组,手动输入/修改品牌名
- **搭配卡**:拖拽选品、缩放置顶、输入标题、导出 PNG
- **展示墙**:4 列网格全览
- **回收**:二手出售(原价+售价+成色+渠道)或捐赠(机构选择)

### 4. 挑选搭配

用户说「帮我搭」时:
- 按 [references/categories.md](references/categories.md) 槽位规则组一套
- 遵循槽位冲突解决策略(互斥槽位优先保留 dress, 同槽位默认保留最后选择)
- 说明理由(配色、风格、场合),让用户确认或替换
- 用户也可在 Web 应用搭配卡页自行拖拽选品

### 5. 生成搭配卡

两种版式,默认用小红书竖版:

1. **小红书竖版(默认)**:`scripts/compose_card_xhs.py`
   - 1152×2048(9:16),纯白底,杂志剪贴感,柔和投影 + 微旋转
   - 自动擦除 AI 水印(带误伤检测:无水印跳过/异常高跳过/正常擦除)
2. **经典 3:4 带标签版**:`scripts/compose_card.py`

```bash
python3 scripts/compose_card_xhs.py spec.json -o outfit-card.png
```

spec JSON 示例见 [`examples/spec-sample.json`](examples/spec-sample.json)。
spec 支持 `layout` 自定义摆位(拖拽定稿时由前端传入):
`{"x","y","h","rot","z"}` = 中心点比例坐标、高度比例、旋转角、层叠顺序。

### 6. 二手回收

在 Web 应用「回收」页:
- 将不需要的单品移至**二手出售**(输入原价、售价、成色、渠道)
- 或移至**捐赠**(选择捐赠机构)
- 可随时移回衣橱

## 注意

- 脚本依赖: Pillow(必需), rembg + numpy(棚拍级 card), opencv-python-headless(本地去皱)
- Web 应用为纯前端,无需安装任何依赖,浏览器直接打开
- 标签含中文时脚本自动切换 CJK 字体
- 用户没有品牌信息时,label 用「品类 + 颜色」,不编造品牌名
- 全局约束见 [constraints/rules.md](constraints/rules.md)
- 数据结构校验见 [`wardrobe.schema.json`](wardrobe.schema.json)
