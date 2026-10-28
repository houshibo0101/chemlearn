"""
批量下载高考真题图片并关联到题目
在服务器上运行：~/chemlearn/backend/venv/bin/python download_gaokao_images.py
"""
import os
import sqlite3
import urllib.request

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "questions")
DB_PATH = os.path.expanduser("~/chemlearn/backend/chemlearn.db")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 题目编号 -> 图片URL列表
# 来源：2024年全国新课标卷化学真题PDF
IMAGE_MAP = {
    "GK2024-XKB-03": [
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/fd412f92906c4f39-6149336c8b9a87ad~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539460&x-signature=oJ3hdzhYt5%2BCYR3dWe3OpLTsla0%3D",
    ],
    "GK2024-XKB-04": [
        "https://p3-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/6807ea8257891a67-65f8c235c61ded18~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539460&x-signature=RXdfEgOT906AWttMO5XLlp6yixM%3D",
    ],
    "GK2024-XKB-07": [
        "https://p3-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/f2b5b7639b0d4d5a-0a9a0a7ef816132f~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539460&x-signature=RrnQihL%2BofEetgCuRRyYK4Yvvz0%3D",
    ],
    "GK2024-XKB-09": [
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/1518a32831da5617-662b8e607c567976~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=jcBfouZwxCodkQHsXo0nJ7KD9gM%3D",
    ],
    "GK2024-XKB-10": [
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/dbf3b0581b174db3-0bf45088ad3995b9~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=Kb3qX7ssw2FvWe8enIdF9hn9gNQ%3D",
    ],
    "GK2024-XKB-11": [
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/fe111bb3c0f68d02-c5e81d34a356c4ff~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=2RNQIkUqYSywR5x3fCJUkgeT6xM%3D",
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/1c9b10578b26552f-7022a7f341ed8bb6~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=ptKkNW4Bjd%2BvaFarMfM9OrHO0RM%3D",
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/a425d40b71649e60-dfe6fe33c02b7e54~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=GQjFHzQrnJb8Z1Tn4BhXcaJg5MM%3D",
    ],
    "GK2024-XKB-12": [
        "https://p3-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/35c45a7a73d22934-5f35c14cef4fc992~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=NwiLYSA9qrd3Yk%2FpggoOvf0eWYQ%3D",
    ],
    "GK2024-XKB-13": [
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/39ea3b66ecca6748-36de2e96065f99af~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539557&x-signature=capLnNaE6Ovm%2BFoFPjBI%2Fe4S%2BZk%3D",
    ],
    "GK2024-XKB-14": [
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/43b2b056ae722de8-af6e60afd78bb98d~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=QA%2BYMhXx3tQFQLuNyckNAZOuoqI%3D",
    ],
    "GK2024-XKB-15": [
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/c9bf6467754f626a-41c4ae31da6132c7~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=w4RKleuF6WE%2Fe50%2BfCZdb8s4ns8%3D",
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/03d6f56e1186e3d2-29c8b0c339336122~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=y%2Bbv5A0AzxCN1Vr6xUBLbRVnCfE%3D",
    ],
    "GK2024-XKB-16": [
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/6815c3d56103b866-a2acf01e7d78de4a~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=QScjB9b9222hNaxlptL7PRfhHTc%3D",
    ],
    "GK2024-XKB-17": [
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/f622006c83cf2778-af65910e9c958717~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=3Ja5NqY8FL4Amnech5kIhtO%2BN6A%3D",
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/f027f33f2cfe767d-e5af5c1e8a0cf52b~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=CO85rv63%2F13ezFZuGO%2FJLSgntMM%3D",
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/47f24f434210ff8c-a7fe09bf010633ff~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=FVZ2SpYTdAo7o54xtc0jjBr7C5Y%3D",
        "https://p3-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/7a82dc4e70f9968c-a3f2d7efa34a1b90~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539570&x-signature=3e9GVTXg5NRGe7DiUr0%2BXE4VCso%3D",
    ],
    "GK2024-XKB-18": [
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/cf8c0f6487fce1fe-5ac633b8c12a4624~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539579&x-signature=8Ij1SJ%2BmsokL2dCYOyJlySgm%2FoQ%3D",
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/7b248a0f6c06691d-f6d690408ccf282c~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539579&x-signature=da8unNQTjrTLcwJgVj9tG8BhRFs%3D",
        "https://p26-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/11a943d7ac64b833-923225bd6c524381~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539579&x-signature=apdJN6xk4uTxjqgrCyDw3DkdHLU%3D",
        "https://p11-doubao-search-sign.byteimg.com/isp-i18n-media/pdf-image/70ce92146e6c9487-834b72401e22d326~tplv-be4g95zd3a-896x896.jpeg?lk3s=0ed4045e&x-expires=1806539579&x-signature=bB2Lc8t2CJFBfZfwIwypGvgoqAk%3D",
    ],
}


def download_image(url, filepath):
    """下载图片"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(filepath, "wb") as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"  下载失败: {e}")
        return False


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    total = 0
    success = 0

    for q_code, urls in IMAGE_MAP.items():
        # 查题目ID
        cursor.execute("SELECT id FROM questions WHERE question_code = ?", (q_code,))
        row = cursor.fetchone()
        if not row:
            print(f"跳过（题目不存在）: {q_code}")
            continue

        q_id = row[0]
        image_paths = []

        print(f"处理 {q_code} (ID={q_id}), {len(urls)}张图...")

        for i, url in enumerate(urls):
            filename = f"{q_code}_{i+1}.jpg"
            filepath = os.path.join(UPLOAD_DIR, filename)
            total += 1

            if download_image(url, filepath):
                image_paths.append(f"/uploads/questions/{filename}")
                success += 1
                print(f"  ✓ {filename}")
            else:
                print(f"  ✗ 第{i+1}张下载失败")

        # 更新数据库
        if image_paths:
            import json
            cursor.execute(
                "UPDATE questions SET images = ? WHERE id = ?",
                (json.dumps(image_paths, ensure_ascii=False), q_id)
            )

    conn.commit()
    conn.close()
    print(f"\n完成！下载 {success}/{total} 张图片")


if __name__ == "__main__":
    main()
