# 价格同步维护项目 (pricing-sync)

本项目为 **New API / bita-api** 提供一套轻量、可控、透明的模型价格同步数据源工程。

通过本地配置文件维护官方价格页与按次计费模型，每周通过本地脚本或 AI 工具一键提取并换算，产出符合 New API 原生标准的 `ratio_config.json`，并通过私有化 GitLab 供 New API 一键同步入库。

---

## 目录结构

```text
pricing-sync/
├── providers.json       # 官网价格页配置表（人维护：URL、货币、厂商）
├── overrides.json       # 本地自定义与按次计费模型（Midjourney、Flux、私有模型）
├── ratio_config.json    # 最终生成并对外发布的标准比率文件（供 New API 读取）
├── sync.py              # 价格提取、比率换算与文件生成核心脚本
├── requirements.txt     # Python 可选扩展依赖
├── .gitlab-ci.yml       # GitLab CI/CD 自动校验与 Pages 静态发布配置
└── .gitignore           # 忽略文件
```

---

## 核心配置与文件说明

### 1. `providers.json`（官网价格页清单）
记录你需要关注的主流模型厂商价格页 URL 及结算币种（USD / CNY）：
```json
[
  {
    "provider": "OpenAI",
    "url": "https://openai.com/api/pricing/",
    "currency": "USD"
  },
  {
    "provider": "DeepSeek",
    "url": "https://platform.deepseek.com/api-docs/pricing/",
    "currency": "CNY"
  }
]
```

### 2. `overrides.json`（本地自定义与按次计费模型）
**优先级最高**。凡是记录在此文件中的模型与价格，生成时会自动合并，并且永远不会被外部抓取冲掉：
* `model_price`：按次计费模型单次美元金额（如 Midjourney、DALL-E-3、Flux 等）
* `model_ratio`：私有模型或需手动强制指定的输入倍率
* `completion_ratio`：补全倍率
* `cache_ratio`：缓存读取倍率

### 3. `ratio_config.json`（New API 标准数据源）
执行脚本后自动生成的最终产物，结构符合 New API 渠道价格同步规范（包含 `model_ratio`、`completion_ratio`、`cache_ratio`、`model_price`）。

---

## 换算公式（与 New API 保持一致）

1. **汇率折算**：人民币价格按 `1 USD = 7.2 RMB` 折算为美元单价（可在 `sync.py` 或环境变量 `USD_CNY_RATE` 中调整）。
2. **输入倍率**：
   $$\text{model\_ratio} = \frac{\text{输入单价 (USD / 1M tokens)}}{2.0}$$
3. **输出补全倍率**：
   $$\text{completion\_ratio} = \frac{\text{输出单价}}{\text{输入单价}}$$
4. **缓存读取倍率**：
   $$\text{cache\_ratio} = \frac{\text{缓存读取单价}}{\text{输入单价}}$$

---

## 快速使用

### 方式一：命令行运行（推荐）
```bash
# 1. 核心厂商全量生成（默认模式，只包含配置的 8 家核心官方模型）
python3 sync.py

# 2. 单厂商专项测试模式（只生成某一家官网模型，极度干净，适合测试特定官网）
python3 sync.py --provider DeepSeek
python3 sync.py --provider OpenAI
python3 sync.py --provider Anthropic
python3 sync.py --provider Aliyun-Qwen
```
* 脚本将自动处理汇率、合并 `overrides.json`，生成 `ratio_config.json`；
* 并在终端输出 **【本周价格更新与核对简报】**，清晰列出哪些模型降价、涨价或新增。

### 方式二：本地 AI Agent 对话式更新
在 AI 编程助手（如 Antigravity / Cursor / Claude Code）中直接吩咐：
> “请帮我运行 `sync.py` 更新价格，并汇报本周有哪些价格变动。”

---

## 托管到私有化 GitLab

### 1. 首次推送到私有 GitLab
在公司的私有 GitLab 上新建一个项目（例如 `llm/pricing-sync`），然后在本地执行：
```bash
cd /Users/ganwangzha/leinao/token-factory/pricing-sync
git init
git add .
git commit -m "feat: initial pricing-sync project"
git branch -M main
git remote add origin http://gitlab.yourcompany.com/llm/pricing-sync.git
git push -u origin main
```

### 2. 每周更新后一键推送
```bash
python3 sync.py
git add ratio_config.json
git commit -m "chore: update pricing $(date +%F)"
git push
```

---

## 在 New API 中接入并同步

进入 New API 管理面板，按以下步骤配置：

### 步骤 1：添加同步渠道
1. 打开 **渠道** $\to$ **添加渠道**。
2. **类型**：随意（如 `自定义` 或 `OpenAI`）。
3. **名称**：`私有价格同步源 (GitLab)`。
4. **代理地址 (Base URL)**：填入 GitLab 域名，例如：
   ```text
   http://gitlab.yourcompany.com
   ```
5. **密钥 (Key)**：任意填写占位字符（如 `dummy`）。

### 步骤 2：配置 Endpoint 提取价格

#### 情形 A：GitLab 仓库是内部公开的（Internal / Public）
进入 **系统设置** $\to$ **运营设置**（或 **比率设置**） $\to$ 点击 **「同步倍率」**：
* 勾选 `私有价格同步源 (GitLab)` 渠道；
* Endpoint 选择 `custom`，输入 Raw 路径：
  ```text
  /<group>/<project>/-/raw/main/ratio_config.json
  ```
* 点击 **获取** 即可拉取并进行高亮比对！

#### 情形 B：GitLab 仓库是私有的（Private）
如果仓库受权限保护，在 GitLab 中生成一个只读 Project Access Token：
1. GitLab 项目 $\to$ **Settings** $\to$ **Access Tokens**。
2. 权限仅勾选 **`read_repository`**，生成 token（如 `glpat-xxxxxxxxxxxx`）。
3. 在 New API 同步倍率弹窗中，Endpoint 选择 `custom` 并带上 Token 参数：
   ```text
   /<group>/<project>/-/raw/main/ratio_config.json?private_token=glpat-xxxxxxxxxxxx
   ```
4. 点击 **获取**，New API 将安全拉取文件并展示对比差异。

#### 情形 C：开启了 GitLab Pages
如果使用了 GitLab Pages，直接将渠道 Base URL 设为 Pages 根地址，Endpoint 填 `/ratio_config.json` 即可。
