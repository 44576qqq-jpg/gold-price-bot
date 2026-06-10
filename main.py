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
BEIJING_TZ = timezone(timedelta(hours=8))

XAU_API = "https://api.gold-api.com/price/XAU"


def retry_request(url, headers=None):
    for i in range(1, 4):
        try:
            logging.info(f"请求第 {i} 次: {url}")
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            return r
        except Exception as e:
            logging.error(f"请求失败第 {i} 次: {e}")
            if i < 3:
                time.sleep(5)
    raise RuntimeError(f"连续3次请求失败: {url}")


def get_xau_usd():
    r = retry_request(XAU_API)
    data = r.json()
    price = data.get("price")
    if price is None:
        raise RuntimeError(f"国际金价接口返回异常: {data}")
    return float(price)


def usd_oz_to_cny_g(xau_usd):
    """
    计算人民币金价：
    美元/盎司 → 元/克
    1 金衡盎司 = 31.1034768 克

    汇率这里先用外部免费接口。
    """
    url = "https://open.er-api.com/v6/latest/USD"
    r = retry_request(url)
    data = r.json()

    cny_rate = data["rates"]["CNY"]

    return xau_usd * cny_rate / 31.1034768


def get_bank_gold_prices(cny_gold):
    """
    银行实物金条价格没有统一免费稳定API。
    这里先用“人民币金价 + 银行溢价”的方式估算。
    后续如果你有稳定数据源，可以替换这里。
    """

    return {
        "浦发": round(cny_gold + 19.0, 2),
        "邮储": round(cny_gold + 12.3, 2),
        "农行": round(cny_gold + 10.0, 2),
        "工行": round(cny_gold + 21.08, 2),
        "中行": round(cny_gold + 17.26, 2),
        "招行": round(cny_gold + 43.06, 2),
        "建行": round(cny_gold + 16.13, 2),
    }


def send_feishu(message):
    if not FEISHU_WEBHOOK:
        raise RuntimeError("未配置 FEISHU_WEBHOOK")

    payload = {
        "msg_type": "text",
        "content": {
            "text": message
        }
    }

    for i in range(1, 4):
        try:
            logging.info(f"飞书推送第 {i} 次")
            r = requests.post(FEISHU_WEBHOOK, json=payload, timeout=15)
            r.raise_for_status()
            logging.info("飞书推送成功")
            return
        except Exception as e:
            logging.error(f"飞书推送失败第 {i} 次: {e}")
            if i < 3:
                time.sleep(5)

    raise RuntimeError("飞书连续3次推送失败")


def main():
    now = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M")

    xau_usd = get_xau_usd()
    cny_gold = usd_oz_to_cny_g(xau_usd)
    banks = get_bank_gold_prices(cny_gold)

    message = f"""黄金价格播报 {now}
国际现货金: {xau_usd:.2f} 美元/盎司
人民币金价: {cny_gold:.2f} 元/克
银行实物金条:
浦发: {banks["浦发"]} 元/克
邮储: {banks["邮储"]} 元/克
农行: {banks["农行"]} 元/克
工行: {banks["工行"]} 元/克
中行: {banks["中行"]} 元/克
招行: {banks["招行"]} 元/克
建行: {banks["建行"]} 元/克"""

    logging.info(message)
    send_feishu(message)


if __name__ == "__main__":
    main()
