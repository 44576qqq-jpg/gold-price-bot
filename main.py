import os
import time
import logging
from datetime import datetime, timezone, timedelta

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

FEISHU_WEBHOOK = os.getenv("FEISHU_WEBHOOK")
GOLD_API_URL = "https://api.gold-api.com/price/XAU"
BEIJING_TZ = timezone(timedelta(hours=8))


def get_gold_price():
    for attempt in range(1, 4):
        try:
            logging.info(f"第 {attempt} 次获取黄金价格")

            response = requests.get(GOLD_API_URL, timeout=10)
            response.raise_for_status()

            data = response.json()
            price = data.get("price")

            if price is None:
                raise ValueError(f"接口返回数据异常: {data}")

            return price

        except Exception as e:
            logging.error(f"获取失败，第 {attempt} 次: {e}")
            if attempt < 3:
                time.sleep(5)

    raise RuntimeError("连续3次获取黄金价格失败")


def send_to_feishu(price):
    if not FEISHU_WEBHOOK:
        raise RuntimeError("未配置 FEISHU_WEBHOOK")

    now = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "msg_type": "text",
        "content": {
            "text": f"""📈 黄金价格提醒

时间：{now} 北京时间

国际黄金 XAU/USD：
{price} USD/OZ
"""
        }
    }

    for attempt in range(1, 4):
        try:
            logging.info(f"第 {attempt} 次推送飞书")

            response = requests.post(
                FEISHU_WEBHOOK,
                json=payload,
                timeout=10
            )
            response.raise_for_status()

            logging.info("飞书推送成功")
            return

        except Exception as e:
            logging.error(f"推送失败，第 {attempt} 次: {e}")
            if attempt < 3:
                time.sleep(5)

    raise RuntimeError("连续3次飞书推送失败")


if __name__ == "__main__":
    logging.info("黄金价格推送任务开始")
    price = get_gold_price()
    send_to_feishu(price)
    logging.info("黄金价格推送任务完成")
