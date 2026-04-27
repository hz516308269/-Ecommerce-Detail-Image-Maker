#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商图片生成插件
支持 OpenClaw / Hermes 等 Agent 框架

本插件完整实现《电商图片生成使用说明（完整版）》的所有规范
文档位置：C:\\Users\\Demo\\Desktop\\使用说明.md
"""

import os
import json
import base64
import requests

# ═══════════════════════════════════════════════════════════════════════════════
# 配置管理
# ═══════════════════════════════════════════════════════════════════════════════

CONFIG_FILE = os.path.expanduser("~/.ecommerce_image_config.json")

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_config(config):
    """保存配置"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_api_key():
    """获取 API Key（优先环境变量，其次配置文件）"""
    key = os.environ.get('HENNG_API_KEY', '')
    if key:
        return key
    return load_config().get('api_key', '')

def set_api_key(key):
    """设置 API Key（同时写入环境变量和配置文件）"""
    os.environ['HENNG_API_KEY'] = key
    config = load_config()
    config['api_key'] = key
    save_config(config)
    return True

# ═══════════════════════════════════════════════════════════════════════════════
# 常量定义
# ═══════════════════════════════════════════════════════════════════════════════

# 充值提示（余额不足时显示）
RECHARGE_MSG = """
💰 余额不足，请充值

充值方式：
添加微信：nulifeiyu001
备注：电商生图充值

价格：5元/套
包含：5张主图 + 5张描述图
"""

# 桌面路径
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
OUTPUT_BASE = os.path.join(DESKTOP_PATH, "描述图制作")

# ═══════════════════════════════════════════════════════════════════════════════
# 加载 prompts.json（支持远程更新）
# ═══════════════════════════════════════════════════════════════════════════════

PROMPTS_FILE = os.path.join(os.path.dirname(__file__), "prompts.json")

def load_prompts():
    """加载提示词模板，支持从 prompts.json 读取"""
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告：加载 prompts.json 失败: {e}，使用内置默认值")
    return None

_PROMPTS_DATA = load_prompts()

def get_prompt(template_key, fallback_prompt=""):
    """获取提示词模板，优先从 prompts.json 读取"""
    if _PROMPTS_DATA and 'templates' in _PROMPTS_DATA:
        template = _PROMPTS_DATA['templates'].get(template_key, {})
        return template.get('prompt', fallback_prompt)
    return fallback_prompt

def get_category_map():
    """获取类目映射表，优先从 prompts.json 读取"""
    if _PROMPTS_DATA and 'category_map' in _PROMPTS_DATA:
        return _PROMPTS_DATA['category_map']
    return CATEGORY_MAP

# ═══════════════════════════════════════════════════════════════════════════════
# 零、文件夹管理规范（强制执行）
# ═══════════════════════════════════════════════════════════════════════════════

# 每次生成图片必须按以下结构分类存放，禁止散落在根目录：
#
# 描述图制作/
# └── {商品名称}-{颜色/特征}/
#     ├── 白底图/
#     │   └── 原始白底图.png
#     ├── 主图/
#     │   ├── 主图 01-促销首图.png
#     │   ├── 主图 02-痛点解决图.png
#     │   ├── 主图 03-设计细节图.png
#     │   ├── 主图 04-场景穿搭图.png
#     │   └── 主图 05-白底图.png
#     └── 详情图/
#         ├── 01-首屏焦点.png
#         ├── 02-对比卖点.png
#         ├── 03-工艺细节.png
#         ├── 04-场景展示.png
#         └── 05-尺码售后.png
#
# 命名规则：
# - 商品主文件夹：{商品名称}-{颜色/特征}（如：天丝套装 - 米色 、 头层牛皮拖鞋 - 卡其色）
# - 子文件夹固定为：白底图/、 主图/、 详情图/
# - 图片文件：按功能命名
#
# 目的：避免根目录混乱，方便多商品并行管理和查找。

def create_folder_structure(product_name, color):
    """创建文件夹结构"""
    folder_name = f"{product_name}-{color}"
    base_path = os.path.join(OUTPUT_BASE, folder_name)
    
    folders = {
        'base': base_path,
        'white': os.path.join(base_path, '白底图'),
        'main': os.path.join(base_path, '主图'),
        'detail': os.path.join(base_path, '详情图')
    }
    
    for path in folders.values():
        os.makedirs(path, exist_ok=True)
    
    return folders

def copy_white_image(source_path, dest_folder):
    """复制白底图到目标文件夹"""
    import shutil
    ext = os.path.splitext(source_path)[1] or '.png'
    dest_path = os.path.join(dest_folder, f'原始白底图{ext}')
    shutil.copy2(source_path, dest_path)
    return dest_path

# ═══════════════════════════════════════════════════════════════════════════════
# 一、淘宝主图生成 - 6 约束法（已验证✅）
# ═══════════════════════════════════════════════════════════════════════════════

# 5 张主图结构：
#
# | 序号 | 文件名 | 功能 | 核心目标 |
# |:---|:---|:---|:---|
# | 01 | 主图 01-促销首图 | 点击率 | 抓眼球，促点击 |
# | 02 | 主图 02-痛点解决 | 转化率 | 解决顾虑 |
# | 03 | 主图 03-设计细节 | 差异化 | 展示卖点 |
# | 04 | 主图 04-场景穿搭 | 购买欲 | 代入感 |
# | 05 | 主图 05-白底图 | 平台权重 | 活动报名 |
#
# 通用强约束（所有主图）：
# 1. 必须使用白底图参考，严格遵循款式、颜色、版型
# 2. 尺寸 1024×1024px 方图（800×800 会报 upstream_error）
# 3. 以淘宝运营专家视角设计
# 4. 只写 1-2 个卖点，手机端文字清晰可读
# 5. 必须体现促销价格，价格醒目
# 6. 使用 https://api.henng.cn/v1/images/edits 接口，images 数组传 base64 data URL
# 7. 提示词必须包含："不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改"

# ═══════════════════════════════════════════════════════════════════════════════
# 二、主图详细提示词模板（5 张）
# ═══════════════════════════════════════════════════════════════════════════════

# 主图 01-促销首图
# 约束：只写 1-2 个卖点，手机端文字清晰，价格醒目

MAIN_IMAGE_01_PROMPT = get_prompt('main_image_01', """用这张白底图做一张淘宝主图。调用接口：https://api.henng.cn/v1/images/edits

约束条件：
1. 这是【促销首图】，目标是最大化点击率
2. 必须使用提供的白底图作为参考，严格遵循款式、颜色、版型
3. 尺寸 1024×1024px 方图
4. 以淘宝运营专家视角设计
5. 只写最重要的 1-2 个卖点，手机端缩略图文字必须清晰可读
6. 必须体现促销价格，价格要醒目突出
7. 不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改

商品信息：
- 商品：{product_name}
- 原价：{original_price}元
- 现价：{current_price}元
- 核心卖点：{selling_points}

你是淘宝运营专家，请从运营视角自由发挥设计。""")

# 主图 02-痛点解决图
# 约束：明确痛点 + 解决方案，让用户产生共鸣

MAIN_IMAGE_02_PROMPT = """用这张白底图做一张淘宝主图。调用接口：https://api.henng.cn/v1/images/edits

约束条件：
1. 这是【痛点解决图】，目标是解决用户顾虑、提升转化率
2. 必须使用提供的白底图作为参考，严格遵循款式、颜色、版型
3. 尺寸 1024×1024px 方图
4. 以淘宝运营专家视角设计
5. 不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改

商品信息：
- 商品：{product_name}
- 核心痛点：{pain_points}
- 解决方案：{solutions}

你是淘宝运营专家，请从运营视角自由发挥设计这张痛点解决图。"""

# 主图 03-设计细节图
# 约束：手机端文字清晰可读

MAIN_IMAGE_03_PROMPT = """用这张白底图做一张淘宝主图。调用接口：https://api.henng.cn/v1/images/edits

约束条件：
1. 这是【设计细节图】，目标是展示卖点、差异化竞争
2. 必须使用提供的白底图作为参考，严格遵循款式、颜色、版型
3. 尺寸 1024×1024px 方图
4. 以淘宝运营专家视角设计
5. 手机端缩略图文字必须清晰可读，字体大小要合适
6. 不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改

商品信息：
- 商品：{product_name}
- 核心细节：{details}

你是淘宝运营专家，请从运营视角自由发挥设计这张设计细节图。"""

# 主图 04-场景穿搭图
# 约束：明确适用场景，手机端文字清晰

MAIN_IMAGE_04_PROMPT = """用这张白底图做一张淘宝主图。调用接口：https://api.henng.cn/v1/images/edits

约束条件：
1. 这是【场景穿搭图】，目标是代入感、激发购买欲
2. 必须使用提供的白底图作为参考，严格遵循款式、颜色、版型
3. 尺寸 1024×1024px 方图
4. 以淘宝运营专家视角设计
5. 手机端缩略图文字必须清晰可读，字体大小要合适
6. 不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改

商品信息：
- 商品：{product_name}
- 适用场景：{scenes}

你是淘宝运营专家，请从运营视角自由发挥设计这张场景穿搭图。"""

# 主图 05-白底图
# 约束：纯白底无任何文字装饰，商品居中

MAIN_IMAGE_05_PROMPT = """用这张白底图做一张淘宝主图。调用接口：https://api.henng.cn/v1/images/edits

约束条件：
1. 这是【白底图】，目标是符合平台活动报名要求
2. 必须使用提供的白底图作为参考，严格遵循款式、颜色、版型
3. 尺寸 1024×1024px 方图
4. 以淘宝运营专家视角设计
5. 纯白色背景（#FFFFFF），无任何文字、无任何装饰、无任何模特、无任何道具
6. 商品居中摆放，完整清晰，仅保留自然产品轮廓阴影
7. 不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改

你是淘宝运营专家，请从运营视角生成一张符合平台规范的纯白底图。"""

# ═══════════════════════════════════════════════════════════════════════════════
# 三、电商详情图 - 动态自适应模板（核心）
# ═══════════════════════════════════════════════════════════════════════════════

# 2.1 核心逻辑
#
# 固定骨架 + 动态约束 = 高质量自适应
#
# - 固定约束（硬规则）：图 03/图 05 绝对不能有商品图，尺寸 1024×1536
# - 动态匹配（agent 自主）：识别类目→自动匹配对比维度/场景类型/细节点
#
# 执行流程：
# 1. agent 识别白底图类目（女装/鞋靴/箱包/数码...）
# 2. 按类目自动查表匹配动态规则
# 3. 注入 prompt 生成 5 张详情图

# 2.2 5 图固定结构
#
# | 图号 | 类型 | 是否含商品 | 自适应规则 |
# |:---|:---|:---|:---|
# | 01 | 首屏焦点图 | ✅ | 按价格带：低客单促销/高客单价值 |
# | 02 | 对比卖点图 | ✅ | 按类目选对比维度 |
# | 03 | 工艺细节图 | ❌ | 纯细节特写，4 个细节点 + 文字 |
# | 04 | 场景展示图 | ✅ | 按类目选场景类型 |
# | 05 | 尺码售后图 | ❌ | 纯信息排版，无商品 |
#
# 硬约束（所有类目通用）：
# - 图 03：4 个细节特写 + 文字说明，绝对不要完整商品
# - 图 05：纯信息排版（尺码表/售后/促单），绝对不要商品图
# - 图 04：场景展示图，一张图里至少体现 2 个不同场景（如"街头潮搭 + 校园穿搭"）
# - 尺寸：1024×1536 竖版
# - 文字：手机端清晰可读，每图 1-2 个卖点

# 2.3 类目动态映射表

# 图 04-场景展示自适应：
#
# | 类目 | 场景类型 | 提示词关键词（示例，model 可自由发挥） |
# |:---|:---|:---|
# | 女装/男装 | 真人穿搭 | "真人模特穿搭场景：职场通勤、周末休闲、街头潮搭、约会聚餐、咖啡厅、逛街购物" |
# | 鞋靴 | 真人上脚 | "真人上脚穿搭场景：商务场合、日常休闲、街头潮搭、校园穿搭、周末出游、滑板公园、音乐节、朋友聚会" |
# | 箱包 | 真人搭配 | "真人搭配展示场景：通勤背负、逛街手提、机场出行、职场会议、周末短途旅行" |
# | 配饰/首饰 | 真人佩戴 | "真人佩戴展示场景：日常搭配、晚宴场合、约会、职场、派对、婚礼" |
# | 工具/五金 | 真人使用 | "真人使用场景：专业作业、家庭 DIY、车间维修、户外施工、车库改装" |
# | 数码/电子 | 真人使用 | "真人使用场景：办公桌面、移动出行、咖啡厅办公、居家娱乐、游戏电竞、户外拍摄" |
# | 家居/家纺 | 场景摆放 | "场景展示：客厅摆放、卧室使用、书房布置、餐厅摆盘、阳台休闲、玄关装饰" |
# | 食品/生鲜 | 场景食用 | "场景展示：餐桌摆盘、制作过程、野餐露营、办公室零食、家庭聚餐、下午茶" |

# 图 02-对比卖点自适应：
#
# | 类目 | 对比维度 | 示例 |
# |:---|:---|:---|
# | 服装 | 面料对比 | 普通面料 vs 天丝面料 |
# | 鞋靴 | 舒适度对比 | 普通鞋底 vs 缓震鞋底 |
# | 箱包 | 容量对比 | 普通包 vs 扩容设计 |
# | 数码 | 性能对比 | 普通充电 vs 快充 |
# | 家居 | 材质对比 | 普通材质 vs 环保材质 |
# | 食品 | 原料对比 | 普通原料 vs 有机原料 |

# 图 03-工艺细节自适应：
#
# | 类目 | 细节点选择 | 示例 |
# |:---|:---|:---|
# | 服装 | 面料/走线/领口/袖口 | 天丝面料、精密走线、V 领设计、舒适袖口 |
# | 鞋靴 | 鞋面/鞋底/内里/工艺 | 头层牛皮、防滑底、透气内里、手工缝线 |
# | 箱包 | 材质/五金/内衬/拉链 | 头层牛皮、金属拉链、分区内衬、加固提手 |
# | 首饰 | 材质/工艺/镶嵌/抛光 | 925 银、磨砂工艺、精密镶嵌、镜面抛光 |
# | 数码 | 接口/散热/材质/工艺 | Type-C 接口、散热孔、铝合金、CNC 工艺 |

# 图 01-首屏焦点自适应：
#
# | 价格带 | 首屏策略 | 提示词重点 |
# |:---|:---|:---|
# | 低客单（<100） | 促销驱动 | "限时特价、库存紧张、立即抢购" |
# | 中客单（100-500） | 价值 + 促销 | "品质之选、限时优惠" |
# | 高客单（>500） | 价值驱动 | "匠心工艺、品质生活、轻奢之选" |

CATEGORY_MAP = {
    '女装': {
        'scene': '真人模特穿搭场景：职场通勤、周末休闲、街头潮搭、约会聚餐、咖啡厅、逛街购物',
        'comparison': '面料对比',
        'details': ['面料', '走线', '领口', '袖口']
    },
    '男装': {
        'scene': '真人模特穿搭场景：职场通勤、周末休闲、街头潮搭、约会聚餐、咖啡厅、逛街购物',
        'comparison': '面料对比',
        'details': ['面料', '走线', '领口', '袖口']
    },
    '鞋靴': {
        'scene': '真人上脚穿搭场景：商务场合、日常休闲、街头潮搭、校园穿搭、周末出游、滑板公园、音乐节、朋友聚会',
        'comparison': '舒适度对比',
        'details': ['鞋面', '鞋底', '内里', '工艺']
    },
    '箱包': {
        'scene': '真人搭配展示场景：通勤背负、逛街手提、机场出行、职场会议、周末短途旅行',
        'comparison': '容量对比',
        'details': ['材质', '五金', '内衬', '拉链']
    },
    '配饰': {
        'scene': '真人佩戴展示场景：日常搭配、晚宴场合、约会、职场、派对、婚礼',
        'comparison': '材质对比',
        'details': ['材质', '工艺', '镶嵌', '抛光']
    },
    '首饰': {
        'scene': '真人佩戴展示场景：日常搭配、晚宴场合、约会、职场、派对、婚礼',
        'comparison': '材质对比',
        'details': ['材质', '工艺', '镶嵌', '抛光']
    },
    '工具': {
        'scene': '真人使用场景：专业作业、家庭 DIY、车间维修、户外施工、车库改装',
        'comparison': '性能对比',
        'details': ['材质', '工艺', '接口', '耐用性']
    },
    '五金': {
        'scene': '真人使用场景：专业作业、家庭 DIY、车间维修、户外施工、车库改装',
        'comparison': '性能对比',
        'details': ['材质', '工艺', '接口', '耐用性']
    },
    '数码': {
        'scene': '真人使用场景：办公桌面、移动出行、咖啡厅办公、居家娱乐、游戏电竞、户外拍摄',
        'comparison': '性能对比',
        'details': ['接口', '散热', '材质', '工艺']
    },
    '电子': {
        'scene': '真人使用场景：办公桌面、移动出行、咖啡厅办公、居家娱乐、游戏电竞、户外拍摄',
        'comparison': '性能对比',
        'details': ['接口', '散热', '材质', '工艺']
    },
    '家居': {
        'scene': '场景展示：客厅摆放、卧室使用、书房布置、餐厅摆盘、阳台休闲、玄关装饰',
        'comparison': '材质对比',
        'details': ['材质', '工艺', '结构', '环保']
    },
    '家纺': {
        'scene': '场景展示：客厅摆放、卧室使用、书房布置、餐厅摆盘、阳台休闲、玄关装饰',
        'comparison': '材质对比',
        'details': ['材质', '工艺', '触感', '环保']
    },
    '食品': {
        'scene': '场景展示：餐桌摆盘、制作过程、野餐露营、办公室零食、家庭聚餐、下午茶',
        'comparison': '原料对比',
        'details': ['原料', '工艺', '口感', '包装']
    },
    '生鲜': {
        'scene': '场景展示：餐桌摆盘、制作过程、野餐露营、办公室零食、家庭聚餐、下午茶',
        'comparison': '原料对比',
        'details': ['新鲜度', '产地', '口感', '包装']
    },
}

def get_category_info(category):
    """获取类目信息
    
    重要：动态映射表是"常见类目示例"，不是"穷举限制"。
    遇到表里没有的类目（如早餐机、新型数码产品等），
    Agent 必须自主推理该类目的使用场景、对比维度、工艺细节点，
    而不是死板套表或报错。
    """
    return CATEGORY_MAP.get(category, None)  # 表里没有返回 None，让 Agent 自主推理

def get_price_strategy(price):
    """根据价格获取首屏策略"""
    if price < 100:
        return '低客单促销驱动：限时特价、库存紧张、立即抢购'
    elif price <= 500:
        return '中客单价值+促销：品质之选、限时优惠'
    else:
        return '高客单价值驱动：匠心工艺、品质生活、轻奢之选'

# 2.4 详情图通用提示词模板
#
# 调用方式：每次一张图，分 5 次调用，每次都是完整提示词 + 白底图，使用 https://api.henng.cn/v1/images/edits 接口
#
# 通用强约束（所有详情图）：
# 1. 以淘宝运营专家视角设计
# 2. 不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改
# 3. 尺寸：1024×1536 竖版
# 4. 文字：手机端清晰可读，每图 1-2 个卖点
# 5. 图 03 工艺细节：必须是 4 个局部特写 + 文字，绝对不要完整商品
# 6. 图 05 尺码售后：必须是纯信息排版，绝对不要商品图
# 7. 图 04 场景展示：一张图里至少体现 2 个不同场景
# 8. 图 02-05 绝对不要出现价格数字

# 提示词模板（每张图单独调用）：

# 详情图 01-首屏焦点图（低客单示例）：
DETAIL_IMAGE_01_PROMPT = """用这张白底图做一张淘宝详情图，竖版 1024×1536。以淘宝运营专家视角设计。

这是首屏焦点图，目标是 3 秒内抓住注意力，让用户继续往下看。

不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改。

商品是{product_name}，价格{current_price}元（低价促销）。突出"{current_price}元超值价"，营造捡漏感。只写 1-2 个核心卖点，文字清晰可读。风格简约大气。

尺寸 1024×1536px 竖版。不指定具体排版。"""

# 详情图 02-对比卖点图：
DETAIL_IMAGE_02_PROMPT = """用这张白底图做一张淘宝详情图，竖版 1024×1536。以淘宝运营专家视角设计。

这是对比卖点图，目标是通过对比展示产品优势。

不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改。

对比维度：{comparison_dimension}。用对比方式展示，让用户一眼看出优势。手机端文字清晰可读。

尺寸 1024×1536px 竖版。不指定具体排版。

注意：这张图不显示价格。"""

# 详情图 03-工艺细节图：
DETAIL_IMAGE_03_PROMPT = """用这张白底图做一张淘宝详情图，竖版 1024×1536。以淘宝运营专家视角设计。

这是工艺细节图，目标是展示做工和品质细节。

不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改。

展示 4 个特写细节：{detail_points}。纯细节展示，这张图里不出现完整商品。文字标注清晰，突出品质感。

尺寸 1024×1536px 竖版。不指定具体排版。

注意：这张图不显示价格。"""

# 详情图 04-场景展示图：
DETAIL_IMAGE_04_PROMPT = """用这张白底图做一张淘宝详情图，竖版 1024×1536。以淘宝运营专家视角设计。

这是场景展示图，目标是让用户想象自己使用产品的场景。

不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改。

展示至少 2 个使用场景：{scene_type}。每个场景配简短文字标注（如"商务通勤"、"周末休闲"），文字清晰可读。场景真实自然，产品使用效果清晰。

尺寸 1024×1536px 竖版。不指定具体排版。

注意：这张图不显示价格。"""

# 详情图 05-售后保障图：
DETAIL_IMAGE_05_PROMPT = """用这张白底图做一张淘宝详情图，竖版 1024×1536。以淘宝运营专家视角设计。

这是售后保障图，目标是消除用户购买顾虑，促成下单。

不允许修改白底图的任何细节，产品的外观、颜色、形状、材质、结构、所有视觉特征必须 100% 还原白底图，一字不改。

展示售后保障信息：7 天无理由退换、正品保证、破损包赔、全国包邮。纯信息排版，这张图里不出现商品。文字清晰，营造信任感。

尺寸 1024×1536px 竖版。不指定具体排版。

注意：这张图不显示价格。"""

# 5 张图的具体内容：
#
# | 图号 | 功能 | 核心目标 | 动态内容示例 |
# |:---|:---|:---|:---|
# | 01 | 首屏焦点图 | 3 秒内抓住注意力 | 按价格带：低客单突出"超值价/捡漏感"，高客单突出"品质/匠心" |
# | 02 | 对比卖点图 | 通过对比展示优势 | 按类目选对比维度（服装=面料/鞋靴=舒适度/数码=性能） |
# | 03 | 工艺细节图 | 展示做工和品质 | 4 个特写细节（面料/走线/接口/工艺），纯细节无商品 |
# | 04 | 场景展示图 | 让用户想象使用场景 | 按类目选场景（女装=穿搭/鞋靴=上脚/数码=使用），至少 2 个场景 |
# | 05 | 售后保障图 | 消除顾虑促成下单 | 7 天退换/正品保证/破损包赔/全国包邮，纯信息无商品 |

# ═══════════════════════════════════════════════════════════════════════════════
# 四、API 调用规范
# ═══════════════════════════════════════════════════════════════════════════════

# 配置：
# - 完整 API URL：https://api.henng.cn/v1/images/edits
# - model: gpt-image-2
# - 参数：images: [{"image_url": "data:image/png;base64,..."}]（是 images 数组，不是 image 单个）
# - 尺寸：主图 1024×1024，详情图 1024×1536
# - n: 1（每次一张，避免费用浪费）

API_URL = "https://api.henng.cn/v1/images/edits"
MODEL = "gpt-image-2"

def encode_image(image_path):
    """读取白底图转 base64"""
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{image_data}"

def generate_image(prompt, image_path, size="1024x1024", timeout=120):
    """调用 API 生成单张图片"""
    api_key = get_api_key()
    if not api_key:
        raise ValueError("API Key 未配置，请先设置 HENNG_API_KEY 环境变量")
    
    image_base64 = encode_image(image_path)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [{"image_url": image_base64}],  # 注意是 images 数组，不是 image 单个
        "size": size,
        "n": 1  # 每次一张，避免费用浪费
    }
    
    # 发送请求
    response = requests.post(API_URL, json=payload, headers=headers, timeout=timeout)
    
    if response.status_code != 200:
        error_data = response.json() if response.text else {}
        error_msg = error_data.get('error', {}).get('message', response.text)
        
        # 常见错误处理
        if any(x in error_msg for x in ['USAGE_LIMIT_EXCEEDED', 'DAILY_LIMIT_EXCEEDED', 'API_KEY_QUOTA_EXHAUSTED', '额度已用完']):
            raise ValueError(f"API Key 额度用完，需更换 Key 或等次日刷新。{RECHARGE_MSG}")
        elif 'upstream_error' in error_msg:
            raise ValueError(f"upstream_error：通常是尺寸不对（800×800 会报错）或接口不对（用 generations 会报错）。错误：{error_msg}")
        else:
            raise ValueError(f"API调用失败：{error_msg}")
    
    result = response.json()
    return result['data'][0]['b64_json']

def save_base64_image(b64_data, output_path):
    """解码保存 base64 图片"""
    img_data = base64.b64decode(b64_data)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(img_data)
    return output_path

# ═══════════════════════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════════════════════

def generate_ecommerce_images(
    image_path: str,
    product_name: str,
    color: str,
    original_price: float,
    current_price: float,
    selling_points: str = "",
    pain_points: str = "",
    solutions: str = "",
    details: str = "",
    scenes: str = "",
    category: str = "",
    progress_callback=None
) -> dict:
    """
    生成电商商品图（5主图+5详情图）
    
    参数:
        image_path: 白底图路径
        product_name: 商品名称
        color: 颜色/特征
        original_price: 原价
        current_price: 现价
        selling_points: 核心卖点（可选）
        pain_points: 痛点（可选）
        solutions: 解决方案（可选）
        details: 细节（可选）
        scenes: 场景（可选）
        category: 类目（可选，如女装/鞋靴等）
        progress_callback: 进度回调函数(当前步, 总步数, 描述)
    
    返回:
        {
            "status": "success/error",
            "folder_path": "保存路径",
            "main_images": [主图路径列表],
            "detail_images": [详情图路径列表],
            "message": "提示信息"
        }
    """
    
    # 检查 API Key
    if not get_api_key():
        return {
            "status": "error",
            "message": "API Key 未配置，请先设置 HENNG_API_KEY 环境变量"
        }
    
    # 检查图片是否存在
    if not os.path.exists(image_path):
        return {
            "status": "error",
            "message": f"白底图不存在：{image_path}"
        }
    
    # 创建文件夹结构
    # 描述图制作/
    # └── {商品名称}-{颜色/特征}/
    #     ├── 白底图/
    #     ├── 主图/
    #     └── 详情图/
    folders = create_folder_structure(product_name, color)
    
    # 复制白底图
    copy_white_image(image_path, folders['white'])
    
    # 获取类目信息
    # 重要：动态映射表是"常见类目示例"，不是"穷举限制"。
    # 遇到表里没有的类目，Agent 必须自主推理，通过参数传入场景/对比维度/细节点
    cat_info = get_category_info(category) if category else None
    
    # 如果表里没有该类目，且 Agent 没有传入对应参数，给出明确提示
    if cat_info is None and category:
        # Agent 传入了 category 但表里没有，必须自主推理
        pass  # 让下面的逻辑使用传入的参数或默认值
    
    price_strategy = get_price_strategy(current_price)
    
    # 准备参数：传入的参数优先级 > 类目表默认值 > 通用默认值
    # 这样 Agent 可以自主推理并覆盖任何值
    params = {
        'product_name': product_name,
        'original_price': original_price,
        'current_price': current_price,
        'selling_points': selling_points or '高品质、舒适',
        'pain_points': pain_points or '质量差、不舒服、不耐用',
        'solutions': solutions or '精选材质、人体工学设计、严格质检',
        'details': details or (cat_info['details'] if cat_info else ['细节1', '细节2', '细节3', '细节4']),
        'scenes': scenes or (cat_info['scene'] if cat_info else '真人使用场景：日常使用'),
        'price_strategy': price_strategy,
        'comparison_dimension': cat_info['comparison'] if cat_info else '品质对比',
        'detail_points': '、'.join(cat_info['details'] if cat_info else (details.split('、') if details else ['细节1', '细节2', '细节3', '细节4'])),
        'scene_type': scenes or (cat_info['scene'] if cat_info else '真人使用场景：日常使用')
    }
    
    result = {
        "status": "success",
        "folder_path": folders['base'],
        "main_images": [],
        "detail_images": [],
        "message": ""
    }
    
    total_steps = 10
    current_step = 0
    
    # 生成5张主图
    # | 序号 | 文件名 | 功能 | 核心目标 |
    # |:---|:---|:---|:---|
    # | 01 | 主图 01-促销首图 | 点击率 | 抓眼球，促点击 |
    # | 02 | 主图 02-痛点解决 | 转化率 | 解决顾虑 |
    # | 03 | 主图 03-设计细节 | 差异化 | 展示卖点 |
    # | 04 | 主图 04-场景穿搭 | 购买欲 | 代入感 |
    # | 05 | 主图 05-白底图 | 平台权重 | 活动报名 |
    main_prompts = [
        ('01', '主图 01-促销首图.png', MAIN_IMAGE_01_PROMPT),
        ('02', '主图 02-痛点解决图.png', MAIN_IMAGE_02_PROMPT),
        ('03', '主图 03-设计细节图.png', MAIN_IMAGE_03_PROMPT),
        ('04', '主图 04-场景穿搭图.png', MAIN_IMAGE_04_PROMPT),
        ('05', '主图 05-白底图.png', MAIN_IMAGE_05_PROMPT),
    ]
    
    for i, (key, name, prompt_template) in enumerate(main_prompts, 1):
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, f"生成主图 {i}/5: {name}")
        
        try:
            prompt = prompt_template.format(**params)
            # 使用 https://api.henng.cn/v1/images/edits 接口
            # 尺寸：主图 1024×1024
            # n: 1（每次一张，避免费用浪费）
            b64_data = generate_image(prompt, image_path, size="1024x1024")
            output_path = os.path.join(folders['main'], name)
            save_base64_image(b64_data, output_path)
            result['main_images'].append(output_path)
        except Exception as e:
            error_msg = str(e)
            if '额度用完' in error_msg:
                return {"status": "error", "message": error_msg}
            return {"status": "error", "message": f"生成主图 {name} 失败: {error_msg}"}
    
    # 生成5张详情图
    # | 图号 | 功能 | 核心目标 | 动态内容示例 |
    # |:---|:---|:---|:---|
    # | 01 | 首屏焦点图 | 3 秒内抓住注意力 | 按价格带：低客单突出"超值价/捡漏感"，高客单突出"品质/匠心" |
    # | 02 | 对比卖点图 | 通过对比展示优势 | 按类目选对比维度（服装=面料/鞋靴=舒适度/数码=性能） |
    # | 03 | 工艺细节图 | 展示做工和品质 | 4 个特写细节（面料/走线/接口/工艺），纯细节无商品 |
    # | 04 | 场景展示图 | 让用户想象使用场景 | 按类目选场景（女装=穿搭/鞋靴=上脚/数码=使用），至少 2 个场景 |
    # | 05 | 售后保障图 | 消除顾虑促成下单 | 7 天退换/正品保证/破损包赔/全国包邮，纯信息无商品 |
    detail_prompts = [
        ('01', '01-首屏焦点.png', DETAIL_IMAGE_01_PROMPT),
        ('02', '02-对比卖点.png', DETAIL_IMAGE_02_PROMPT),
        ('03', '03-工艺细节.png', DETAIL_IMAGE_03_PROMPT),
        ('04', '04-场景展示.png', DETAIL_IMAGE_04_PROMPT),
        ('05', '05-尺码售后.png', DETAIL_IMAGE_05_PROMPT),
    ]
    
    for i, (key, name, prompt_template) in enumerate(detail_prompts, 1):
        current_step += 1
        if progress_callback:
            progress_callback(current_step, total_steps, f"生成详情图 {i}/5: {name}")
        
        try:
            prompt = prompt_template.format(**params)
            # 使用 https://api.henng.cn/v1/images/edits 接口
            # 尺寸：详情图 1024×1536
            # n: 1（每次一张，避免费用浪费）
            b64_data = generate_image(prompt, image_path, size="1024x1536")
            output_path = os.path.join(folders['detail'], name)
            save_base64_image(b64_data, output_path)
            result['detail_images'].append(output_path)
        except Exception as e:
            error_msg = str(e)
            if '额度用完' in error_msg:
                return {"status": "error", "message": error_msg}
            return {"status": "error", "message": f"生成详情图 {name} 失败: {error_msg}"}
    
    result['message'] = f"""✅ 生成完成！
📁 保存位置：{folders['base']}
🖼️ 主图：5张（促销首图、痛点解决、设计细节、场景穿搭、白底图）
🖼️ 详情图：5张（首屏焦点、对比卖点、工艺细节、场景展示、尺码售后）

文件夹结构：
描述图制作/
└── {product_name}-{color}/
    ├── 白底图/
    ├── 主图/
    └── 详情图/"""
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════════════════════════════════════

def generate(
    image_path: str,
    product_name: str,
    color: str,
    original_price: float,
    current_price: float,
    **kwargs
) -> str:
    """
    简化版生成函数，返回字符串结果
    
    示例:
        generate("白底图.jpg", "天丝套装", "米色", 299, 159, category="女装")
    """
    result = generate_ecommerce_images(
        image_path=image_path,
        product_name=product_name,
        color=color,
        original_price=original_price,
        current_price=current_price,
        **kwargs
    )
    
    if result['status'] == 'error':
        return f"❌ 错误：{result['message']}"
    
    return result['message']

# ═══════════════════════════════════════════════════════════════════════════════
# 插件注册（OpenClaw / Hermes 兼容）
# ═══════════════════════════════════════════════════════════════════════════════

PLUGIN_INFO = {
    "name": "电商图片生成工具",
    "version": "1.0.0",
    "description": "自动生成淘宝商品主图和详情图（5主图+5详情图）。完整实现《电商图片生成使用说明（完整版）》的所有规范。",
    "author": "nulifeiyu001",
    "functions": [
        {
            "name": "generate_ecommerce_images",
            "description": "生成一套电商商品图（5主图+5详情图），保存到桌面/描述图制作/",
            "parameters": {
                "image_path": "白底图文件路径",
                "product_name": "商品名称",
                "color": "颜色或特征",
                "original_price": "原价",
                "current_price": "现价",
                "selling_points": "核心卖点（可选）",
                "pain_points": "痛点（可选）",
                "solutions": "解决方案（可选）",
                "details": "细节（可选）",
                "scenes": "场景（可选）",
                "category": "类目（可选，如女装/鞋靴/箱包/数码等）"
            }
        },
        {
            "name": "generate",
            "description": "简化版生成函数，返回字符串结果",
            "parameters": {
                "image_path": "白底图文件路径",
                "product_name": "商品名称",
                "color": "颜色或特征",
                "original_price": "原价",
                "current_price": "现价"
            }
        },
        {
            "name": "set_api_key",
            "description": "设置 API Key（同时写入环境变量和配置文件）",
            "parameters": {
                "key": "API Key 字符串"
            }
        },
        {
            "name": "get_api_key",
            "description": "获取当前 API Key",
            "parameters": {}
        }
    ]
}

def register_plugin():
    """注册插件信息"""
    return PLUGIN_INFO

# 兼容直接导入
__all__ = [
    'generate_ecommerce_images',
    'generate',
    'set_api_key',
    'get_api_key',
    'register_plugin',
    'PLUGIN_INFO',
    'RECHARGE_MSG'
]
