# -*- coding: utf-8 -*-
# Copyright (c) 2026 侯世勃. All rights reserved.
# 本软件受著作权法保护，未经授权不得用于商业用途。
"""
知识图谱
- 高中化学知识点图谱
- 知识点关联关系
- 前置知识推荐
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User, Question, WrongQuestion

router = APIRouter(prefix="/knowledge-graph", tags=["知识图谱"])

# ========== 高中化学知识图谱数据 ==========
KNOWLEDGE_GRAPH = {
    "nodes": [
        # 必修一
        {"id": "chem-basic", "name": "化学基本概念", "grade": "高一", "category": "基础", "description": "物质的量、摩尔、气体摩尔体积等"},
        {"id": "mole", "name": "物质的量", "grade": "高一", "category": "基础", "description": "摩尔、阿伏伽德罗常数、摩尔质量"},
        {"id": "gas-volume", "name": "气体摩尔体积", "grade": "高一", "category": "基础", "description": "标况下气体摩尔体积22.4L/mol"},
        {"id": "concentration", "name": "物质的量浓度", "grade": "高一", "category": "基础", "description": "溶液浓度计算与配制"},
        {"id": "atom-structure", "name": "原子结构", "grade": "高一", "category": "基础", "description": "原子核外电子排布、同位素"},
        {"id": "periodic-table", "name": "元素周期表", "grade": "高一", "category": "基础", "description": "周期律、元素性质递变"},
        {"id": "chemical-bond", "name": "化学键", "grade": "高一", "category": "基础", "description": "离子键、共价键、金属键"},
        {"id": "redox", "name": "氧化还原反应", "grade": "高一", "category": "反应", "description": "氧化剂还原剂、电子转移、配平"},
        {"id": "ion-reaction", "name": "离子反应", "grade": "高一", "category": "反应", "description": "离子方程式、离子共存"},
        {"id": "na-metal", "name": "钠及其化合物", "grade": "高一", "category": "元素", "description": "Na、Na₂O、Na₂O₂、NaOH、Na₂CO₃、NaHCO₃"},
        {"id": "al-metal", "name": "铝及其化合物", "grade": "高一", "category": "元素", "description": "Al、Al₂O₃、Al(OH)₃的两性"},
        {"id": "fe-metal", "name": "铁及其化合物", "grade": "高一", "category": "元素", "description": "Fe、Fe²⁺、Fe³⁺的转化"},
        {"id": "si-nonmetal", "name": "硅及其化合物", "grade": "高一", "category": "元素", "description": "Si、SiO₂、硅酸盐"},
        {"id": "cl-nonmetal", "name": "氯及其化合物", "grade": "高一", "category": "元素", "description": "Cl₂、HCl、次氯酸、漂白粉"},
        {"id": "s-nonmetal", "name": "硫及其化合物", "grade": "高一", "category": "元素", "description": "S、SO₂、H₂SO₄"},
        {"id": "n-nonmetal", "name": "氮及其化合物", "grade": "高一", "category": "元素", "description": "N₂、NO、NO₂、HNO₃、NH₃"},
        # 必修二
        {"id": "organic-basic", "name": "有机化学基础", "grade": "高一", "category": "有机", "description": "有机物概念、烃、烃的衍生物"},
        {"id": "alkane", "name": "甲烷与烷烃", "grade": "高一", "category": "有机", "description": "甲烷性质、烷烃同系物、同分异构"},
        {"id": "alkene", "name": "乙烯与烯烃", "grade": "高一", "category": "有机", "description": "乙烯加成、加聚反应"},
        {"id": "alkyne", "name": "乙炔", "grade": "高二", "category": "有机", "description": "乙炔性质、炔烃"},
        {"id": "aromatic", "name": "苯与芳香烃", "grade": "高一", "category": "有机", "description": "苯的结构与性质、取代反应"},
        {"id": "alcohol", "name": "乙醇与醇类", "grade": "高一", "category": "有机", "description": "乙醇性质、醇的催化氧化"},
        {"id": "acid", "name": "乙酸与羧酸", "grade": "高一", "category": "有机", "description": "乙酸性质、酯化反应"},
        {"id": "ester", "name": "酯类", "grade": "高二", "category": "有机", "description": "酯的水解、油脂"},
        {"id": "sugar", "name": "糖类", "grade": "高一", "category": "有机", "description": "葡萄糖、蔗糖、淀粉、纤维素"},
        {"id": "protein", "name": "蛋白质", "grade": "高一", "category": "有机", "description": "氨基酸、蛋白质性质"},
        # 选修四
        {"id": "reaction-rate", "name": "化学反应速率", "grade": "高二", "category": "原理", "description": "速率计算、影响因素"},
        {"id": "chemical-equilibrium", "name": "化学平衡", "grade": "高二", "category": "原理", "description": "平衡移动、勒夏特列原理、平衡常数"},
        {"id": "weak-electrolyte", "name": "弱电解质电离", "grade": "高二", "category": "原理", "description": "电离平衡、电离常数"},
        {"id": "water-ionization", "name": "水的电离与pH", "grade": "高二", "category": "原理", "description": "水的离子积、pH计算"},
        {"id": "salt-hydrolysis", "name": "盐类水解", "grade": "高二", "category": "原理", "description": "水解规律、离子浓度比较"},
        {"id": "precipitation-equilibrium", "name": "沉淀溶解平衡", "grade": "高二", "category": "原理", "description": "溶度积、沉淀转化"},
        {"id": "electrochemistry", "name": "电化学", "grade": "高二", "category": "原理", "description": "原电池、电解池、金属腐蚀"},
        {"id": "thermochemistry", "name": "热化学", "grade": "高二", "category": "原理", "description": "反应热、盖斯定律"},
        # 选修五
        {"id": "organic-inference", "name": "有机推断", "grade": "高二", "category": "有机", "description": "有机合成路线、官能团转化"},
        {"id": "polymer", "name": "高分子化合物", "grade": "高二", "category": "有机", "description": "加聚反应、缩聚反应"},
    ],
    "edges": [
        # 基础概念关联
        {"source": "chem-basic", "target": "mole", "relation": "包含"},
        {"source": "mole", "target": "gas-volume", "relation": "延伸"},
        {"source": "mole", "target": "concentration", "relation": "应用"},
        {"source": "atom-structure", "target": "periodic-table", "relation": "基础"},
        {"source": "periodic-table", "target": "chemical-bond", "relation": "决定"},
        # 反应类型
        {"source": "redox", "target": "ion-reaction", "relation": "交叉"},
        {"source": "redox", "target": "electrochemistry", "relation": "基础"},
        {"source": "ion-reaction", "target": "salt-hydrolysis", "relation": "应用"},
        # 元素化合物
        {"source": "periodic-table", "target": "na-metal", "relation": "应用"},
        {"source": "periodic-table", "target": "al-metal", "relation": "应用"},
        {"source": "periodic-table", "target": "fe-metal", "relation": "应用"},
        {"source": "redox", "target": "fe-metal", "relation": "重点"},
        {"source": "periodic-table", "target": "cl-nonmetal", "relation": "应用"},
        {"source": "periodic-table", "target": "s-nonmetal", "relation": "应用"},
        {"source": "periodic-table", "target": "n-nonmetal", "relation": "应用"},
        {"source": "redox", "target": "n-nonmetal", "relation": "重点"},
        # 有机化学
        {"source": "chemical-bond", "target": "organic-basic", "relation": "基础"},
        {"source": "organic-basic", "target": "alkane", "relation": "包含"},
        {"source": "alkane", "target": "alkene", "relation": "递进"},
        {"source": "alkene", "target": "alkyne", "relation": "递进"},
        {"source": "alkene", "target": "aromatic", "relation": "并列"},
        {"source": "alkane", "target": "alcohol", "relation": "衍生"},
        {"source": "alcohol", "target": "acid", "relation": "氧化"},
        {"source": "acid", "target": "ester", "relation": "酯化"},
        {"source": "alcohol", "target": "sugar", "relation": "关联"},
        {"source": "sugar", "target": "protein", "relation": "并列"},
        {"source": "organic-basic", "target": "organic-inference", "relation": "综合"},
        {"source": "alkene", "target": "polymer", "relation": "加聚"},
        # 化学反应原理
        {"source": "reaction-rate", "target": "chemical-equilibrium", "relation": "递进"},
        {"source": "chemical-equilibrium", "target": "weak-electrolyte", "relation": "应用"},
        {"source": "weak-electrolyte", "target": "water-ionization", "relation": "延伸"},
        {"source": "water-ionization", "target": "salt-hydrolysis", "relation": "应用"},
        {"source": "salt-hydrolysis", "target": "precipitation-equilibrium", "relation": "并列"},
        {"source": "redox", "target": "electrochemistry", "relation": "基础"},
        {"source": "thermochemistry", "target": "chemical-equilibrium", "relation": "关联"},
    ],
}


@router.get("/graph", summary="获取知识图谱")
async def get_knowledge_graph(
    grade: str = Query(None, description="按学段筛选：高一/高二"),
    category: str = Query(None, description="按类别筛选：基础/反应/元素/有机/原理"),
):
    """获取高中化学知识图谱"""
    nodes = KNOWLEDGE_GRAPH["nodes"]
    edges = KNOWLEDGE_GRAPH["edges"]

    if grade:
        node_ids = [n["id"] for n in nodes if n.get("grade") == grade]
        nodes = [n for n in nodes if n.get("grade") == grade]
        edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    if category:
        node_ids = [n["id"] for n in nodes if n.get("category") == category]
        nodes = [n for n in nodes if n.get("category") == category]
        edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "categories": list(set(n.get("category", "") for n in nodes)),
            "grades": list(set(n.get("grade", "") for n in nodes)),
        },
    }


@router.get("/node/{node_id}", summary="获取知识点详情")
async def get_knowledge_node(
    node_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取知识点详情，包括关联知识点和相关题目"""
    node = None
    for n in KNOWLEDGE_GRAPH["nodes"]:
        if n["id"] == node_id:
            node = n
            break
    if not node:
        # 尝试按名称匹配
        for n in KNOWLEDGE_GRAPH["nodes"]:
            if n["name"] == node_id:
                node = n
                break
    if not node:
        raise HTTPException(status_code=404, detail="知识点不存在")

    # 找关联知识点
    related = []
    for e in KNOWLEDGE_GRAPH["edges"]:
        if e["source"] == node_id:
            target = next((n for n in KNOWLEDGE_GRAPH["nodes"] if n["id"] == e["target"]), None)
            if target:
                related.append({"node": target, "relation": e["relation"], "direction": "out"})
        elif e["target"] == node_id:
            source = next((n for n in KNOWLEDGE_GRAPH["nodes"] if n["id"] == e["source"]), None)
            if source:
                related.append({"node": source, "relation": e["relation"], "direction": "in"})

    # 查找相关题目
    questions = (await db.execute(
        select(Question).where(Question.knowledge_point.like(f"%{node['name']}%")).limit(10)
    )).scalars().all()

    # 查找用户在该知识点的错题
    wrong_count = 0
    if questions:
        q_ids = [q.id for q in questions]
        wrong_count = (await db.execute(
            select(func.count(WrongQuestion.id)).where(
                WrongQuestion.user_id == current_user.id,
                WrongQuestion.question_id.in_(q_ids)
            )
        )).scalar()

    return {
        "node": node,
        "related": related,
        "related_questions": [
            {"id": q.id, "title": q.title, "difficulty": q.difficulty}
            for q in questions[:5]
        ],
        "user_wrong_count": wrong_count,
    }


@router.get("/prerequisites/{node_id}", summary="获取前置知识")
async def get_prerequisites(
    node_id: str,
):
    """获取某个知识点的前置知识链"""
    visited = set()
    chain = []

    def dfs(nid, depth=0):
        if nid in visited or depth > 5:
            return
        visited.add(nid)
        node = next((n for n in KNOWLEDGE_GRAPH["nodes"] if n["id"] == nid), None)
        if node:
            chain.append({"node": node, "depth": depth})
        # 找入边（前置知识）
        for e in KNOWLEDGE_GRAPH["edges"]:
            if e["target"] == nid and e["relation"] in ["基础", "包含", "递进", "应用"]:
                dfs(e["source"], depth + 1)

    dfs(node_id)
    return {"prerequisites": chain, "count": len(chain)}


@router.get("/user-mastery", summary="用户知识图谱掌握度")
async def user_knowledge_mastery(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """根据用户错题情况，生成知识图谱掌握度"""
    # 获取用户所有错题
    wrongs = (await db.execute(
        select(WrongQuestion).where(WrongQuestion.user_id == current_user.id)
    )).scalars().all()

    # 获取所有题目
    all_questions = (await db.execute(select(Question))).scalars().all()
    q_knowledge = {q.id: q.knowledge_point for q in all_questions if q.knowledge_point}

    # 统计每个知识点的错题数
    knowledge_wrong = {}
    for w in wrongs:
        kp = q_knowledge.get(w.question_id)
        if kp:
            knowledge_wrong[kp] = knowledge_wrong.get(kp, 0) + 1

    # 为图谱节点添加掌握度
    nodes_with_mastery = []
    for node in KNOWLEDGE_GRAPH["nodes"]:
        wrong_count = knowledge_wrong.get(node["name"], 0)
        # 简单估算：有错题就是薄弱
        mastery = "薄弱" if wrong_count > 0 else "未测试"
        level = 1 if wrong_count > 0 else 0
        nodes_with_mastery.append({
            **node,
            "wrong_count": wrong_count,
            "mastery": mastery,
            "mastery_level": level,
        })

    return {
        "nodes": nodes_with_mastery,
        "edges": KNOWLEDGE_GRAPH["edges"],
        "weak_nodes": [n for n in nodes_with_mastery if n["mastery_level"] == 1],
        "total_wrong": sum(knowledge_wrong.values()),
    }
