#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商图片生成插件 - 更新模块
支持从 GitHub/Gitee 远程更新 Prompt 模板
"""

import os
import json
import requests

# 远程配置地址
REMOTE_CONFIG_URL = "https://raw.githubusercontent.com/hz516308269/-Ecommerce-Detail-Image-Maker/main/config/latest.json"

# 本地版本
LOCAL_VERSION = "1.0.0"

def check_update():
    """
    检查是否有新版本
    
    返回:
        {
            "has_update": True/False,
            "latest_version": "1.1.0",
            "changelog": "更新内容",
            "download_url": "https://..."
        }
    """
    try:
        response = requests.get(REMOTE_CONFIG_URL, timeout=10)
        if response.status_code == 200:
            remote_config = response.json()
            latest_version = remote_config.get('version', LOCAL_VERSION)
            
            # 简单版本比较
            has_update = _version_compare(latest_version, LOCAL_VERSION) > 0
            
            return {
                "has_update": has_update,
                "latest_version": latest_version,
                "changelog": remote_config.get('changelog', ''),
                "download_url": remote_config.get('url', '')
            }
    except Exception as e:
        return {
            "has_update": False,
            "error": f"检查更新失败: {str(e)}"
        }
    
    return {"has_update": False}

def _version_compare(v1, v2):
    """比较版本号"""
    def parse(v):
        return [int(x) for x in v.split('.')]
    
    a, b = parse(v1), parse(v2)
    for i in range(max(len(a), len(b))):
        x = a[i] if i < len(a) else 0
        y = b[i] if i < len(b) else 0
        if x > y:
            return 1
        elif x < y:
            return -1
    return 0

def update_prompts():
    """
    从远程拉取最新 Prompt 模板
    
    返回:
        {
            "status": "success/error",
            "message": "提示信息"
        }
    """
    try:
        # 这里可以实现从远程拉取 prompts.json
        # 暂时返回本地已是最新
        return {
            "status": "success",
            "message": "当前已是最新版本"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"更新失败: {str(e)}"
        }

# 导出函数
__all__ = ['check_update', 'update_prompts']
