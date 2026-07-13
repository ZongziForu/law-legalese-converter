# 法言法语黑话转换器 v4

> 将中文大白话或普通法律表述，转换为高度抽象、名词化、体系化、教义学化、老派民法式、古典法言式、民国判牍式或“过度认真式搞怪”的法学表达。

本 Skill 的核心不是简单替换几个法律术语，而是在**保留原命题、事实关系、情态强度与明示结论**的前提下，对文本进行结构重写、概念升格和语体塑形。

它采用以下三层控制结构：

```text
任务模式 task_mode
×
文风预设 preset
×
可覆盖参数 parameters
```

- **任务模式**决定“可以增加什么内容”；
- **文风预设**决定“默认写成什么味道”；
- **具体参数**决定“到底多晦涩、多文言、多搞怪、写多长”。

---

# 一、快速上手

## 1. 最简单的用法

直接提供文本，并说明想要的风格即可：

```text
把下面这句话改写成法言法语：

诈骗罪要求欺骗导致认识错误，再由错误导致处分财物。
```

未作其他说明时，Skill 使用：

```yaml
task_mode: rewrite
preset: general_blacktalk
```

即：**只改写，不扩充理论；使用默认通用黑话风格。**

也可以直接使用中文自然语言调节：

```text
把下面这段扩写成教义学浓的风格，术语密度拉满，
但别太长，膨胀倍率控制在 1.3：

……
```

无需记忆英文参数名。

---

## 2. 三种任务模式

任务模式控制的是**内容权限**，不是单纯的篇幅大小。

| 中文模式 | 英文参数 | 作用 | 可以增加什么 | 不可以做什么 |
|---|---|---|---|---|
| 改写 | `rewrite` | 默认模式，只改变表达 | 术语、抽象结构、原句已有关系的显化、文风 | 不增加新理论、新事实或新结论 |
| 扩写 | `expand` | 对原命题作受控理论化展开 | 相关概念、解释框架、概念区分、限定性的理论判断 | 不增加具体事实，不擅自得出责任或效力结论 |
| 分析 | `analysis` | 真正进行法律分析 | 构成要件、请求权、学说比较、法律适用及结论 | 不得伪造法条、判例或资料；现实法律需核验 |

### 2.1 `rewrite｜改写`

适合：

- “换成法言法语”
- “写得像法学论文”
- “写得不说人话一点”
- “改成老派民法教材口吻”
- “搞怪一点，但不要扩写”

示例：

```text
任务模式：改写。
使用通用黑话预设，强度 4，篇幅短。

原文：室友不洗碗。
```

此模式可以把“室友不洗碗”写得极其庄严、抽象，但不能偷偷补入“长期”“屡次”“影响他人生活”等原文没有的事实。

### 2.2 `expand｜扩写`

适合：

- “补充相关法学概念”
- “加入一些理论判断”
- “展开成一段论述”
- “从法理上丰富一下，但不要直接下结论”

示例：

```text
任务模式：扩写。
使用教义学浓预设，只补充与原命题直接相关的概念，
膨胀倍率不超过 1.5，不要给出确定法律结论。

原文：平台收集用户信息，用户不知道用途，后来平台把信息给了第三方。
```

扩写模式允许引入“透明性、目的限定、信息自决、控制能力不对称”等解释框架，但不能据此直接断言平台违法或必然承担责任。

### 2.3 `analysis｜分析`

适合：

- “判断是否构成犯罪”
- “按请求权基础分析”
- “比较不同学说”
- “形成法律意见”
- “适用现行法并给出结论”

示例：

```text
任务模式：分析。
请按犯罪构成进行判断，并核验现行法律依据。
表达风格使用教义学浓预设，但不要让文风掩盖不确定性。

案情：……
```

分析模式调用的是宿主模型的法律研究与推理能力；本 Skill 主要负责控制表达方式、事实边界和论证结构，**本身不等于法律数据库**。

---

## 3. 六种文风预设

预设是一组起始参数。它决定默认语感，但**不会突破任务模式的权限上限**。

| 中文预设 | 英文参数 | 风格特征 | 适合场景 |
|---|---|---|---|
| 通用黑话（默认） | `general_blacktalk` | 抽象、名词化、体系化，但仍较通用 | 普通句子、社交平台玩梗、日常法律表达 |
| 教义学浓 | `doctrinal_dense` | 术语密度高、句法嵌套强、体系定位明显 | 刑法、民法理论表述、论文腔 |
| 老派民法 | `old_school_civilist` | 半文半白、原则—限制式结构、旧式教材节奏 | 民法、商法、合同、物权表达 |
| 古典法言 | `classical_legalese` | 古雅连接词、按断式表达、文言成分高 | 古风改写、戏仿、简短判词感 |
| 民国判牍 | `republican_judgment` | 裁判文书节奏、民国判牍语感、庄重审断 | 判牍戏仿、裁判书语体转换 |
| 搞怪过载 | `absurd_overkill` | 术语和论证规模严重超过事情本身 | 小事大写、娱乐性黑话、荒诞反差 |

### 预设不会自动改变任务模式

例如：

```text
使用教义学浓预设
```

不等于允许扩写，更不等于允许自动判断罪名。

```text
使用搞怪过载预设
```

也不等于允许编造伪学说、伪外语或假判例。

需要增加理论时，应明确写：

```text
任务模式：扩写
```

需要形成法律结论时，应明确写：

```text
任务模式：分析
```

---

## 4. 一句话调预设

```text
用通用黑话预设改写下面这句话：……
```

```text
用老派民法预设，半文半白，篇幅短：……
```

```text
用古典法言预设，但保持当代语境，不要加入古代官名或制度：……
```

```text
用搞怪过载预设，极度不说人话，但控制在两句话以内：……
```

```text
扩写下面内容，使用教义学浓预设，只补一个解释框架，膨胀倍率 1.3：……
```

---

## 5. 三种调参方式

### 方式 A：中文自然语言

推荐日常使用。

```text
扩写，教义学浓，术语密度 5，句法复杂度 4，
过度论证度 3，篇幅标准，膨胀倍率 1.4。
```

### 方式 B：英文参数名

适合需要稳定、可复制配置的场景。

```text
task_mode=expand
preset=doctrinal_dense
terminology_density=5
syntactic_complexity=4
argumentative_overkill=3
output_length=standard
expansion_ratio=1.4
```

### 方式 C：YAML 配置

适合批量处理、保存配置或与 Agent 工作流结合。

```yaml
task_mode: expand
preset: doctrinal_dense
intensity: 4
output_length: standard
expansion_ratio: 1.4
syntactic_complexity: 4
terminology_density: 5
doctrinal_elaboration: 2
archaism: 1
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 3
historical_register: contemporary
authority_policy: none
text_scope: paragraph
coherence_mode: global
```

配置后附上待处理文本即可。

---

# 二、参数速查：中英对照

## 1. 任务与预设参数

| 英文参数 | 中文名 | 可选值 | 说明 |
|---|---|---|---|
| `task_mode` | 任务模式 | `rewrite` 改写 / `expand` 扩写 / `analysis` 分析 | 决定内容权限 |
| `preset` | 文风预设 | 六种预设 | 决定默认风格配方 |

---

## 2. 篇幅控制参数

| 英文参数 | 中文名 | 可选值 | 说明 |
|---|---|---|---|
| `output_length` | 篇幅 | `short` 短 / `standard` 标准 / `expanded` 长 | 控制绝对篇幅 |
| `expansion_ratio` | 膨胀倍率 | `0.5–3.0` | 控制输出字数相对输入字数的上限 |

### `output_length｜篇幅`

- `short`：通常为一至两句；
- `standard`：通常为一段；
- `expanded`：允许多段展开。

### `expansion_ratio｜膨胀倍率`

计算方式：

```text
膨胀倍率 = 输出字数 ÷ 输入字数
```

常用值：

| 值 | 效果 |
|---:|---|
| `0.5–0.9` | 压缩表达 |
| `1.0` | 不变长；新增概念只能通过替换进入 |
| `1.3` | 轻度展开，适合“扩写但别太长” |
| `1.5` | 默认扩写量 |
| `2.0` | 一段论述级展开 |
| `2.5–3.0` | 充分展开，上限级别 |

规则：

- `output_length` 与 `expansion_ratio` 冲突时，取更严格的限制；
- `rewrite` 仍是改写模式，输出膨胀上限固定为约 `1.3`；
- `expand` 默认约 `1.5`，最高 `3.0`；
- “写得晦涩”不等于“写得更长”。

---

## 3. 风格强度参数

| 英文参数 | 中文名 | 范围 | 控制内容 |
|---|---|---:|---|
| `intensity` | 总体强度 | 1–5 | 整体“不说人话”程度 |
| `syntactic_complexity` | 句法复杂度 | 1–5 | 从句、限定、嵌套和长句程度 |
| `terminology_density` | 术语密度／黑话浓度 | 1–5 | 法学术语出现频率 |
| `doctrinal_elaboration` | 教义展开度 | 0–3 | 理论内容的权限级别 |
| `archaism` | 文言度 | 0–5 | 古雅词面和半文半白程度 |
| `foreign_terms` | 外语密度 | 0–5 | 外语术语的使用倾向 |
| `humor_absurdity` | 搞怪度 | 0–5 | 荒诞反差与娱乐效果 |
| `argumentative_overkill` | 过度论证度 | 0–5 | 对简单命题进行多层论证的程度 |

### 建议理解方式

#### `intensity｜总体强度`

- `1`：轻微专业化；
- `3`：默认黑话浓度；
- `5`：极度抽象、名词化和体系化。

它只控制风格强弱，不会自动授权扩写或分析。

#### `syntactic_complexity｜句法复杂度`

- `1`：短句、少从句；
- `3`：适度限定和嵌套；
- `5`：多层从句、插入说明、递进结构，但仍须可以回译。

#### `terminology_density｜术语密度`

- `1`：仅替换少量关键词；
- `3`：术语与普通表达混合；
- `5`：高密度法学概念和抽象名词。

高术语密度不等于可以增加新的理论命题。

#### `doctrinal_elaboration｜教义展开度`

| 值 | 含义 |
|---:|---|
| `0` | 仅词汇升格 |
| `1` | 显化原句已有结构 |
| `2` | 增加相关概念与限定性理论判断 |
| `3` | 完整法律分析 |

模式上限：

| 任务模式 | 默认值 | 上限 |
|---|---:|---:|
| `rewrite` | 1 | 1 |
| `expand` | 2 | 2 |
| `analysis` | 3 | 3 |

显式设置 `doctrinal_elaboration: 2`，可视为授权进入 `expand`。  
完整法律分析仍应明确要求 `analysis`。

#### `archaism｜文言度`

- `0`：纯现代汉语；
- `1–2`：轻微古雅；
- `3`：半文半白；
- `4–5`：明显古典法言或判牍语感。

文言度只改变词面和句法，不会自动增加历史机关、法令、官名或时代事实。

#### `foreign_terms｜外语密度`

- `0`：不使用外语；
- `1–2`：必要时少量使用；
- `3–5`：提高外语术语倾向。

外语术语必须能够确认；无法确认时应自动降低密度，不能现编伪拉丁语、伪德语或伪法谚。

#### `humor_absurdity｜搞怪度`

- `0`：严肃；
- `1–2`：轻微反差；
- `3`：明显戏仿；
- `4–5`：通过庄严措辞与琐碎事件之间的失衡制造笑点。

搞怪来自“过度认真”，不来自编造事实。

#### `argumentative_overkill｜过度论证度`

- `0`：直接表达；
- `1–2`：少量重构；
- `3`：多层说明；
- `4–5`：定义、转折、体系定位和反复限定显著增加。

它控制“论证层数”，不直接控制输出字数。需要压缩时，应同时降低 `expansion_ratio` 或设置 `output_length: short`。

---

## 4. 语境、权威与长文本参数

| 英文参数 | 中文名 | 可选值 | 说明 |
|---|---|---|---|
| `historical_register` | 历史语境 | `contemporary` 当代 / `late_qing` 清末 / `republican` 民国 / `traditional_law` 传统法 / `comparative_history` 比较法史 / `source_bound` 仅依来源 | 控制时代语境 |
| `authority_policy` | 权威策略 | `none` 不引 / `provided_only` 只用用户所给 / `verified` 须可核验 | 控制学者、法条、判例等来源 |
| `text_scope` | 文本范围 | `auto` 自动 / `sentence` 句 / `paragraph` 段 / `document` 篇 | 决定处理单位 |
| `coherence_mode` | 连贯模式 | `local` 局部 / `global` 全局 | 决定是否维护全文术语和风格一致性 |

### `historical_register｜历史语境`

“古雅文风”和“历史事实”是两件事。

例如：

```yaml
preset: classical_legalese
historical_register: contemporary
```

表示可以使用“盖、惟、按、未可遽断”等古雅表达，但不能凭空加入古代官名、法令或程序。

### `authority_policy｜权威策略`

- `none`：默认。不主动引用具体学者、通说、法条号或判例；
- `provided_only`：只使用用户明确提供的来源；
- `verified`：需要真正可核验的来源。

### `text_scope｜文本范围`

- `sentence`：适合单句玩梗；
- `paragraph`：适合一段完整论述；
- `document`：适合长文整体改写；
- `auto`：由 Skill 自动判断。

### `coherence_mode｜连贯模式`

- `local`：逐句或逐段优化；
- `global`：维护全文术语、称谓、强度和模板分布的一致性。

处理长文时推荐：

```yaml
text_scope: document
coherence_mode: global
```

---

# 三、预设的具体配置

下表列出各预设的核心公开参数。用户显式设置的参数会覆盖预设值。

| 预设 | 强度 | 句法 | 术语 | 教义展开 | 文言 | 外语 | 搞怪 | 过度论证 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `general_blacktalk` | 3 | 3 | 3 | 1 | 0 | 0 | 1 | 2 |
| `doctrinal_dense` | 4 | 4 | 5 | 1 | 1 | 1 | 0 | 3 |
| `old_school_civilist` | 4 | 4 | 4 | 1 | 3 | 0 | 0 | 3 |
| `classical_legalese` | 3 | 4 | 3 | 1 | 5 | 0 | 1 | 3 |
| `republican_judgment` | 3 | 4 | 3 | 1 | 4 | 0 | 0 | 3 |
| `absurd_overkill` | 4 | 5 | 5 | 1 | 1 | 0 | 5 | 5 |

## 1. `general_blacktalk｜通用黑话`

```yaml
preset: general_blacktalk
intensity: 3
syntactic_complexity: 3
terminology_density: 3
doctrinal_elaboration: 1
archaism: 0
humor_absurdity: 1
argumentative_overkill: 2
```

特点：兼容性最好，默认使用。

## 2. `doctrinal_dense｜教义学浓`

```yaml
preset: doctrinal_dense
intensity: 4
syntactic_complexity: 4
terminology_density: 5
doctrinal_elaboration: 1
archaism: 1
foreign_terms: 1
humor_absurdity: 0
argumentative_overkill: 3
```

特点：现代法学论文腔明显，但默认仍是改写，不自动启动完整法律分析。

## 3. `old_school_civilist｜老派民法`

```yaml
preset: old_school_civilist
intensity: 4
syntactic_complexity: 4
terminology_density: 4
doctrinal_elaboration: 1
archaism: 3
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 3
historical_register: contemporary
```

特点：半文半白、原则与限制并列、强调法律关系与效力射程。

## 4. `classical_legalese｜古典法言`

```yaml
preset: classical_legalese
intensity: 3
syntactic_complexity: 4
terminology_density: 3
doctrinal_elaboration: 1
archaism: 5
foreign_terms: 0
humor_absurdity: 1
argumentative_overkill: 3
historical_register: contemporary
```

特点：高度古雅，但默认不把文本放进真实古代制度中。

## 5. `republican_judgment｜民国判牍`

```yaml
preset: republican_judgment
intensity: 3
syntactic_complexity: 4
terminology_density: 3
doctrinal_elaboration: 1
archaism: 4
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 3
historical_register: republican
```

特点：调用裁判书语体资源，适合判牍、判词和裁判文书式表达。不得编造案号、机关、程序或史实。

## 6. `absurd_overkill｜搞怪过载`

```yaml
preset: absurd_overkill
intensity: 4
output_length: expanded
expansion_ratio: 2.5
syntactic_complexity: 5
terminology_density: 5
doctrinal_elaboration: 1
archaism: 1
foreign_terms: 0
humor_absurdity: 5
argumentative_overkill: 5
historical_register: contemporary
authority_policy: none
```

特点：以极高术语密度和论证规模制造反差。

该预设默认仍不突破 `rewrite` 权限。若希望加入相关理论并真正展开，应明确指定：

```yaml
task_mode: expand
preset: absurd_overkill
```

---

# 四、怎样调预设和调参数

## 1. 从预设出发，只覆盖需要改变的参数

无需每次提供完整配置。

```text
老派民法预设，但文言度降到 2，篇幅短。
```

等价于：

```yaml
preset: old_school_civilist
archaism: 2
output_length: short
```

## 2. 风格很浓，但不要变长

```text
通用黑话，强度 5，术语密度 5，篇幅短，膨胀倍率 1.0。
```

适合把一句话写得“密”，而不是写得“长”。

## 3. 扩写，但限制理论数量和篇幅

```text
任务模式用扩写，教义学浓，只补一个解释框架，
不要增加具体事实，膨胀倍率 1.3。
```

## 4. 搞怪和冗长分开调

“搞怪度”与“过度论证度”并不相同：

```text
搞怪度 5，过度论证度 1，篇幅短。
```

效果：短而荒诞。

```text
搞怪度 0，过度论证度 5，篇幅标准。
```

效果：严肃但极其繁复。

## 5. 文言和历史分开调

```text
古典法言预设，文言度 5，但历史语境保持当代。
```

效果：词面古雅，不引入古代制度。

## 6. 调参优先级

实际优先级为：

```text
命题核、事实与真实性硬约束
>
任务模式权限上限
>
用户显式参数
>
预设
>
默认值
>
系统推断
```

因此：

- 用户显式设置会覆盖预设；
- 预设不能突破任务模式；
- 参数不能突破真实性和事实边界；
- 风格与准确性冲突时，准确性优先。

---

# 五、可直接复制的配置示例

## 1. 默认黑话改写

```text
用通用黑话改写下面这句话，只改变表达，不增加内容：

【原文】
```

## 2. 极度晦涩但很短

```text
任务模式：改写。
预设：教义学浓。
强度 5，术语密度 5，句法复杂度 4，篇幅短。

【原文】
```

## 3. 老派民法教材腔

```text
任务模式：改写。
预设：老派民法。
文言度 3，过度论证度 4，历史语境保持当代。

【原文】
```

## 4. 古典法言，不历史化

```text
用古典法言预设改写，文言度 5，
但不得加入原文没有的历史机关、法令、官名或程序。

【原文】
```

## 5. 有限扩写

```text
任务模式：扩写。
预设：教义学浓。
只增加与原命题直接相关的概念和解释框架，
不要作确定法律结论，膨胀倍率不超过 1.3。

【原文】
```

## 6. 搞怪过载，但不失控

```text
任务模式：改写。
预设：搞怪过载。
搞怪度 5，过度论证度 4，篇幅短。
不增加任何事实、原因、频率、后果或法律结论。

【原文】
```

## 7. 长文统一改写

```yaml
task_mode: rewrite
preset: doctrinal_dense
text_scope: document
coherence_mode: global
intensity: 4
terminology_density: 4
output_length: standard
```

```text
请保持标题、段落和编号结构，统一全文术语与主体称谓：

【全文】
```

## 8. 正式法律分析

```yaml
task_mode: analysis
preset: doctrinal_dense
authority_policy: verified
text_scope: document
coherence_mode: global
```

```text
请区分已知事实与假设，核验现行法和引用来源，
再形成法律分析：

【事实与问题】
```

---

# 六、实现原理

## 1. 总体架构

Skill 不是一个单一的“风格提示词”，而是由主规则、转换机制、句式模板、领域词库、风格资源、参数路由与验证协议组成的分层系统。

```text
SKILL.md
├── 模式与权限
├── 命题核保真
├── 领域识别
├── 预设和参数合并
├── 资源召回
├── 生成流程
└── 最低质量门槛

references/
├── 转换机制
├── 句式模板
├── 通用与部门法词库
├── 各文风资源
├── 参数与路由
├── 示例
├── 控制与验证
└── 裁判书语体资源
```

主文件 `SKILL.md` 是最高优先级规则。其他文件只提供资源与下位操作方法，不得突破主文件的事实、模式和真实性约束。

---

## 2. 唯一运行路径

每次转换遵循同一条主流程：

```text
识别 task_mode
→ 提取 source_core
→ 判断文本范围和法律领域
→ 载入 preset
→ 合并用户显式参数
→ 应用模式上限与真实性硬约束
→ 选择机制、模板和小词包
→ 生成文本
→ 对照 source_core
→ 审计新增内容
→ 整体回译
→ 输出成文结果
```

六种预设不会各自启动一套独立工作流。它们只是不同的参数配方和资源偏好，因此能够互相覆盖、组合和微调。

---

## 3. 命题核 `source_core`

生成前，Skill 会把输入拆成不可随意改变的命题核：

```yaml
source_core:
  subjects: []
  actions_or_states: []
  objects_or_interests: []
  relations: []
  causal_links: []
  conditions: []
  modality: []
  explicit_conclusions: []
  negations_and_exceptions: []
  attributions_or_quotes: []
```

重点保护：

- 主体数量、角色及相互关系；
- 行为、状态和对象；
- 所有、占有、控制、保管、使用等关系差异；
- 时间先后、因果和条件；
- “可能、通常、原则上、应当、必须、不得”等情态强度；
- 肯定、否定及其作用范围；
- 原句已经明确给出的结论；
- 引述、主张和评价的归属。

例如：

```text
乙的钱包
```

不能当然改写成：

```text
乙占有的钱包
```

因为“归属”与“占有”不是同一关系。

---

## 4. 扩写账本 `addition_ledger`

只有 `expand` 和 `analysis` 会建立新增内容账本：

```yaml
addition_ledger:
  added_concepts: []
  added_theoretical_judgments: []
  relation_to_source: []
  limiting_language: []
  prohibited_factual_inferences: []
```

每项新增内容都要回答：

```text
它是在解释原命题，
还是在偷偷替原命题增加事实或结论？
```

扩写内容还需通过三项相关性检查：

1. 能否说明该概念与原命题的直接关系？
2. 删除该概念后，原命题是否仍完整存在？
3. 该概念是否依赖原文未提供的具体事实？

合格答案应当是：

```text
能；是；否
```

否则应删除，或改为明确的条件性、解释性表达。

---

## 5. 任务模式是权限门

Skill 将可用操作分成三层：

```text
lexical_rewrite
结构和词汇改写
↓
structural_explication
显化原句已有关系
↓
doctrinal_supplement
增加相关概念与理论
↓
full_analysis
完整法律分析
```

对应关系：

| 模式 | 权限 |
|---|---|
| `rewrite` | 词汇改写 + 原有结构显化 |
| `expand` | 上述权限 + 教义性补充 |
| `analysis` | 全部权限，但现实法律需核验 |

这避免了一个常见错误：模型一见到刑法或民法术语，就自动开始“办案”。

---

## 6. 领域路由

Skill 会判断文本所属领域：

```yaml
legal_domain:
  general
  criminal
  civil
  commercial
  labor
  administrative
  intellectual_property
  data_platform
  procedure
  legal_theory
  legal_history
  mixed
```

领域只影响词库和概念资源，不直接决定法律结论。

例如：

- 刑法文本优先使用行为、结果、风险、归责等资源；
- 民商法文本优先使用意思表示、法律关系、效力、履行等资源；
- 数据平台文本优先使用信息利益、控制、透明性、目的限定等资源；
- 程序文本优先使用主张、证明、程序行为和裁判语域资源。

---

## 7. 十六种转换机制

Skill 内置十六类转换操作：

| 编号 | 机制 | 作用 |
|---|---|---|
| M01 | 主体功能化 | 将日常主体改写为关系中的功能主体 |
| M02 | 行为名词化 | 将动作改写为抽象行为或状态 |
| M03 | 对象／利益抽象化 | 将具体对象提升为利益或关系对象 |
| M04 | 关系重构 | 把主体、行为、关系变化重新组织 |
| M05 | 因果链显化 | 展开原句已有的因果节点 |
| M06 | 否定—重构 | 使用“并非……而是……”进行同义升格 |
| M07 | 情态与条件展开 | 保持可能、应当、必须等强度 |
| M08 | 体系定位 | 将命题置于关系、效力、规范或制度层面 |
| M09 | 效力与射程表达 | 表达作用对象、范围和阶段 |
| M10 | 事实—规范分层 | 区分事实描述与规范表达 |
| M11 | 概念严分 | 在扩写中区分相关概念 |
| M12 | 定义递归 | 对概念进行多层定义和改述 |
| M13 | 相关理论增益 | 引入直接相关的解释框架 |
| M14 | 价值张力与利益衡量 | 呈现相关价值之间的张力 |
| M15 | 语体滤镜 | 叠加现代、老派、古典或判牍语体 |
| M16 | 过度论证式搞怪 | 用不成比例的论证规模制造反差 |

单次生成通常只选择其中数项，而不是机械使用全部机制。

---

## 8. 模板与小词包

生成资源分为三类：

### 8.1 句式模板

包括：

- 主体功能化；
- 行为名词化；
- 关系重构；
- 否定—重构；
- 因果链；
- 情态保留；
- 条件保留；
- 效力射程；
- 谨慎收束；
- 理论概念引入；
- 原则与限制；
- 老派民法、古典法言、民国判牍模板。

模板提供结构，不提供案件事实或法律结论。

### 8.2 领域词库

包括：

- 通用法学词库；
- 刑法词库；
- 民商法词库；
- 行政法、知识产权、数据平台、程序法、劳动法、法理学等微型词包。

词库按领域、模式和风险过滤，不会整库倾倒。

### 8.3 风格资源

包括：

- 现代教义学语体；
- 老派民法学术腔；
- 古典法言与民国判牍；
- 裁判书语体词库。

其中裁判者端词汇受到额外门控，避免把当事人陈述擅自改成法院已经“认定”或“采信”的结论。

---

## 9. 参数合并逻辑

参数处理不是简单覆盖，而是分层合并：

```text
默认值
→ 载入预设
→ 应用用户显式参数
→ 检查任务模式权限
→ 检查事实和真实性约束
→ 解决篇幅、风格和语境冲突
```

典型冲突处理：

| 冲突 | 处理方式 |
|---|---|
| 高强度 + 短篇幅 | 提高单位字数内的密度，减少展开层数 |
| 高术语密度 + `rewrite` | 多用术语，但不增加新理论 |
| 高搞怪 + 低过度论证 | 短而荒诞 |
| 低搞怪 + 高过度论证 | 严肃冗密 |
| 老派民法 + 当代语境 | 使用旧式句法，不增加历史机构 |
| 古典法言 + 当代语境 | 使用古典词面，不增加古代制度 |
| 扩写 + 不引权威 | 可自建解释框架，不冒称通说 |
| 外语密度高 + 无法确认术语 | 自动降低外语密度 |
| 长篇幅 + 低膨胀倍率 | 取更严格限制并压缩 |
| 原句关系不明 | 使用中性称谓，不猜测法律关系 |

---

## 10. 验证与回译

生成后会进行两类检查。

### 10.1 `rewrite` 检查

- 主体、行为、对象是否一致；
- 关系是否被擅自改变；
- 因果、条件和否定范围是否一致；
- 情态和结论强度是否一致；
- 是否新增事实；
- 是否新增理论结论；
- 是否符合指定风格和篇幅。

回译标准：

```text
将输出压缩回普通语言后，应与原输入命题等值。
```

### 10.2 `expand` 检查

- 原命题是否完整保留；
- 新概念是否与原文直接相关；
- 理论判断是否使用限定性表达；
- 是否新增具体事实；
- 是否虚构权威；
- 是否超出膨胀倍率；
- 风格是否连贯。

回译标准：

```text
输出应能被拆分为：
原命题 + 可明确识别的概念性补充。
```

补充内容不能反向改变原命题。

---

## 11. 长文本一致性

处理段落或全文时，Skill 会内部维护：

```yaml
glossary: {}
template_history: []
paragraph_functions: []
intensity_baseline: 1-5
```

用于实现：

- 同一主体使用稳定称谓；
- 同一法律关系使用相同核心术语；
- 避免连续重复同一高辨识度句式；
- 控制各段功能；
- 保持全文强度稳定；
- 防止后文把前文的中性关系升级为确定法律关系。

---

## 12. 真实性与安全边界

在任何模式下，均不得无依据生成：

- 具体人物、时间、地点、金额、动机、证据或程序；
- 法条号、判例号、案号；
- 学者姓名、通说、少数说、著作或页码；
- 伪外语、伪法谚、伪历史；
- 原文没有的责任、效力、罪名、赔偿或胜败结论。

可以使用抽象解释框架，但不能把它伪装成确定的现行法结论。

例如可以写：

```text
可进一步从合理信赖与诚信控制的角度加以观察。
```

但不能在缺乏事实与法律依据时直接写：

```text
因此对方当然构成违约并应承担赔偿责任。
```

---

# 七、项目文件结构

```text
law-legalese-converter/
├── SKILL.md
└── references/
    ├── 00_project_readme.md
    ├── 01_conversion_mechanisms.md
    ├── 02_sentence_templates.md
    ├── 03_lexicon_general.md
    ├── 04_lexicon_criminal.md
    ├── 05_lexicon_civil_commercial.md
    ├── 06_domain_micro_packs.md
    ├── 07_resource_modern_doctrinal.md
    ├── 08_resource_old_school_civilist.md
    ├── 09_resource_classical_republican.md
    ├── 10_parameters_and_routing.md
    ├── 11_examples.md
    ├── 12_control_and_validation.md
    ├── 13_test_set.md
    ├── 14_source_provenance.md
    └── 15_lexicon_judicial_register.md
```

主要文件职责：

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 主流程、模式权限和最高优先级约束 |
| `01_conversion_mechanisms.md` | 十六种复杂化机制 |
| `02_sentence_templates.md` | 可迁移的句法骨架 |
| `03–06` | 通用和部门法词库 |
| `07–09` | 三类核心文风资源 |
| `10_parameters_and_routing.md` | 参数、预设、别名与冲突处理 |
| `11_examples.md` | 模式和风格示例 |
| `12_control_and_validation.md` | 保真、扩写、真实性与回译规则 |
| `13_test_set.md` | 回归检查材料 |
| `14_source_provenance.md` | 开发溯源，日常运行无需读取 |
| `15_lexicon_judicial_register.md` | 裁判书语体词库及门控规则 |

---

# 八、推荐使用习惯

1. **先选任务模式，再选预设。**  
   “要不要加内容”比“写成什么味道”优先级更高。

2. **篇幅和理论量分开控制。**  
   想要“短而密”，提高术语密度并降低膨胀倍率；想要“长而不新增理论”，使用 `rewrite` 并调整句法与论证层次。

3. **大多数时候只需要调四个旋钮。**  
   推荐常用组合：

   ```text
   预设 + 强度 + 篇幅/膨胀倍率 + 搞怪度
   ```

4. **长文使用全局连贯。**

   ```yaml
   text_scope: document
   coherence_mode: global
   ```

5. **现实案件分析使用可核验权威策略。**

   ```yaml
   task_mode: analysis
   authority_policy: verified
   ```

6. **风格越夸张，越要写清楚禁止新增事实。**

---

# 九、常见问题

## Q1：教义学浓预设会自动帮我分析案件吗？

不会。预设只影响文风。默认仍为 `rewrite`，不会自动判断罪名、请求权或责任。

## Q2：怎样让它扩写，但不要写成小论文？

使用：

```text
任务模式：扩写；膨胀倍率 1.2–1.4；篇幅短或标准。
```

## Q3：怎样做到“非常不说人话，但字数基本不变”？

使用：

```text
强度 5，术语密度 5，句法复杂度 4，
膨胀倍率 1.0，篇幅短。
```

## Q4：搞怪度和过度论证度有什么区别？

- 搞怪度控制荒诞反差；
- 过度论证度控制论证层数；
- 篇幅由 `output_length` 和 `expansion_ratio` 另行控制。

## Q5：能否混合预设？

Skill 以一个主预设为基础，再通过参数覆盖实现混合。例如：

```text
以老派民法为主，文言度提高到 4，搞怪度调到 2。
```

## Q6：可以让它引用学者、法条和判例吗？

可以，但应设置：

```yaml
authority_policy: provided_only
```

或：

```yaml
authority_policy: verified
```

默认 `none` 不主动生成具体权威。

## Q7：为什么分析模式仍可能要求核验资料？

因为本 Skill 的核心能力是表达控制与事实边界管理，而不是内置实时法律数据库。涉及现行法律、司法解释、判例和最新制度时，应由宿主模型进行可靠检索和核验。

---

# 十、最小记忆版

只需要记住下面几句：

```text
改写 = 只换说法
扩写 = 可以补相关概念，但不下确定结论
分析 = 真正做法律判断，现实资料要核验
```

```text
预设决定味道
参数决定浓度
模式决定权限
真实性约束永远优先
```

最常用指令模板：

```text
【改写/扩写/分析】下面内容，
使用【通用黑话/教义学浓/老派民法/古典法言/民国判牍/搞怪过载】预设，
强度【1–5】，篇幅【短/标准/长】，膨胀倍率【0.5–3.0】，
并保持原事实、关系、情态和结论不变：

【文本】
```

---

# 十一、语料素材来源

本 skill 的词库、句法与风格资源取材于以下文献：

| 作者 / 编者 | 书名 |
| :--- | :--- |
| 朱庆育 | 《民法总论（第二版）》 |
| 郭卫 编；吴宏耀、郭恒、李娜 点校 | 《大理院判决例全书》 |
| 许玉秀 | 《当代刑法思潮》 |
| 史尚宽 | 《物权法论》 |
| 王泽鉴 | 《民法学说与判例研究》 |
| 林山田 | 《刑法通论》 |
| 汪庆祺 编 | 《各省审判厅判牍》 |
| 郭卫 编著；吴宏耀、郭恒 点校 | 《民国大理院解释例全文》 |
| 沈家本 | 《历代刑法考》 |
| 台湾司法院 | 《裁判通俗化用語彙整表》 |

词库与风格资源系从此等文献中提取概念、语料与句法模式后重组加工，未完整引用原文。

---

# 十二、关于作者 / Contact

有任何问题欢迎随时交流！你可以从以下任何一种方式找到我～

| 平台 | 名称 | 链接 / 联系方式 |
| :--- | :--- | :--- |
| 小红书 | 只有肉粽子才算是粽子ney！ | [点击访问](https://xhslink.com/m/5XGgBInSyJc) |
| 微信公众号 | 正在施工的二层楼 | [点击访问](https://mp.weixin.qq.com/s/KUhM7u6ajCfLsw0KDXluZQ) |
| 邮箱 | — | `yqc0122@163.com` |

---
