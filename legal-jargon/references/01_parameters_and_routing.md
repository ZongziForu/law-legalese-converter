<!-- chunk: r01.h000 -->
# 参数、中文别名、预设与路由

> 参数用于稳定理解用户的自然语言要求。用户无需填写 YAML；英文参数名、中文名称和常见口语表达具有同等效力。

<!-- chunk: r01.h001 -->
## 一、参数分层

<!-- chunk: r01.h002 -->
### A. 常用参数

| 英文参数 | 中文名称 | 取值 | 作用 |
|---|---|---|---|
| `task_mode` | 任务模式 | rewrite / expand / analyze | 决定允许增加什么 |
| `preset` | 风格预设 | 七种预设 | 决定写成什么样 |
| `intensity` | 黑话强度 | 1—5 | 总体抽象化与“不说人话”程度 |
| `output_length` | 篇幅 | minimal / short / standard / long / extended | 软性输出预算 |
| `length_limit` | 硬性篇幅上限 | N字 / N句 / N段 / 约N倍 | 用户的明确上限 |
| `expansion_budget` | 理论增量 | 0—3 | `expand` 中可新增的概念框架数量与深度 |
| `humor_absurdity` | 搞怪度 | 0—5 | 庄严措辞与题材规模的反差 |
| `argumentative_overkill` | 过度论证度 | 0—5 | 同义递进、限定与结构铺陈程度 |

<!-- chunk: r01.h003 -->
### B. 高级覆盖项

| 英文参数 | 中文名称 | 取值 |
|---|---|---|
| `syntactic_complexity` | 句法复杂度 | 1—5 |
| `terminology_density` | 术语密度 | 1—5 |
| `archaism` | 古雅度／半文言度 | 0—5 |
| `foreign_terms` | 外语术语显现度 | 0—5 |
| `historical_register` | 历史语境 | contemporary / source_bound / late_qing / republican / traditional_law / comparative_history |
| `authority_policy` | 权威策略 | none / provided_only / verified |
| `text_scope` | 文本范围 | auto / sentence / paragraph / document |
| `coherence_mode` | 一致性 | local / global |
| `format_preservation` | 格式保留 | strict / relaxed |

常用参数优先满足；高级参数只在用户明确要求时覆盖。

---

<!-- chunk: r01.h004 -->
## 二、中英对照与自然语言别名

中英对照是必要的输入兼容层，但不应要求用户背诵参数。只需在本文件集中维护一次，不在每个资源文件重复。

<!-- chunk: r01.h005 -->
### 模式别名

| 用户表达 | 规范化结果 |
|---|---|
| “只改写”“不要补理论”“保守一点” | `task_mode: rewrite` |
| “扩写”“展开一点”“可以补概念但别下结论” | `task_mode: expand` |
| “分析”“判断是否成立”“适用法律”“给出结论” | `task_mode: analyze` |

<!-- chunk: r01.h006 -->
### 篇幅别名

| 用户表达 | 规范化结果 |
|---|---|
| “一句话”“极短” | `output_length: minimal` |
| “短一点”“简洁”“别太啰嗦” | `output_length: short`，并降低过度论证层数 |
| “适中”“正常长度” | `output_length: standard` |
| “详细一点”“写长一点” | `output_length: long` |
| “充分展开”“尽量展开” | `output_length: extended` |
| “不超过200字／两句／一段／原文两倍” | 写入 `length_limit`，优先于命名档位 |

<!-- chunk: r01.h007 -->
### 理论增量别名

| 用户表达 | 规范化结果 |
|---|---|
| “不要引入新概念” | `expansion_budget: 0`；通常进入 rewrite |
| “补一个相关概念即可” | `expansion_budget: 1` |
| “可以加入几组理论视角” | `expansion_budget: 2` |
| “多角度充分展开，但别下结论” | `expansion_budget: 3` |

<!-- chunk: r01.h008 -->
### 其他常见表达

| 用户表达 | 参数变化 |
|---|---|
| “再黑话一点” | `intensity +1` |
| “更绕，但不要更长” | `syntactic_complexity +1`，篇幅不变 |
| “专业词多一点” | `terminology_density +1` |
| “搞怪一点” | `humor_absurdity +1` |
| “少一点车轱辘话” | `argumentative_overkill -1` |
| “半文半白，但别写成古文” | `preset: old_school_civilist` 或 `archaism: 2-3` |
| “像当代判决书” | `preset: judicial_formal` |
| “像民国判牍” | `preset: republican_judgment` |
| “像历代刑法考／考据按断” | `historical_register: traditional_law`，主资源 `13_lexicon_traditional_appellate.md` |
| “浪漫一点／有文采／多用成语／像法学著作序言” | 主资源 `15_legal_preface_rhetoric.md`；普通转换中仅低剂量辅助 |
| “强度5，但两句内” | 高强度与 `length_limit: 2句` 同时生效 |

---

<!-- chunk: r01.h009 -->
## 三、默认值与模式派生

```yaml
task_mode: rewrite
preset: general_blacktalk
intensity: 3
output_length: standard
length_limit: auto
expansion_budget: 0
syntactic_complexity: 3
terminology_density: 3
archaism: 0
foreign_terms: 0
humor_absurdity: 1
argumentative_overkill: 2
historical_register: contemporary
authority_policy: none
text_scope: auto
coherence_mode: local
format_preservation: strict
```

模式权限具有硬上限：

| 模式 | `expansion_budget` | 教义展开上限 | 结论权限 |
|---|---:|---:|---|
| `rewrite` | 强制 0 | 仅同义替换与既有结构显化 | 不得新增或强化 |
| `expand` | 默认 1，最高 3 | 可加概念框架、区分与制度功能 | 不得新增或强化 |
| `analyze` | 默认 2，可按需 | 可作完整分析 | 有依据时允许 |

若参数与模式冲突，以模式权限为准。例如：

- `rewrite + expansion_budget 3` → 自动降为 0；
- `expand + “直接判断违法”` → 该请求实质进入 `analyze`；
- `analyze + authority_policy none` → 可作一般原理或条件分析，不得虚构具体权威。

---

<!-- chunk: r01.h010 -->
## 四、篇幅预算

<!-- chunk: r01.h011 -->
### 1. 命名档位

| 档位 | 短输入的默认形态 | 扩写层数上限 |
|---|---|---:|
| `minimal` 极短 | 1个高密度句 | 0—1 |
| `short` 简短 | 1—2句，通常不分段 | 1 |
| `standard` 适中 | 1段，通常2—4句 | 2 |
| `long` 详细 | 2—3段 | 3 |
| `extended` 充分 | 多段展开，仅在用户明确要求时使用 | 4 |

对段落或全文，档位按原有结构相对控制，不得为了命中字数而删除原命题。

<!-- chunk: r01.h012 -->
### 2. 明确上限优先

优先级：

```text
用户明确字数／句数／段数／倍率
> output_length
> 预设或默认偏好
```

为满足上限，按以下顺序压缩：

1. 删除额外理论框架；
2. 减少同义递进与定义递归；
3. 合并限定语和句子；
4. 保留源命题、情态与结论；
5. 不得通过删掉事实或偷换情态来“达标”。

<!-- chunk: r01.h013 -->
### 3. `expand` 的双预算

`output_length` 决定可见文字量；`expansion_budget` 决定新增概念量。

| `expansion_budget` | 允许的新增内容 |
|---:|---|
| 0 | 不新增；等同 rewrite 的概念权限 |
| 1 | 至多一个上位框架、概念区分或制度功能；通常不超过一句 |
| 2 | 至多两至三个彼此相关的框架；通常不超过一段 |
| 3 | 多角度展开，可含框架、区分与功能，但默认不超过两段；更长需用户明确要求 |

新增框架不得复制成多轮同义改写以绕过预算。

---

<!-- chunk: r01.h014 -->
## 五、强度档位

| 档位 | 行为 |
|---:|---|
| 1 | 轻度法律书面语，短句为主 |
| 2 | 明显名词化与主体功能化 |
| 3 | 标准黑话，适度长句、关系重构与体系定位 |
| 4 | 高密度术语、多层限定和较强抽象化 |
| 5 | 极端不说人话，但仍可回译、不得虚构或失控增篇 |

`intensity` 不自动改变篇幅、模式或理论增量。

---

<!-- chunk: r01.h015 -->
## 六、七种预设

预设不设置 `task_mode`、`output_length` 或 `expansion_budget`；它们只提供语体与资源偏好。

<!-- chunk: r01.h016 -->
### `general_blacktalk`｜现代通用黑话

```yaml
syntactic_complexity: 3
terminology_density: 3
archaism: 0
foreign_terms: 0
humor_absurdity: 1
argumentative_overkill: 2
primary_resources: [general_lexicon, general_templates]
secondary_resources: [modern_doctrinal]
```

<!-- chunk: r01.h017 -->
### `doctrinal_dense`｜高浓度现代教义学

```yaml
syntactic_complexity: 4
terminology_density: 5
archaism: 0
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 3
primary_resources: [modern_doctrinal, domain_lexicon]
secondary_resources: [general_lexicon]
```

在 `rewrite` 中只使用与原意等值的教义术语；三阶层、请求权基础、学说争议仍须由模式权限开放。

<!-- chunk: r01.h018 -->
### `old_school_civilist`｜老派民法学术腔

```yaml
syntactic_complexity: 4
terminology_density: 4
archaism: 3
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 3
primary_resources: [old_school_civilist, civil_lexicon]
secondary_resources: [general_lexicon]
avoid_registers: [republican_institutions, historical_procedure]
```

<!-- chunk: r01.h019 -->
### `judicial_formal`｜当代中性裁判文书腔

```yaml
syntactic_complexity: 3
terminology_density: 3
archaism: 0
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 2
primary_resources: [judicial_formal, general_lexicon]
secondary_resources: [domain_lexicon]
avoid_registers: [republican_institutions, archaic_officialese]
```

“像判决书”默认路由到本预设，不路由到民国判牍。

<!-- chunk: r01.h020 -->
### `classical_legalese`｜古典法言

```yaml
syntactic_complexity: 4
terminology_density: 3
archaism: 5
foreign_terms: 0
humor_absurdity: 1
argumentative_overkill: 3
primary_resources: [classical_contemporary_compatible]
secondary_resources: [general_lexicon, traditional_appellate]
avoid_registers: [period_bound_institutions]
```

`traditional_appellate`（历代刑法考式按断资源）仅在用户要求考据、辨名、沿革维度，或 `historical_register=traditional_law` 时开放；默认当代语境下只调用其可迁移句法。

<!-- chunk: r01.h021 -->
### `republican_judgment`｜民国判牍

```yaml
syntactic_complexity: 4
terminology_density: 3
archaism: 4
foreign_terms: 0
humor_absurdity: 0
argumentative_overkill: 3
historical_register: republican
primary_resources: [judicial_archival, classical_contemporary_compatible]
secondary_resources: [domain_lexicon]
```

仅在用户明确说“民国判牍／旧式判词”或输入本身处于该时代时使用。

<!-- chunk: r01.h022 -->
### `absurd_overkill`｜真实理论过度使用式搞怪

```yaml
syntactic_complexity: 5
terminology_density: 5
archaism: 1
foreign_terms: 0
humor_absurdity: 5
argumentative_overkill: 5
primary_resources: [general_lexicon, modern_doctrinal, absurd_templates]
secondary_resources: [domain_lexicon]
authority_policy: none
```

本预设默认仍遵守用户当前篇幅；它不会自动切换为 `long` 或 `extended`。

---

<!-- chunk: r01.h023 -->
## 七、冲突处理

| 冲突 | 处理 |
|---|---|
| 高强度＋短篇幅 | 用一至两个高密度句，不降低术语密度 |
| 高过度论证＋明确字数上限 | 先削减递归层数，绝不突破上限制造车轱辘话 |
| `expand`＋短篇幅 | 保留一个最相关框架，其余删除 |
| 高术语密度＋rewrite | 只用等值术语，不补理论要件 |
| 搞怪＋rewrite | 以比例失衡和同义复杂化制造笑点，不补事实或理论 |
| 搞怪＋expand | 理论新增仍受 `expansion_budget` 限制 |
| 古典法言＋当代语境 | 只改变词面与句法，不加入古代制度 |
| 当代判决书＋民国词汇 | 删除民国词汇，使用 `judicial_formal` |
| 明确字数上限＋长原文 | 优先保真；若无法同时满足，最低限度超出而不删命题 |
| 用户同时说“只改写”与“补充理论” | 后者实质为 expand；以更具体、更新的指令为准 |

---

<!-- chunk: r01.h024 -->
## 八、权威与历史参数

```yaml
authority_policy:
  none            # 默认，不出现具体法条、判例、学者、引文或“通说”
  provided_only   # 仅使用用户提供的权威信息
  verified        # 仅使用实际核验过的信息
```

`historical_register=source_bound` 表示：只保留来源文本已有的时代词，不自行补充同类历史事实。

---

<!-- chunk: r01.h025 -->
## 九、资源路由细则

路由是声明式权限边界。先按输入的领域、语体请求与历史语境确定允许的资源，再由 `scripts/retrieve.py` 在允许范围内排序并组成小素材包。排序分值只决定优先召回顺序，不得把禁用资源变为可用资源，也不得覆盖模式、历史、主体端、情态方向或评价来源门控。

<!-- chunk: r01.h026 -->
### 1. 按领域

| 输入领域 | 主资源 | 辅助资源 |
|---|---|---|
| 刑法 | `06_lexicon_criminal_law.md` | `08_style_modern_doctrinal.md`、`05_lexicon_general.md` |
| 民法、物权、债 | `07_lexicon_civil_property_obligations.md` | `09_style_old_school_civilist.md`（按预设决定）、`05` |
| 商、劳动、行政、知产、程序 | `07` 相应小节＋`05` | `08` |
| 法理、法史 | `05` 体系升格词 | `15_legal_preface_rhetoric.md`（价值表达）、`13`（法史） |

<!-- chunk: r01.h027 -->
### 2. 按语体请求

| 请求 | 主资源 | 辅助资源 | 禁用资源 |
|---|---|---|---|
| 老派民法学者腔 | `09_style_old_school_civilist.md` | `07` 第九节 | 民国判牍程序词 |
| 当代司法正式文风 | `10_style_classical_and_judicial.md` 第二节＋`16_lexicon_judicial_register_official.md`（全量词表）＋`14` 第六节（门控摘要） | `05` 判断梯度 | 清末民国判牍主资源 |
| 古典法言（当代语境） | `10` 第一节 | `05` 文言连接词 | 古代制度事实 |
| 历代刑法考式按断 | `13_lexicon_traditional_appellate.md` | `10` 第一节 | 现代刑法理论作主资源（仅可用于保持概念可理解性） |
| 民国判牍、判旨、解释例 | `14_lexicon_judicial_archival.md` | `10` 第六、七节 | 当代裁判语体词冒充民国词 |
| 序言式、浪漫、有文采 | `15_legal_preface_rhetoric.md` | `08` 方法论转场、`05` 四字格 | 裁判语体 |

<!-- chunk: r01.h028 -->
### 3. 历史语境限制资源

- `13_lexicon_traditional_appellate.md`：仅在 `traditional_law`、`source_bound`、古代法制史料输入或用户明确要求时全量开放；否则仅调用可迁移句法（其第七节三类限制适用）。
- `14_lexicon_judicial_archival.md` 第四、五、七节（函复、判牍、民国程序词）：仅在 `republican_judgment`、`source_bound` 或来源已有相应时代要素时开放。
- `15_legal_preface_rhetoric.md` 第八节（清末民国序文语汇）：仅在历史性预设或用户明确要求时调用。
- 普通现代预设下，上述资源一律不得作为主资源；不得无根据加入旧式制度事实。

<!-- chunk: r01.h029 -->
### 4. 模式与资源的交叉门控

- `rewrite`：所有资源仅作等值替换；`15` 不得新增宏大价值命题，`13`/`14` 不得新增褒贬与裁判结论。
- `expand`：新增框架计入 `expansion_budget`；`15` 的价值张力、制度功能、人文关怀表达每类计一单位。
- `analyze`：`15` 仅用于段落衔接与结论收束，不得以价值修辞替代法律论证。
