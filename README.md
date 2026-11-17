# BTC 底部信号看板（btc.seanzhao.ai 克隆）

单文件静态看板 + 每日自动构建。五信号底部评分（S1 持有者成本 / S2 MVRV / S3 未实现损失 / S4 资金流 / S5 恐慌指数）+ 历史触发回测。

线上：https://linqj1986.github.io/btc-dashboard/

## 本地运行

### 环境

- Windows / Python 3.12+（仅标准库，无需装依赖；测试用 pytest）
- 直连不通外网时自动降级代理 `http://127.0.0.1:7890`（可在环境变量 `HTTPS_PROXY` 覆盖）

```bash
cd btc

# 1) 安装测试工具（一次性）
python -m pip install pytest

# 2) 构建（默认拉最新数据；缓存 12 小时内直接复用）
python -X utf8 build.py

# 3) 本地预览（构建 + 起服务）
python -X utf8 build.py --serve          # 默认 8124 端口
python -X utf8 build.py --serve --port 8125
```

打开 http://localhost:8124/index.html（手机同 WiFi 访问 `http://本机IP:8124/index.html`）。

### 常用命令

| 命令 | 说明 |
|---|---|
| `python -X utf8 build.py` | 构建 `dist/index.html`（数据缓存 12h 内复用） |
| `python -X utf8 build.py --force` | 忽略缓存，强制重新拉全部数据 |
| `python -X utf8 build.py --offline` | 只用本地缓存构建，不联网（首次运行前需先成功构建过一次） |
| `python -X utf8 build.py --serve` | 构建 + 本地 HTTP 服务 |
| `python -m pytest -q` | 跑全部离线测试（含黄金回归） |
| `python -m pytest -m network` | 网络冒烟测试（真实拉各数据源，约 2 分钟） |

构建结束会打印一行摘要，含与原站评分序列的**偏差统计**（诚实口径，见下）。

## 目录结构

```
btc/
├── build.py            # 构建入口
├── lib/
│   ├── net.py          # HTTP: 缓存/代理降级/重试
│   ├── fetchers.py     # 数据源: CoinMetrics / alternative.me / DefiLlama / Binance
│   ├── signals.py      # S2/S4/S5 信号分量
│   ├── approx.py       # S1/S3 近似分量 + 全史合成
│   └── trig.py         # 触发段提取(黄金验证逐段一致)
├── template.html       # 页面模板(数字注入 + spark/指针 JS 运行时填充)
├── cycle_bots.json     # 历史周期底(人工维护)
├── cache/              # 数据缓存(git 忽略)
├── dist/index.html     # 构建产物
└── tests/              # 28 个测试, 含 TRIG/准确率矩阵双黄金锚
```

## 数据口径（与原站差异，诚实声明）

原站数据源为 Glassnode（付费）。本项目免费拼凑：

| 信号 | 数据/口径 | 说明 |
|---|---|---|
| S1 短期成本 | 120 日 SMA 近似 | 当日锚校准 +1.2% |
| S1 平均成本 | CoinMetrics MVRV/市值/供应反推 | 免费数据止于 2026-05-24，之后冻结成本+价格推算 MVRV |
| S1 长期成本 | 平均成本 × 0.906 | 当日单点锚，无历史真值 |
| S2 MVRV | 价格 ÷ 平均成本 | 同上冻结口径 |
| S3 RNL | 价格/短期成本代理式 | 近似 |
| S4 资金 | DefiLlama 稳定币总量 | 程度层+背离层(状态机) |
| S5 恐慌 | alternative.me | 与原站同源同值 |
| 价格 | Binance klines 全史 | 实时价 Binance 24h 行情 |

全史评分与原站序列偏差：中位 ~4.4 分、当日值全锚命中。页脚已标注。

## 财报/周期维护

- **周期底**：新熊市底确认后，往 `cycle_bots.json` 加一行 `{"date": "...", "price": ...}`
- GitHub Actions 每日 06:30（北京时间）自动重建；push 代码立即重建

## 免责

仅为个人研究的数据面板克隆，非投资建议。原作者：子琦 · X @Seanzhao1105（评分框架与页面设计版权归原作者）。
