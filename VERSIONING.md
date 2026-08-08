# VERSIONING.md — SciForge-OSS 大一统版本策略

> **Status (v1.1.2)**: 单一版本号策略 — 开发、release、marketplace、README、CHANGELOG、plugin manifest **全部使用同一个版本号**。不再有"内容版本 vs 发布版本 vs 框架版本"的多套编号混乱。

---

## 1. 核心原则：一个版本号，全链路统一

SciForge-OSS **只有一个版本号**：**`1.1.2`**（当前正式版）。

| 位置 | 使用 | 必须与当前版本一致 |
|------|------|---------------------|
| 根 `./SKILL.md` frontmatter `version:` | atomcode skill-package 发布版本 | ✅ `1.1.2` |
| `.atomcode-plugin/plugin.json` `"version"` | marketplace 插件版本 | ✅ `1.1.2` |
| 24 个子 skill `SKILL.md` frontmatter `version:` | 每个子 skill 的版本 | ✅ `1.1.2` |
| `README.md` 版本徽章 | 仓库主页展示 | ✅ `1.1.2` |
| `CHANGELOG.md` 最新条目 | 变更记录 | ✅ `1.1.2` |
| git release tag | 发行版 | ✅ `v1.1.2` |
| `.atomcode/` marketplace `git_commit` | 自动拉取锁定的 commit | 与 release tag 对应 |

**为什么这么做**：v3.2→v3.4 期间出现过 4 套编号并存（根 SKILL.md=1.2.0/1.3.0、plugin.json=3.4.0、experiment-execution=2.0.0、publishability-score=2.2.0、22 个子 skill 无 version）——读者无法判断哪个是"当前版本"。大一统后：**任何时候只有一个版本号**，任何入口读到的都是同一个。

---

## 2. 版本号规则（正式版 + 补丁）

### 2.1 当前版本：`1.1.2`（正式版）

`1.1.2` 是**当前正式版**（1.1.0 初始发布 → 1.1.1 定位收敛与绘图工具链 → 1.1.2 管线治理：verdicts 统一 / 工作区整洁 / 回环登记 / 公平评测 / 反 AIGC 活人感）。

### 2.2 补丁版本：`1.1.2.x`

**Bug 修复、文档修正、小幅优化**都记为 `1.1.2.x`（`x` = 递增的补丁序号，从 0 开始）：

| 场景 | 版本号 | 例子 |
|------|--------|------|
| 当前正式版 | `1.1.2` | 初始发布 + 绘图工具链 + 管线治理 |
| 第一个 bug 修复 | `1.1.2.1` | 修复了 smoke gate 的路径引用 |
| 第二个 bug 修复 | `1.1.2.2` | 修复了 leakage scrub 漏检一类模式 |
| ... | `1.1.2.x` | 每次修复递增 x |

**补丁规则**：
- 每个修复/文档修正 = `1.1.2.x` 的 x 递增 1
- 补丁**不改变**主版本号 `1.1.2` 前缀——它们属于同一个正式版系列的维护
- 补丁必须写进 `CHANGELOG.md`（见 §4），并更新**所有** 26 个文件的 version 字段
- release tag：`v1.1.2`、`v1.1.2.1`、`v1.1.2.2`...

### 2.3 什么时候升主版本（未来）

只有**功能性重大变更**才升主版本（突破 `1.1.2` 前缀）：

| 变更类型 | 版本号动作 | 例子 |
|----------|-----------|------|
| Bug 修复 / 文档 / 小幅优化 | `1.1.2.x`（x+1） | 修 bug、改文档 |
| 新增子 skill / 新 phase / 行为改变 | `1.2.0` | 加一个"文献综述"子 skill |
| 破坏性变更 / 架构重写 | `2.0.0` | 重构 orchestrator 执行模型 |

---

## 3. 为什么选 `1.1.1` 而非 `0.1.0` 或 `1.0.0`

- **`1.x.x`**：正式版语义——pipeline 已能端到端产出论文（两个真实测试 run 完成，21 阶段全跑通）
- **`1.1.1`** 而非 `1.0.0`：`1.0.0` 是早期可用，`1.1.1` 表达"已带 v3.4 完整特性集的第一正式版"——human_skip、figure budget、leakage scrub、reproducibility statements 全部内置
- 与旧 release tag（`1.2.0`）不同：那是**错误的历史编号**（按内容版本写的），大一统后废弃

---

## 4. 每次变更的发布流程（Checklist）

每次发布一个补丁/新版本，**必须**执行：

1. **改代码/文档** — 修复或新增内容
2. **更新所有 26 个文件的 version 字段**：
   ```bash
   # 26 文件 = 根 SKILL.md + .atomcode-plugin/plugin.json + 24 子 skill
   sed -i 's/^version: .*/version: 1.1.2.x/' SKILL.md
   sed -i 's/"version": "[0-9.]*"/"version": "1.1.2.x"/' .atomcode-plugin/plugin.json
   # 24 子 skill 同理
   ```
3. **更新 `CHANGELOG.md`** — 在顶部加 `## [1.1.2.x] - YYYY-MM-DD`，写明修复内容
4. **更新 `README.md` 版本徽章**（如 `![version](https://img.shields.io/badge/version-1.1.2.x-blue)`）
5. **打 git tag**：`git tag v1.1.2.x`
6. **marketplace 同步**：发布后本地 `git pull` 拉取（.atomcode-plugin/plugin.json 的 version 已是新值）
7. **核验**：`grep -c "1.1.2" SKILL.md .atomcode-plugin/plugin.json skills/*/*/SKILL.md` 应覆盖全部 26 文件

---

## 5. 常见问题

### Q: 内容版本（v3.x 特性标识）和发布版本（1.1.2）冲突吗？
不冲突。`v3.x` 是**内容特性标识**（写在 description 里，描述"这个版本有哪些功能"），`1.1.2` 是**发布版本号**（所有 version 字段 + tag + marketplace 用）。**version 字段永远用 1.1.2.x；v3.x 只出现在 description/文档叙述里**。

### Q: 为什么子 skill 也要统一版本？
因为 atomcode 发布向导会扫描仓库所有 SKILL.md——如果子 skill 版本混乱，发布时显示不一致。统一后任何入口读到的一致。

### Q: 改了根 SKILL.md 的 version 但忘了改 plugin.json 会怎样？
marketplace 安装的插件版本和根发布版本不一致，读者困惑。**必须同步**（§4 checklist 第 2 步）。

---

## 6. 历史版本记录（废弃的编号体系）

以下编号**已废弃**，仅供追溯（不要再用）：

| 旧编号 | 含义 | 废弃原因 |
|--------|------|----------|
| `v2.3` / `v3.0` / `v3.2` / `v3.4` | 内容特性标识 | 保留在 description 里，不再作 version 字段 |
| `1.2.0`（根 SKILL.md 旧值） | 错误的历史发布号 | 与 plugin.json 3.4.0 冲突 |
| `2.0.0`（experiment-execution 旧值） | 子 skill 独立编号 | 与根不一致 |
| `2.2.0`（publishability-score 旧值） | 子 skill 独立编号 | 与根不一致 |
| `0.1.0`（PR #25 方案） | marketplace 首发草案 | 升级为正式版 1.1.0 |

**从现在起：只认 `1.1.2.x` 一个编号体系。**
