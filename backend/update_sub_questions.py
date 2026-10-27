"""
更新2024年高考真题大题为分小问格式
在服务器上运行：~/chemlearn/backend/venv/bin/python update_sub_questions.py
"""
import os
import sqlite3
import json

DB_PATH = os.path.expanduser("~/chemlearn/backend/chemlearn.db")

# 4道大题的分小问数据
SUB_QUESTIONS = {
    "GK2024-XKB-15": [
        {
            "id": 1,
            "content": "(1)“还原浸出”中还原性糖的作用是___；能提高锰浸出率的措施有___（答2条）。",
            "answer": "把二氧化锰还原为硫酸锰；把软锰矿粉碎、搅拌、加热等",
            "keywords": [
                {"word": "还原", "score": 1},
                {"word": "二氧化锰", "score": 1},
                {"word": "粉碎", "score": 1},
                {"word": "搅拌", "score": 1},
                {"word": "加热", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 2,
            "content": "(2)滤渣1的主要成分是___。",
            "answer": "SiO2",
            "keywords": [{"word": "SiO2", "score": 1}, {"word": "二氧化硅", "score": 1}],
            "score": 1,
        },
        {
            "id": 3,
            "content": "(3)“除杂”中调节pH≈5~6，生成的沉淀为___。",
            "answer": "Al(OH)3、Fe(OH)3",
            "keywords": [
                {"word": "Al(OH)3", "score": 1},
                {"word": "Fe(OH)3", "score": 1},
                {"word": "氢氧化铝", "score": 1},
                {"word": "氢氧化铁", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 4,
            "content": "(4)试剂X宜选用___（填标号）。A.H2S  B.Na2S  C.(NH4)2S  D.CuS",
            "answer": "C",
            "keywords": [{"word": "C", "score": 1}],
            "score": 1,
        },
        {
            "id": 5,
            "content": "(5)“沉锰”的离子方程式为___。",
            "answer": "2Mn2++3CO32-+2H2O=Mn2(OH)2CO3↓+2HCO3-",
            "keywords": [
                {"word": "Mn2+", "score": 1},
                {"word": "CO32-", "score": 1},
                {"word": "Mn2(OH)2CO3", "score": 1},
                {"word": "HCO3-", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 6,
            "content": "(6)KMnF3的摩尔质量为151g/mol，其晶胞参数为a pm，阿伏加德罗常数为NA，晶体密度为___g/cm3（列出计算式）。",
            "answer": "151/(NA×a3×10-30)",
            "keywords": [
                {"word": "151", "score": 1},
                {"word": "NA", "score": 1},
                {"word": "a3", "score": 1},
                {"word": "10-30", "score": 1},
            ],
            "score": 2,
        },
    ],
    "GK2024-XKB-16": [
        {
            "id": 1,
            "content": "(1)仪器a的名称是___；装置A中制取Cl2的化学方程式为___。",
            "answer": "分液漏斗；MnO2+4HCl(浓)△MnCl2+Cl2↑+2H2O",
            "keywords": [
                {"word": "分液漏斗", "score": 1},
                {"word": "MnO2", "score": 1},
                {"word": "HCl", "score": 1},
                {"word": "Cl2", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 2,
            "content": "(2)装置B中试剂是___，作用是___。",
            "answer": "饱和食盐水；除去Cl2中的HCl",
            "keywords": [
                {"word": "饱和食盐水", "score": 1},
                {"word": "HCl", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 3,
            "content": "(3)实验时先点燃A处酒精灯，待装置D中充满黄绿色气体后，再点燃D处酒精灯，目的是___。",
            "answer": "排尽装置中的空气，防止Fe被O2氧化",
            "keywords": [
                {"word": "空气", "score": 1},
                {"word": "氧化", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 4,
            "content": "(4)设计实验验证无水FeCl3与KI发生了反应：取少量D中固体溶于水，___（补充操作和现象）。已知：Fe3+与I-反应生成Fe2+和I2。",
            "answer": "滴加KSCN溶液，溶液不变红；再滴加淀粉溶液，溶液变蓝",
            "keywords": [
                {"word": "KSCN", "score": 1},
                {"word": "淀粉", "score": 1},
                {"word": "变蓝", "score": 1},
            ],
            "score": 2,
        },
    ],
    "GK2024-XKB-17": [
        {
            "id": 1,
            "content": "(1)反应2CO(g)+O2(g)=2CO2(g)的ΔH=___kJ/mol。",
            "answer": "-566",
            "keywords": [{"word": "566", "score": 1}, {"word": "-566", "score": 1}],
            "score": 2,
        },
        {
            "id": 2,
            "content": "(2)一定温度下，向恒容密闭容器中充入等物质的量的CH4和CO2，发生反应CH4(g)+CO2(g)⇌2CO(g)+2H2(g)。下列能说明反应达到平衡状态的是___（填标号）。",
            "answer": "容器内压强不再变化；CO的体积分数不再变化",
            "keywords": [
                {"word": "压强", "score": 1},
                {"word": "体积分数", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 3,
            "content": "(3)在恒压、CO2和H2的起始浓度一定的条件下，反应CO2(g)+3H2(g)⇌CH3OH(g)+H2O(g)中，CO2的平衡转化率随温度变化如图所示。温度升高，CO2平衡转化率降低的原因是___。",
            "answer": "正反应放热，升高温度平衡逆向移动",
            "keywords": [
                {"word": "放热", "score": 1},
                {"word": "逆向", "score": 1},
                {"word": "平衡", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 4,
            "content": "(4)在催化剂作用下，CO2与H2合成CH3OH的反应速率方程为v=k·c(CO2)·c3(H2)。某温度下，当c(CO2)=0.1mol/L、c(H2)=0.3mol/L时，v=0.027mol/(L·min)，则k=___。",
            "answer": "10",
            "keywords": [{"word": "10", "score": 1}],
            "score": 2,
        },
        {
            "id": 5,
            "content": "(5)电解CO2制CO的装置如图所示，阴极的电极反应式为___。",
            "answer": "CO2+2H++2e-=CO+H2O",
            "keywords": [
                {"word": "CO2", "score": 1},
                {"word": "CO", "score": 1},
                {"word": "H2O", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 6,
            "content": "(6)以CO2为原料合成高分子材料的优点是___（答1条）。",
            "answer": "减少温室气体；缓解白色污染",
            "keywords": [
                {"word": "温室", "score": 1},
                {"word": "白色污染", "score": 1},
                {"word": "环保", "score": 1},
            ],
            "score": 1,
        },
    ],
    "GK2024-XKB-18": [
        {
            "id": 1,
            "content": "(1)A可由R(邻二溴苯)合成，R的化学名称是___。",
            "answer": "邻二溴苯",
            "keywords": [{"word": "邻二溴苯", "score": 1}, {"word": "1,2-二溴苯", "score": 1}],
            "score": 1,
        },
        {
            "id": 2,
            "content": "(2)由A生成B的化学方程式为___。",
            "answer": "A与ClCH2OCH3在K2CO3作用下生成B和HCl",
            "keywords": [
                {"word": "ClCH2OCH3", "score": 1},
                {"word": "K2CO3", "score": 1},
                {"word": "HCl", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 3,
            "content": "(3)D中含氧官能团的名称是___。",
            "answer": "羟基、醚键、醛基",
            "keywords": [
                {"word": "羟基", "score": 1},
                {"word": "醚键", "score": 1},
                {"word": "醛基", "score": 1},
            ],
            "score": 2,
        },
        {
            "id": 4,
            "content": "(4)F生成G的反应类型为___。",
            "answer": "还原反应",
            "keywords": [{"word": "还原", "score": 1}],
            "score": 1,
        },
        {
            "id": 5,
            "content": "(5)符合下列条件的C的含苯环同分异构体共有___种，其中能与NaHCO3溶液反应产生气体的结构简式为___（任写一种）。条件：①遇Fe3+显色；②含酯基；③核磁共振氢谱5组峰，峰面积比6:2:2:1:1。",
            "answer": "多种；含羧基和酚羟基的酯类同分异构体",
            "keywords": [
                {"word": "Fe3+", "score": 1},
                {"word": "酯基", "score": 1},
                {"word": "羧基", "score": 1},
            ],
            "score": 3,
        },
        {
            "id": 6,
            "content": "(6)某同学用乙酸酐代替ClCH2OCH3保护酚羟基，设计更短路线。由J推出K的结构简式为___。A→J的转化___（合理/不合理），理由是___。",
            "answer": "K为含乙酸酯基的中间体；不合理；乙酸酐会与醛基或其他官能团反应",
            "keywords": [
                {"word": "乙酸酐", "score": 1},
                {"word": "不合理", "score": 1},
                {"word": "反应", "score": 1},
            ],
            "score": 3,
        },
    ],
}


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for q_code, sub_qs in SUB_QUESTIONS.items():
        cursor.execute("SELECT id FROM questions WHERE question_code = ?", (q_code,))
        row = cursor.fetchone()
        if not row:
            print(f"跳过（题目不存在）: {q_code}")
            continue

        q_id = row[0]
        cursor.execute(
            "UPDATE questions SET sub_questions = ? WHERE id = ?",
            (json.dumps(sub_qs, ensure_ascii=False), q_id)
        )
        print(f"✓ 更新 {q_code} (ID={q_id})，{len(sub_qs)}个小问")

    conn.commit()
    conn.close()
    print("\n完成！")


if __name__ == "__main__":
    main()
