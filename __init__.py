#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商图片生成插件 - 初始化文件
"""

from .tool import (
    generate_ecommerce_images,
    generate,
    set_api_key,
    get_api_key,
    register_plugin,
    PLUGIN_INFO,
    RECHARGE_MSG
)
from .updater import check_update, update_prompts

__version__ = "1.0.0"
__author__ = "nulifeiyu001"

# 插件入口
plugin = PLUGIN_INFO

# 导出主要功能
__all__ = [
    'generate_ecommerce_images',
    'generate',
    'set_api_key',
    'get_api_key',
    'register_plugin',
    'check_update',
    'update_prompts',
    'PLUGIN_INFO',
    'RECHARGE_MSG'
]
