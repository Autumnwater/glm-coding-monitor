# GLM Coding Lite 套餐库存监控

监控智谱 AI BigModel GLM Coding Lite 套餐的库存状态，当商品可购买时发送飞书通知。

## 功能特点

- 🔍 **智能检测**：自动检测页面库存状态变化
- 📱 **飞书通知**：库存可购买时立即推送消息
- ⏰ **定时监控**：每天 9:50-10:30 高峰期每 2 分钟检查一次
- 🆓 **免费托管**：使用 GitHub Actions，零成本运行
- 🖼️ **调试支持**：失败时自动保存页面截图

## 快速开始

### 1. 配置飞书机器人

1. 打开飞书群聊 → 设置 → 群机器人 → 添加机器人
2. 选择「自定义机器人」
3. 复制 Webhook 地址（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx`）

### 2. 部署到 GitHub

#### 方式一：Fork 本仓库
1. 点击右上角 Fork 按钮，将仓库复制到你的账号下
2. 进入 Settings → Secrets and variables → Actions
3. 点击 "New repository secret"
4. 名称：`FEISHU_WEBHOOK`
5. 值：粘贴你的飞书 Webhook 地址
6. 点击 "Add secret"

#### 方式二：手动创建仓库
1. 创建新的 GitHub 仓库
2. 上传以下文件：
   - `monitor.py`
   - `requirements.txt`
   - `.github/workflows/monitor.yml`
3. 配置 Secrets（同上）

### 3. 验证运行

1. 进入 Actions 页面
2. 找到 "GLM Coding 库存监控" 工作流
3. 点击 "Run workflow" 手动触发测试
4. 检查飞书是否收到测试通知

## 本地测试

```bash
# 克隆仓库
git clone <your-repo-url>
cd stock-monitor

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 设置环境变量
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxx"
export SAVE_SCREENSHOT=1  # 可选：保存调试截图

# 运行监控
python monitor.py
```

## 监控策略

| 时间段 | 检查频率 | 说明 |
|--------|----------|------|
| 09:50-10:30 | 每 2 分钟 | 抢购高峰期 |
| 其他时间 | 每 10 分钟 | 常规监控 |
| 手动触发 | 即时 | 随时测试 |

## 通知示例

**有货通知**：
```
🔥 库存提醒

商品: GLM Coding Lite 套餐
状态: 有货 (立即购买)
价格: ¥39.2/月（年度 ¥470.4）
时间: 2024-04-25 10:00:05

[🚀 立即抢购]
```

**售罄通知**：
```
⏳ 库存提醒

商品: GLM Coding Lite 套餐
状态: 暂时售罄 (04月26日 10:00 补货)
价格: ¥39.2/月（年度 ¥470.4）
时间: 2024-04-25 10:05:12

[🚀 立即抢购]
```

## 自定义配置

编辑 `monitor.py` 中的 `CONFIG` 字典：

```python
CONFIG = {
    "url": "https://bigmodel.cn/glm-coding?...",  # 监控页面
    "product_name": "GLM Coding Lite 套餐",       # 商品名称
    "price": "¥39.2/月（年度 ¥470.4）",          # 价格信息
    "check_interval": 120,  # 检查间隔（秒）
}
```

## 调整监控时间

编辑 `.github/workflows/monitor.yml` 中的 `schedule`：

```yaml
# 北京时间 9:50-10:30（UTC 1:50-2:30）
cron: '*/2 1-2 * * *'

# 其他时间每 10 分钟
cron: '*/10 2-23,0-1 * * *'
```

## 常见问题

### Q: 飞书通知没收到？
A: 检查以下步骤：
1. 确认 `FEISHU_WEBHOOK` Secrets 已正确设置
2. 检查飞书机器人是否在群中
3. 查看 GitHub Actions 日志确认执行成功

### Q: 页面抓取失败？
A: 可能原因：
1. 页面结构变化 → 需要更新选择器
2. 网络问题 → 已添加重试逻辑
3. 反爬拦截 → 已模拟真实浏览器

### Q: 如何监控多个商品？
A: 可以：
1. 复制多个 monitor 任务
2. 修改脚本支持多配置
3. 为每个商品创建独立仓库

### Q: GitHub Actions 免费额度？
A: 公共仓库无限免费，私有仓库每月 2000 分钟免费额度足够使用。

## 文件说明

```
stock-monitor/
├── monitor.py              # 核心监控脚本
├── requirements.txt        # Python 依赖
├── .github/
│   └── workflows/
│       └── monitor.yml     # GitHub Actions 配置
└── README.md              # 使用说明
```

## 技术栈

- **Python 3.10**：核心语言
- **Playwright**：浏览器自动化
- **Requests**：HTTP 请求
- **GitHub Actions**：定时任务托管

## 免责声明

本工具仅供个人学习和使用，请勿用于商业竞争或恶意抢购。使用本工具请遵守相关网站的服务条款。

## License

MIT License
