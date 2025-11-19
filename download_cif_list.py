# qpod_extract_material_ids.py
# 只提取类似 2AgBrSe2-1.Ag_Br.0.1 这样的唯一ID，一行一个
# Python 3.6+ 即可运行，只需 requests 和 beautifulsoup4

import requests
from bs4 import BeautifulSoup
import time
import os

# ================== 配置区 ==================
sid = 73                              # ← 修改这里的 sid 即可
output_file = f"qpod_sid{sid}_material_ids.txt"   # 输出文件名
interval = 5                          # 每页间隔秒数（建议 4~6 秒，对服务器友好）
session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
)
# ===========================================

# 断点续爬：如果文件已存在，读取最后一条ID，避免重复
existing_ids = set()
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                existing_ids.add(line)
    print(f"检测到已有 {len(existing_ids)} 条ID，将从上次位置继续...")

with open(output_file, "a", encoding="utf-8") as f:
    page = 0
    while True:
        url = f"https://qpod.fysik.dtu.dk/table?sid={sid}&page={page}"
        print(f"正在抓取第 {page+1} 页 → {url}")

        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print("请求出错：", e)
            print("10秒后重试本页...")
            time.sleep(10)
            continue

        soup = BeautifulSoup(r.text, "html.parser")

        rows = soup.select("tbody tr")
        if not rows:
            print("本页没有数据行，可能是结构变了，打印前500字符排查：")
            print(r.text[:500])
            break

        links = []
        for row in rows:
            anchor = row.select_one("th a[href*='/material/']")
            if anchor:
                links.append(anchor)

        if not links:
            print("没有找到任何 material 链接，打印前500字符排查：")
            print(r.text[:500])
            break

        new_count = 0
        for a in links:
            material_id = a["href"].split("/material/")[1]   # 提取 xxx 部分
            if material_id not in existing_ids:
                f.write(material_id + "\n")
                existing_ids.add(material_id)
                new_count += 1

        f.flush()
        os.fsync(f.fileno())

        print(f"第 {page+1} 页完成，本页新增 {new_count} 条，累计 {len(existing_ids)} 条")

        # 判断是否到最后一页
        next_btn = soup.find(
            "a",
            class_="page-link",
            string=lambda s: s and s.strip() in [">", "›", "Next"],
        )

        if not next_btn:
            print("没有下一页按钮，结束。")
            break

        parent_li = next_btn.find_parent("li")
        if parent_li and "disabled" in parent_li.get("class", []):
            print("已到达最后一页！")
            break

        page += 1
        time.sleep(interval)  # 礼貌等待

print(f"\n全部完成！共 {len(existing_ids)} 条 material ID 已保存到：")
print(output_file)
