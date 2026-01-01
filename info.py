# %%
import requests
import json

from config import load_config


def get_info(config, target="羽毛球", day="明天", time="上午"):
    """
    根据配置文件的内容，请求场地数据
    """

    DICT_DAY = {"今天": "0", "明天": "1", "后天": "2"}
    DICT_TIME = {"上午": "0", "下午": "1", "晚上": "2"}

    # 1. 从 field_types 中查找对应的 VenueNo 和 FieldTypeNo
    type_info = config["field_types"].get(target)
    if not type_info:
        print(f"[!] 错误：在配置文件 field_types 中找不到 '{target}' 的定义")
        return None

    venue_no = type_info["VenueNo"]
    field_type_no = type_info["FieldTypeNo"]

    # 2. 设置时间参数 (由于你的config里删了这些，这里需要指定)
    # 建议后续加回 config.yaml，这里先手动指定：
    # dateadd: 0=今天, 1=明天
    # TimePeriod: 0=上午, 1=下午, 2=晚上
    try:
        current_date_add = DICT_DAY[day]  # <--- 想要查询哪天，改这里
        current_time_period = DICT_TIME[time]  # <--- 想要查询哪个时段，改这里
    except KeyError:
        print(f"[!] 错误：错误的时间参数：{day} {time}")
        return None

    headers = config["request_headers"]
    url = "https://gyytygyy.xidian.edu.cn/Field/GetVenueStateNew"

    params = {
        "VenueNo": venue_no,
        "FieldTypeNo": field_type_no,
        "dateadd": current_date_add,
        "TimePeriod": current_time_period,
    }

    print(
        f"--- 正在请求: {target} (Venue:{venue_no}, Type:{field_type_no}) | 偏移: {current_date_add} | 时段: {current_time_period} ---"
    )

    # 在 headers 中加入 Referer 和 X-Requested-With
    full_headers = headers.copy()
    full_headers["Referer"] = "https://gyytygyy.xidian.edu.cn/Views/Field/FieldOrder.html"
    full_headers["X-Requested-With"] = "XMLHttpRequest"

    try:
        response = requests.get(url, headers=full_headers, params=params)
        return response.text
    except Exception as e:
        print(f"[!] 请求失败: {e}")
        return None


# %%
def parse_info(json_text):
    """
    解析 JSON 并返回一个二维矩阵结构的字典
    结构: matrix[BeginTime][FieldName] = { ...原始数据... }
    """
    # 初始化一个空字典来模拟矩阵
    field_matrix = {}

    if not json_text:
        return {}

    try:
        # 1. 解析外层
        data = json.loads(json_text)

        # 检查基本错误
        if data.get("type") != 1:
            print(f"[!] API 返回错误: {data.get('message')}")
            return {}

        if not data.get("resultdata"):
            print("[-] resultdata 为空，可能该时段无场地信息")
            return {}

        # 2. 解析内层 resultdata (字符串转列表)
        raw_list = json.loads(data["resultdata"])

        # 3. 遍历列表，构建矩阵
        for item in raw_list:
            field_name = item.get("FieldName")
            begin_time = item.get("BeginTime")

            # 如果该时间点还没在矩阵里，先初始化一个空字典
            if begin_time not in field_matrix:
                field_matrix[begin_time] = {}

            # 将该时间段的【完整原始字典】存入矩阵
            field_matrix[begin_time][field_name] = item

    except json.JSONDecodeError:
        print("[!] JSON 解析失败")
    except Exception as e:
        print(f"[!] 解析异常: {e}")

    return field_matrix


def print_info(field_matrix):
    if not field_matrix:
        print("未获取到任何场地数据。")
    else:
        for time_k, fields_dict in sorted(field_matrix.items()):
            print(f"\n[ {time_k} ]")
            print("-" * 60)

            count = 0
            for field_name, info in fields_dict.items():
                t = info.get("TimeStatus")
                f = info.get("FieldState")

                if t == "1" and f == "0":
                    print(
                        f"{field_name}: {info.get('TimeStatus')} {info.get('FieldState')} {'空闲    '.ljust(6)}\t",
                        end=" ",
                    )

                else:
                    print(
                        f"{field_name}: {info.get('TimeStatus')} {info.get('FieldState')} {info.get('MembeName').ljust(6)}\t",
                        end=" ",
                    )
                count += 1
                if count % 3 == 0:  # 每3个换行
                    print()
            print()


# %%
if __name__ == "__main__":
    # 1. 加载配置
    config = load_config()

    if config:
        # 2. 获取原始数据
        raw_content = get_info(config, target="羽毛球", day="后天", time="下午")

        # 3. 解析并显示结果
        field_matrix = parse_info(raw_content)

        print("\n=== 查询结果概览 ===")
        print_info(field_matrix)

# %%
