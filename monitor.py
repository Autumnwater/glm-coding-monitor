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
                # 先找到包含 "Lite" 的元素（通常是标题）
                lite_locator = page.locator('text=Lite').first
                if lite_locator.count() > 0:
                    log("找到 Lite 套餐区域")

                    # 等待一下确保按钮已渲染
                    page.wait_for_timeout(1000)

                    # 获取 Lite 卡片的父容器（向上查找包含卡片的祖先元素）
                    lite_card = lite_locator.locator('xpath=ancestor::div[contains(@class, "card") or contains(@class, "Card")]').first
                    if lite_card.count() == 0:
                        # 如果没找到特定class，向上查找3层
                        lite_card = lite_locator.locator('xpath=..').locator('xpath=..').locator('xpath=..').locator('xpath=..')

                    # 策略1a: 在 Lite 卡片内查找所有可能的按钮
                    all_buttons = lite_card.locator('button, [role="button"], a[class*="btn"], .ant-btn, [class*="button"]').all()
                    log(f"策略1a - 在Lite卡片内找到 {len(all_buttons)} 个按钮")

                    # 策略1b: 如果没找到足够按钮，扩大到Lite卡片附近区域（使用父级容器）
                    if len(all_buttons) < 2:
                        # 向上查找更多层级，获取更大的容器
                        parent_container = lite_locator.locator('xpath=ancestor::div[contains(@class, "section") or contains(@class, "Section") or contains(@class, "pricing") or contains(@class, "plan")]').first
                        if parent_container.count() == 0:
                            parent_container = lite_locator.locator('xpath=..').locator('xpath=..').locator('xpath=..').locator('xpath=..').locator('xpath=..').locator('xpath=..')

                        parent_buttons = parent_container.locator('button, [role="button"], a[class*="btn"], .ant-btn, [class*="button"], [class*="action"]').all()
                        log(f"策略1b - 在父容器内找到 {len(parent_buttons)} 个按钮")

                        # 合并按钮列表，去重
                        all_buttons = all_buttons + parent_buttons

                    # 策略1c: 如果还是没找到，搜索整个页面中与Lite相关的按钮
                    if len(all_buttons) < 2:
                        # 获取页面所有按钮
                        page_buttons = page.locator('button, [role="button"], a[class*="btn"], .ant-btn, [class*="button"]').all()
                        log(f"策略1c - 页面总共找到 {len(page_buttons)} 个按钮")

                        # 过滤出文本包含特定关键词的按钮
                        for btn in page_buttons:
                            try:
                                text = btn.text_content().strip()
                                # 如果按钮文本包含库存相关关键词，加入列表
                                if text and any(kw in text for kw in ['售罄', '售完', '缺货', '无货', '补货', '购买', '订阅', '抢购']):
                                    if btn not in all_buttons:
                                        all_buttons.append(btn)
                                        log(f"策略1c - 添加相关按钮: {text}")
                            except Exception:
                                continue

                    button_text = None
                    # 优先级1: 售罄状态关键词（最准确）
                    sold_out_keywords = ['售罄', '售完', '缺货', '无货', '暂时售罄']
                    # 优先级2: 补货信息
                    restock_keywords = ['补货']
                    # 优先级3: 可购买关键词（但要排除纯标签）
                    purchase_keywords = ['立即购买', '立即订阅', '立即抢购', '即刻订阅']
                    # 排除的标签（这些是折扣标签，不是按钮）
                    exclude_labels = ['特惠订阅', '优惠', '折扣', '立减']

                    # 去重：记录已处理的按钮文本
                    processed_texts = set()

                    # 第一遍：寻找售罄状态按钮（最高优先级）
                    log(f"开始扫描 {len(all_buttons)} 个按钮...")
                    for btn in all_buttons:
                        try:
                            text = btn.text_content().strip()
                            # 跳过已处理的相同文本
                            if text in processed_texts:
                                continue
                            processed_texts.add(text)

                            log(f"扫描到按钮文本: '{text}'")
                            # 排除折扣标签
                            if text and any(exclude in text for exclude in exclude_labels):
                                log(f"  -> 跳过折扣标签")
                                continue
                            # 优先匹配售罄关键词
                            if text and any(kw in text for kw in sold_out_keywords):
                                button_text = text
                                log(f"  -> 找到售罄状态按钮: {button_text}")
                                break
                        except Exception as e:
                            log(f"扫描按钮时出错: {e}")
                            continue

                    # 第二遍：寻找补货信息按钮
                    if not button_text:
                        for btn in all_buttons:
                            try:
                                text = btn.text_content().strip()
                                if text in processed_texts or (text and any(exclude in text for exclude in exclude_labels)):
                                    continue
                                if text and any(kw in text for kw in restock_keywords):
                                    button_text = text
                                    log(f"  -> 找到补货信息按钮: {button_text}")
                                    break
                            except Exception:
                                continue

                    # 第三遍：寻找可购买按钮
                    if not button_text:
                        for btn in all_buttons:
                            try:
                                text = btn.text_content().strip()
                                if text in processed_texts or (text and any(exclude in text for exclude in exclude_labels)):
                                    continue
                                if text and any(kw in text for kw in purchase_keywords):
                                    button_text = text
                                    log(f"  -> 找到可购买按钮: {button_text}")
                                    break
                            except Exception:
                                continue

                    # 如果没找到有效按钮，尝试第一个非空且非折扣标签的按钮作为后备
                    if not button_text and len(all_buttons) > 0:
                        for btn in all_buttons:
                            try:
                                text = btn.text_content().strip()
                                if text and len(text) > 1 and not any(exclude in text for exclude in exclude_labels):
                                    button_text = text
                                    log(f"  -> 使用后备按钮: {button_text}")
                                    break
                            except Exception:
                                continue

                    if button_text:
                        result['button_text'] = button_text

                        # 根据按钮识别的优先级判断状态
                        # 优先级1: 售罄状态（包括"暂时售罄"）
                        if any(kw in button_text for kw in sold_out_keywords):
                            result['is_available'] = False
                            result['status'] = f"暂时售罄 ({button_text})"
                            log(f"状态判断: 售罄 - 匹配关键词在 '{button_text}' 中")
                        # 优先级2: 补货信息也算售罄
                        elif any(kw in button_text for kw in restock_keywords):
                            result['is_available'] = False
                            result['status'] = f"暂时售罄 ({button_text})"
                            log(f"状态判断: 售罄(补货中) - 匹配关键词在 '{button_text}' 中")
                        # 优先级3: 可购买状态
                        elif any(kw in button_text for kw in purchase_keywords):
                            result['is_available'] = True
                            result['status'] = f"有货 ({button_text})"
                            log(f"状态判断: 有货 - 匹配关键词在 '{button_text}' 中")
                        # 其他情况: 未知，保守判断为售罄
                        else:
                            result['is_available'] = False
                            result['status'] = f"状态未知 ({button_text})"
                            log(f"状态判断: 未知 - 文本 '{button_text}' 未匹配任何关键词，保守判断为售罄")
                    else:
                        log("未获取到按钮文本，尝试策略2")
                        raise Exception("按钮文本为空")
                else:
                    result['error'] = "未找到 Lite 套餐区域"

            except Exception as e:
                log(f"策略1检测失败: {e}")

            # 策略2: 通过页面文本全局搜索（验证或备用）
            try:
                page_content = page.content()
                log("执行策略2: 全局页面内容检查...")

                # 检查是否包含售罄关键词
                if '暂时售罄' in page_content or '已售罄' in page_content:
                    # 如果策略1判断为有货，但页面显示售罄，以页面为准
                    if result.get('is_available') == True:
                        log(f"策略2覆盖: 策略1判断为有货，但页面内容显示售罄，修正为售罄")
                        result['is_available'] = False
                        result['status'] = f"暂时售罄 (页面文本检测)"
                    elif not result.get('button_text'):
                        # 策略1失败时的备用判断
                        result['is_available'] = False
                        result['status'] = "暂时售罄"
                        log("通过页面内容检测到: 暂时售罄")
                elif not result.get('button_text'):
                    # 策略1失败且页面没有售罄标记时
                    if '立即购买' in page_content or '立即订阅' in page_content or '即刻订阅' in page_content:
                        result['is_available'] = True
                        result['status'] = "有货"
                        log("通过页面内容检测到: 有货")
                    else:
                        result['error'] = "无法确定库存状态"
            except Exception as e2:
                if not result.get('button_text'):
                    result['error'] = f"策略2也失败: {e2}"
                log(f"策略2执行出错: {e2}")

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
