# -*- coding: utf-8 -*-
"""化学连连看示例关卡

用途：
  · 新装环境 / 从旧版本升级（matching_sets 表刚创建）时，由 main.py 自动灌入
  · 也可以手动执行 backend/seed_matching.py 重新灌入或强制重建
"""
from sqlalchemy import delete, select

from app.models import MatchingPair, MatchingRecord, MatchingSet

SETS = [
    {
        "title": "物质与俗名：这些别称你认得几个",
        "description": "看到俗名能立刻想到化学物质，是化学考试的基本功。",
        "category": "common_name",
        "difficulty": "easy",
        "grade": "高一",
        "pairs": [
            ("氢氧化钠", "烧碱、火碱、苛性钠", "NaOH，强碱，有强腐蚀性"),
            ("碳酸钠", "纯碱、苏打", "Na₂CO₃，水溶液显碱性，俗称纯碱但不是碱"),
            ("碳酸氢钠", "小苏打", "NaHCO₃，可用于治疗胃酸过多、焙制糕点"),
            ("氯化钠", "食盐", "NaCl，厨房里的食盐主要成分"),
            ("氧化钙", "生石灰", "CaO，与水反应放出大量热"),
            ("氢氧化钙", "熟石灰、消石灰", "Ca(OH)₂，澄清石灰水用于检验 CO₂"),
            ("硫酸铜晶体", "胆矾、蓝矾", "CuSO₄·5H₂O，蓝色晶体，受热变白"),
            ("碳酸钙", "石灰石、大理石的主要成分", "CaCO₃，高温分解生成生石灰"),
            ("氧化铁", "铁红", "Fe₂O₃，红棕色，可作红色颜料"),
            ("四氧化三铁", "磁铁矿的主要成分", "Fe₃O₄，有磁性，黑色晶体"),
            ("乙醇", "酒精", "C₂H₅OH，医用酒精的主要成分"),
            ("乙酸", "醋酸、冰醋酸", "CH₃COOH，食醋中的酸味来源"),
        ],
    },
    {
        "title": "官能团与性质：结构决定性质",
        "description": "把官能团和它对应的类别、特征反应配起来。",
        "category": "functional_group",
        "difficulty": "medium",
        "grade": "高二",
        "pairs": [
            ("羟基（—OH）", "醇类，能与钠反应放出 H₂", "乙醇、苯酚都含羟基，但苯酚羟基连在苯环上，酸性更强"),
            ("羧基（—COOH）", "羧酸类，具有酸性，能与 NaHCO₃ 反应放出 CO₂", "乙酸、苯甲酸都含羧基"),
            ("醛基（—CHO）", "醛类，能发生银镜反应", "乙醛与银氨溶液水浴加热生成银镜"),
            ("羰基（>C=O）", "酮类，可与氢气发生加成反应", "丙酮是最简单的酮"),
            ("氨基（—NH₂）", "胺类，具有碱性", "氨基酸中同时含有氨基和羧基"),
            ("酯基（—COO—）", "酯类，可发生水解反应", "乙酸乙酯在酸性或碱性条件下都能水解"),
            ("碳碳双键（C=C）", "烯烃，能发生加成、氧化反应", "乙烯能使溴的四氯化碳溶液褪色"),
            ("碳碳三键（C≡C）", "炔烃，能与溴水、氢气发生加成", "乙炔俗称电石气，可用于焊接"),
            ("苯环", "芳香族化合物，能发生取代反应", "苯的硝化、溴代都属于取代反应"),
            ("醚键（C—O—C）", "醚类，性质比较稳定", "乙醚曾用作麻醉剂，易挥发易燃"),
        ],
    },
    {
        "title": "方程式与现象：看反应写现象",
        "description": "每个方程式都对应一个实验现象或工业用途，连起来记忆更牢。",
        "category": "equation",
        "difficulty": "hard",
        "grade": "高一",
        "pairs": [
            ("2Na + 2H₂O = 2NaOH + H₂↑", "钠浮在水面熔成小球，四处游动", "说明钠密度比水小、熔点低，反应放热"),
            ("Fe + CuSO₄ = FeSO₄ + Cu", "铁表面析出红色固体，溶液由蓝色变浅绿色", "湿法炼铜的原理"),
            ("CaCO₃ →（高温）CaO + CO₂↑", "工业制生石灰", "石灰石高温分解，是制水泥、玻璃的原料之一"),
            ("2H₂O₂ →（MnO₂）2H₂O + O₂↑", "实验室制氧气，带火星木条复燃", "MnO₂ 作催化剂，反应前后质量不变"),
            ("CH₄ + 2O₂ →（点燃）CO₂ + 2H₂O", "淡蓝色火焰，放出大量热", "甲烷完全燃烧，天然气的主要成分"),
            ("2Al + 2NaOH + 2H₂O = 2NaAlO₂ + 3H₂↑", "铝在强碱溶液中也能反应放出气体", "铝既能与酸反应，也能与强碱反应，具有两性"),
            ("C₂H₅OH + 3O₂ →（点燃）2CO₂ + 3H₂O", "乙醇燃烧，发出蓝色火焰", "乙醇可用作燃料，也用作溶剂"),
            ("NaHCO₃ + HCl = NaCl + H₂O + CO₂↑", "产生大量气泡", "小苏打可用于治疗胃酸过多"),
            ("Fe₂O₃ + 3CO →（高温）2Fe + 3CO₂", "红棕色粉末逐渐变黑", "高炉炼铁的主要反应，CO 作还原剂"),
            ("Cu + 2AgNO₃ = Cu(NO₃)₂ + 2Ag", "铜丝表面析出银白色固体，溶液变蓝", "金属活动性：Cu > Ag"),
        ],
    },
    {
        "title": "物质与化学式：快速配对",
        "description": "常见物质的化学式，考前热身用。",
        "category": "substance",
        "difficulty": "easy",
        "grade": "高一",
        "pairs": [
            ("硫酸", "H₂SO₄", "二元强酸，浓硫酸有吸水性、脱水性"),
            ("硝酸", "HNO₃", "强氧化性酸，见光易分解"),
            ("盐酸", "HCl 的水溶液", "氯化氢溶于水得到盐酸"),
            ("氨气", "NH₃", "有刺激性气味，极易溶于水"),
            ("二氧化碳", "CO₂", "能使澄清石灰水变浑浊"),
            ("氢氧化钾", "KOH", "强碱，常用于制肥皂"),
            ("硫酸钡", "BaSO₄", "难溶于水，医学上用作钡餐"),
            ("氯化银", "AgCl", "白色沉淀，难溶于稀硝酸"),
            ("甲烷", "CH₄", "最简单的有机物，正四面体结构"),
            ("乙烯", "C₂H₄", "含碳碳双键，能使溴水褪色"),
        ],
    },
]


async def seed_matching(db, creator_id: int, force: bool = False) -> int:
    """向数据库灌入示例关卡，返回新建数量。

    force=True 会先删掉同名关卡（连同作答记录）再重建。
    """
    created = 0
    for spec in SETS:
        existed = (await db.execute(
            select(MatchingSet).where(
                MatchingSet.title == spec["title"],
                MatchingSet.creator_id == creator_id,
            )
        )).scalar_one_or_none()
        if existed:
            if not force:
                continue
            await db.execute(delete(MatchingRecord).where(MatchingRecord.set_id == existed.id))
            await db.execute(delete(MatchingPair).where(MatchingPair.set_id == existed.id))
            await db.delete(existed)
            await db.commit()

        item = MatchingSet(
            title=spec["title"],
            description=spec["description"],
            category=spec["category"],
            difficulty=spec["difficulty"],
            grade=spec["grade"],
            is_active=True,
            creator_id=creator_id,
        )
        db.add(item)
        await db.flush()
        for index, (left, right, hint) in enumerate(spec["pairs"]):
            db.add(MatchingPair(
                set_id=item.id, left_text=left, right_text=right,
                hint=hint, order_index=index,
            ))
        await db.commit()
        created += 1
    return created
