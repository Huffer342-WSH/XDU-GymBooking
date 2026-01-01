import time
import datetime
from config import load_config
from booking import booking_prepare_cell, booking_request


# 1. 设置抢票日期偏移 (0=抢今天的, 1=抢明天的)
# 通常早上8点是抢明天的票，所以这里默认设为 "1"
DATE_OFFSET = 1

# 2. 设置开抢时间 (24小时制)
TARGET_HOUR = 8
TARGET_MINUTE = 0
TARGET_SECOND = 0

# 3. 设置目标场地列表 (必须准确！)
# 提示：FieldNo 是最关键的。建议提前用 info.py 跑一次看看你想抢的场地的 "FieldNo" 是什么。
# 例如：健身房通常 FieldTypeNo是023, FieldNo可能是 023001, 023002 等
TARGETS = [
    {
        "FieldNo": "GYMQ001",  # <---【关键】场地具体编号 (需提前知道)
        "FieldTypeNo": "021",  # 场地类型编号 (健身房023, 羽毛球021)
        "FieldName": "羽毛球馆1号",  # 名字 (随便填，不影响后端校验，方便自己看)
        "BeginTime": "15:00",  # 开始时间
        "EndTime": "17:00",  # 结束时间
        "FinalPrice": "0.00",  # 价格
    },
    {
        "FieldNo": "GYMQ002",  # <---【关键】场地具体编号 (需提前知道)
        "FieldTypeNo": "021",  # 场地类型编号 (健身房023, 羽毛球021)
        "FieldName": "羽毛球馆2号",  # 名字 (随便填，不影响后端校验，方便自己看)
        "BeginTime": "15:00",  # 开始时间
        "EndTime": "17:00",  # 结束时间
        "FinalPrice": "0.00",  # 价格
    },
]


def wait_until_target(target_time: datetime.datetime):
    """
    精准等待直到指定时间
    """
    now = datetime.datetime.now()

    # 如果当前时间已经过了今天的8点，说明是想测试或者第二天，这里简单处理为：如果过了就立即执行(用于测试)，或者你可以加逻辑判断
    if now > target_time:
        # 如果当前是 7:58，但目标是 8:00，进入下面逻辑。
        # 如果当前是 8:05，目标是 8:00，说明已经错过了，但为了防止死循环，这里选择不做处理直接返回，或者打印警告
        pass

    print(f"⏳ 正在等待目标时间: {target_time.strftime('%D %H:%M:%S.%f')} ...")

    while True:
        now = datetime.datetime.now()
        # 计算剩余秒数
        diff = (target_time - now).total_seconds()
        print(f"\r还剩 {diff}  秒...", end="")

        # 如果剩余时间大于 5秒，睡大觉
        if diff > 20:
            print(f"休眠 {int(diff - 20)} 秒")
            time.sleep(diff - 20)

        elif diff > 1:
            time.sleep(0.5)
        # 只要时间一到（差值小于等于0），立马跳出
        elif diff <= 0.05:
            break


def main():
    print("=== 🔥 西电体育馆暴力抢票脚本启动 🔥 ===")

    # 1. 加载配置
    cfg = load_config()
    if not cfg:
        return

    # 2. 【准备阶段】提前组装好数据包
    print(f"[*] 正在根据预设目标组装数据包 (共 {len(TARGETS)} 个场地)...")
    ready_packet = booking_prepare_cell(cfg, TARGETS, str(DATE_OFFSET))

    if not ready_packet:
        print("[!] 数据包组装失败，请检查配置。")
        return

    print("[*] 数据包准备就绪 (Ready to Fire)")

    # 3. 【等待阶段】
    # 比如你7:58启动，这里会卡住，直到8:00:00
    targettime = datetime.datetime.now().replace(
        hour=TARGET_HOUR, minute=TARGET_MINUTE, second=TARGET_SECOND, microsecond=0
    )
    targettime = targettime + datetime.timedelta(days=DATE_OFFSET)
    wait_until_target(targettime)

    # 4. 【发射阶段】
    # 循环发送请求，确保命中
    booking_request(ready_packet, 1, 10, 0)


if __name__ == "__main__":
    main()
