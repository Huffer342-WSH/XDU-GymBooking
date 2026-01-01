# %%
import requests
import json
import time
import re
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from requests.adapters import HTTPAdapter
from config import load_config


def fill_pattern(pattern, x):
    """
    用整数 x 替换模式字符串中的 '###'，不足位数自动补 0。

    参数:
        pattern (str): 包含 '#' 的模式字符串，例如 'GYMQ###'
        x (int): 需要填充的整数

    返回:
        str: 替换后的字符串
    """
    match = re.search(r"(#+)", pattern)
    if not match:
        return pattern
    placeholder = match.group(1)
    length = len(placeholder)
    number_str = str(x).zfill(length)
    result = pattern.replace(placeholder, number_str, 1)
    return result


# %%
def booking_prepare_cell(config, venue_no, field_info_list, date_offset):
    """
    返回一个字典：{'url': url, 'headers': headers, 'params': params}
    """
    # 0. 兼容性处理
    if isinstance(field_info_list, dict):
        field_info_list = [field_info_list]

    if not field_info_list:
        return None

    order_data = []
    for field in field_info_list:
        order_item = {
            "FieldNo": field["FieldNo"],
            "FieldTypeNo": field["FieldTypeNo"],
            "FieldName": field["FieldName"],
            "BeginTime": field["BeginTime"],
            "Endtime": field["EndTime"],
            "Price": field["FinalPrice"],
        }
        order_data.append(order_item)

    url = config["OrderFieldFree"]

    headers = config["request_headers"].copy()
    headers["Referer"] = "https://gyytygyy.xidian.edu.cn/Views/Field/FieldOrder.html"
    headers["X-Requested-With"] = "XMLHttpRequest"

    checkdata_json = json.dumps(order_data)
    params = {"checkdata": checkdata_json, "dateadd": date_offset, "VenueNo": venue_no}

    print(f"[*] 数据包已装填完毕，包含 {len(field_info_list)} 个场地")

    return {
        "url": url,
        "headers": headers,
        "params": params,
        "desc": f"{len(field_info_list)}个场地",  # 用于日志
    }


def booking_prepare(config, type, number, day, begin_time, end_time):
    """
    动态生成预定数据包

    参数:
        config: 加载的 yaml 配置对象
        type: 场地类型名称，必须与 config.yaml 中的 key 一致 (例如 "羽毛球", "健身房")
        number: 场地编号数字 (例如 1, 5, 12)
        day: 日期偏移 (0=今天, 1=明天)
        begin_time: 开始时间 (例如 "15:00")
        end_time: 结束时间 (例如 "17:00")
    """
    type_info = config["field_types"].get(type)

    if not type_info:
        print(f"[!] 错误: 配置文件中找不到场地类型 '{type}'")
        return None

    venue_no = type_info["VenueNo"]
    field_no = fill_pattern(type_info.get("FieldNo", ""), number)
    field_name = fill_pattern(type_info.get("FieldName", ""), number)

    target_item = {
        "FieldNo": field_no,  # 动态生成的编号，如 GYMQ001
        "FieldTypeNo": type_info["FieldTypeNo"],  # 从配置读取，如 021
        "FieldName": field_name,  # 动态生成的名字，如 羽毛球馆1号
        "BeginTime": begin_time,
        "EndTime": end_time,
        "FinalPrice": "0.00",  # 默认价格
    }

    print(f"[*] 正在构建请求: {type} | 场地:{field_no} | 时间:{begin_time}-{end_time}")

    return booking_prepare_cell(config, venue_no, [target_item], str(day))

    # %%


# 全局停止信号，一旦有一个线程抢到了，其他线程就停止，防止多抢或封号
stop_event = threading.Event()


def _worker_task(session, packet, thread_id, loop_times, interval):
    """
    单个线程的工作逻辑：循环发送 loop_times 次请求
    """
    url = packet["url"]
    params = packet["params"]

    for i in range(loop_times):
        # 1. 检查是否已经有别的线程成功了
        if stop_event.is_set():
            return False

        try:
            start_t = time.time()
            # 发送请求
            resp = session.get(url, params=params, timeout=2.5)
            cost_t = (time.time() - start_t) * 1000

            try:
                res_json = resp.json()
                print(
                    f"⚠️ [线程{thread_id}-第{i + 1}次] 返回结果: {res_json.get('message')}"
                )

                # --- 判断成功逻辑 ---
                if res_json.get("type") == 1:
                    print(
                        f"✅ [线程{thread_id}-第{i + 1}次] 抢票成功！(耗时{cost_t:.1f}ms) 结果: {res_json.get('message')}"
                    )
                    # 设置全局停止信号
                    stop_event.set()
                    return True
                else:
                    # 失败打印 (仅打印关键错误，避免日志爆炸)
                    # 如果返回 "当前时间不可预定"，说明还没到点，继续循环
                    msg = res_json.get("message", "")
                    print(
                        f"❌ [线程{thread_id}-第{i + 1}次] 失败: {msg} ({cost_t:.0f}ms)"
                    )

            except Exception:
                print(f"⚠️ [线程{thread_id}-第{i + 1}次] 解析异常")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ [线程{thread_id}-第{i + 1}次] 网络错误: {e}")

        # 2. 循环间隔
        if interval > 0:
            time.sleep(interval)

    return False


def booking_request(packet, m_concurrent=1, n_loop=1, t_interval=0.1):
    """
    参数:
        packet: 预组装的数据包
        m_concurrent: 并发线程数 (同时有多少个请求在跑)
        n_loop: 每个线程循环次数 (持久战次数)
        t_interval: 每次请求间隔 (秒)
    """
    if not packet:
        return False

    # 重置停止信号
    stop_event.clear()

    print(f"   - 并发线程数 (m): {m_concurrent}")
    print(f"   - 单线程循环 (n): {n_loop}")
    print(f"   - 单次间隔   (t): {t_interval}s")
    print(f"   - 预计总请求数  : {m_concurrent * n_loop} 次")

    # 1. 配置 Session 连接池 (关键!)
    # 必须保证连接池大小 >= 并发数，否则会发生阻塞
    headers = packet["headers"]
    session = requests.Session()
    session.headers.update(headers)

    adapter = HTTPAdapter(
        pool_connections=m_concurrent,  # 池连接数
        pool_maxsize=m_concurrent,  # 最大连接数
        max_retries=0,  # 关闭自动重试，我们要自己控制重试
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 2. 启动多线程
    futures = []
    with ThreadPoolExecutor(max_workers=m_concurrent) as executor:
        for i in range(m_concurrent):
            # 提交任务
            f = executor.submit(
                _worker_task, session, packet, i + 1, n_loop, t_interval
            )
            futures.append(f)

        # 3. 等待所有任务结束 (或者直到有人抢到)
        # 这里的 wait 会阻塞主线程，直到所有线程跑完或者 stop_event 被触发后线程陆续退出
        wait(futures)

    # 4. 总结
    if stop_event.is_set():
        print("\n🎉 恭喜！检测到抢票成功信号。")
        return True
    else:
        print("\n💨 所有请求已发送，似乎未抢到。")
        return False


# %%
# === 如何在 main.py 中使用 ===
if __name__ == "__main__":
    cfg = load_config()

    # 预组装数据包
    ready_packet = booking_prepare(
        config=cfg,
        type="羽毛球",
        number=1,
        day="2",  # 今天0/明天1/后天2
        begin_time="15:00",
        end_time="17:00",
    )

    booking_request(ready_packet)
