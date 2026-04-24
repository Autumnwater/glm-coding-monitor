#!/usr/bin/env python3
"""
GLM Coding Lite 套餐库存监控脚本
检测页面按钮状态变化并发送飞书通知
"""

import os
import sys
import json
import time
import random
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# 配置
CONFIG = {
    "url": "https://bigmodel.cn/glm-coding?utm_source=bigmodel&utm_medium=quick-start&utm_content=glm-coding-plan&utm_campaign=Platform_Ops&_channel_track_key=2BDsH00Y",
    "product_name": "GLM Coding Lite 套餐",
    "price": "¥39.2/月（年度 ¥470.4）",
    "check_interval": 120,  # 检查间隔（秒）
}


def log(message):
    """打印带时间戳的日志"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def send_feishu_notification(webhook_url, title, status, price, url, is_available=False):
    """
    发送飞书卡片消息

    Args:
        webhook_url: 飞书群机器人 Webhook 地址
        title: 消息标题
        status: 库存状态
        price: 价格信息
        url: 购买链接
        is_available: 是否有货
    """
    template_color = "red" if is_available else "blue"
    status_emoji = "🔥" if is_available else "⏳"

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{status_emoji} {title}"
                },
                "template": template_color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**商品**: {CONFIG['product_name']}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**状态**: {status}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**价格**: {price}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "🚀 立即抢购"
                            },
                            "url": url,
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        log(f"飞书通知发送成功: {response.json()}")
        return True
    except Exception as e:
        log(f"飞书通知发送失败: {e}")
        return False


def check_stock():
    """
    检查 GLM Coding Lite 套餐库存状态

    Returns:
        dict: 包含库存状态信息的字典
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "is_available": False,
        "button_text": None,
        "error": None
    }

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu'
            ]
        )

        # 创建浏览器上下文，模拟真实用户
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
            timezone_id='Asia/Shanghai'
        )

        # 添加随机延迟，模拟真实用户行为
        time.sleep(random.uniform(1, 3))

        page = context.new_page()

        try:
            log(f"正在访问页面: {CONFIG['url']}")

            # 访问页面
            page.goto(CONFIG['url'], wait_until='networkidle', timeout=30000)

            # 等待页面加载完成
            page.wait_for_load_state('domcontentloaded')

            # 额外等待动态内容加载
            time.sleep(random.uniform(2, 4))

            log("页面加载完成，开始检测库存状态...")

            # 截图用于调试（仅在本地运行时保存）
            if os.getenv('SAVE_SCREENSHOT'):
                page.screenshot(path='screenshot.png', full_page=True)
                log("已保存调试截图: screenshot.png")

            # 策略1: 通过 Lite 文本定位，然后查找相邻的按钮
            try:
                # 先找到包含 "Lite" 的元素
                lite_locator = page.locator('text=Lite').first
                if lite_locator.count() > 0:
                    log("找到 Lite 套餐区域")

                    # 等待一下确保按钮已渲染
                    page.wait_for_timeout(1000)

                    # 在 Lite 区域内查找按钮 - 尝试多种选择器
                    button_selectors = [
                        'button',  # 普通按钮
                        '[role="button"]',  # ARIA按钮
                        'a[class*="btn"]',  # 链接按钮
                        '.ant-btn',  # Ant Design按钮
                        '[class*="button"]',  # 包含button类名
                    ]

                    button_text = None
                    for selector in button_selectors:
                        try:
                            # 获取 Lite 卡片的父容器
                            lite_card = lite_locator.locator('xpath=ancestor::div[contains(@class, "card") or contains(@class, "Card") or position()=1]').first
                            if lite_card.count() == 0:
                                lite_card = lite_locator.locator('xpath=..').locator('xpath=..').locator('xpath=..')

                            button = lite_card.locator(selector).first
                            if button.count() > 0:
                                # 等待按钮可见
                                button.wait_for(state='visible', timeout=5000)
                                button_text = button.text_content().strip()
                                if button_text:  # 确保文本不为空
                                    log(f"使用选择器 '{selector}' 找到按钮: {button_text}")
                                    break
                        except Exception as e:
                            continue

                    if button_text:
                        result['button_text'] = button_text

                        # 判断是否售罄 - 检查多种关键词
                        sold_out_keywords = ['售罄', '暂时', '缺货', '售完', '无货', '补货']
                        if any(keyword in button_text for keyword in sold_out_keywords):
                            result['is_available'] = False
                            result['status'] = f"暂时售罄 ({button_text})"
                        else:
                            result['is_available'] = True
                            result['status'] = f"有货 ({button_text})"
                    else:
                        log("未获取到按钮文本，尝试策略2")
                        raise Exception("按钮文本为空")
                else:
                    result['error'] = "未找到 Lite 套餐区域"

            except Exception as e:
                log(f"策略1检测失败: {e}")

                # 策略2: 通过页面文本全局搜索
                try:
                    page_content = page.content()
                    if '暂时售罄' in page_content:
                        result['is_available'] = False
                        result['status'] = "暂时售罄"
                        log("通过页面内容检测到: 暂时售罄")
                    elif '立即购买' in page_content or '立即订阅' in page_content:
                        result['is_available'] = True
                        result['status'] = "有货"
                        log("通过页面内容检测到: 有货")
                    else:
                        result['error'] = "无法确定库存状态"
                except Exception as e2:
                    result['error'] = f"策略2也失败: {e2}"

        except PlaywrightTimeout:
            result['error'] = "页面加载超时"
            log("页面加载超时")
        except Exception as e:
            result['error'] = str(e)
            log(f"检测过程出错: {e}")
        finally:
            browser.close()

    return result


def main():
    """主函数"""
    log("=" * 50)
    log("GLM Coding Lite 套餐库存监控启动")
    log("=" * 50)

    # 获取飞书 Webhook
    feishu_webhook = os.getenv('FEISHU_WEBHOOK')
    if not feishu_webhook:
        log("警告: 未设置 FEISHU_WEBHOOK 环境变量，将只打印日志不发送通知")

    # 执行库存检查
    result = check_stock()

    log(f"检测结果: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 如果有货或发生错误，发送通知
    should_notify = result.get('is_available', False) or result.get('error')

    if should_notify and feishu_webhook:
        title = "库存提醒" if result.get('is_available') else "监控异常"
        status = result.get('status', result.get('error', '未知状态'))

        send_feishu_notification(
            webhook_url=feishu_webhook,
            title=title,
            status=status,
            price=CONFIG['price'],
            url=CONFIG['url'],
            is_available=result.get('is_available', False)
        )

    # 设置 GitHub Actions 输出
    if os.getenv('GITHUB_ACTIONS'):
        with open(os.environ.get('GITHUB_OUTPUT', '/dev/null'), 'a') as f:
            f.write(f"is_available={str(result.get('is_available', False)).lower()}\n")
            f.write(f"status={result.get('status', 'unknown')}\n")

    log("监控完成")

    # 如果有货，返回成功退出码，否则返回特殊码
    return 0 if result.get('is_available') else 1


if __name__ == '__main__':
    sys.exit(main())
