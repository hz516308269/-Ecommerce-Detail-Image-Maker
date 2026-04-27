#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商详情图制作 - Agent 更新脚本
Ecommerce Detail Image Maker - Agent Update Script

此脚本供 Agent 读取，由 Agent 决定是否执行更新
This script is for Agent to read and decide whether to update
"""

import os
import json
import requests
import shutil

# 配置 / Configuration
GITHUB_USER = "hz516308269"
REPO_NAME = "-Ecommerce-Detail-Image-Maker"
REMOTE_PROMPTS_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/prompts/prompts.json"
REMOTE_CONFIG_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/config/latest.json"

LOCAL_PROMPTS_PATH = os.path.join(os.path.dirname(__file__), "prompts.json")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), ".backup")


def get_local_prompts_version():
    """获取本地 prompts.json 版本"""
    if os.path.exists(LOCAL_PROMPTS_PATH):
        try:
            with open(LOCAL_PROMPTS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('version', '0.0.0')
        except:
            return '0.0.0'
    return '0.0.0'


def get_remote_prompts_version():
    """获取远程 prompts.json 版本"""
    try:
        response = requests.get(REMOTE_CONFIG_URL, timeout=10)
        if response.status_code == 200:
            config = response.json()
            return config.get('version', '0.0.0')
    except Exception as e:
        return None
    return None


def check_update():
    """
    检查是否有更新
    Check if update is available
    
    返回 / Returns:
        {
            "has_update": True/False,
            "local_version": "1.0.0",
            "remote_version": "1.1.0",
            "changelog": "更新内容",
            "action": "prompt_agent_to_decide"  # 提示 Agent 决定
        }
    """
    local_version = get_local_prompts_version()
    remote_version = get_remote_prompts_version()
    
    if remote_version is None:
        return {
            "has_update": False,
            "error": "无法获取远程版本信息"
        }
    
    # 简单版本比较
    def parse_version(v):
        return [int(x) for x in v.split('.')]
    
    has_update = False
    try:
        local_parts = parse_version(local_version)
        remote_parts = parse_version(remote_version)
        for i in range(max(len(local_parts), len(remote_parts))):
            l = local_parts[i] if i < len(local_parts) else 0
            r = remote_parts[i] if i < len(remote_parts) else 0
            if r > l:
                has_update = True
                break
            elif r < l:
                break
    except:
        pass
    
    return {
        "has_update": has_update,
        "local_version": local_version,
        "remote_version": remote_version,
        "changelog": "请查看 GitHub 仓库获取更新日志",
        "action": "prompt_agent_to_decide",
        "message": f"本地版本: {local_version}, 远程版本: {remote_version}" + ("\n有可用更新，是否更新？" if has_update else "\n当前已是最新版本。")
    }


def download_prompts():
    """
    下载远程 prompts.json
    Download remote prompts.json
    
    返回 / Returns:
        {"status": "success/error", "message": "..."}
    """
    try:
        response = requests.get(REMOTE_PROMPTS_URL, timeout=30)
        if response.status_code == 200:
            # 备份旧版本
            if os.path.exists(LOCAL_PROMPTS_PATH):
                os.makedirs(BACKUP_DIR, exist_ok=True)
                backup_path = os.path.join(BACKUP_DIR, f"prompts_{get_local_prompts_version()}.json")
                shutil.copy2(LOCAL_PROMPTS_PATH, backup_path)
            
            # 保存新版本
            with open(LOCAL_PROMPTS_PATH, 'w', encoding='utf-8') as f:
                json.dump(response.json(), f, ensure_ascii=False, indent=2)
            
            return {
                "status": "success",
                "message": f"prompts.json 已更新到最新版本"
            }
        else:
            return {
                "status": "error",
                "message": f"下载失败，HTTP {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"更新失败: {str(e)}"
        }


def update_info_for_agent():
    """
    供 Agent 读取的更新信息
    Update info for Agent to read
    
    Agent 应该：
    1. 调用 check_update() 检查是否有更新
    2. 如果有更新，询问用户是否更新
    3. 用户确认后，调用 download_prompts() 执行更新
    """
    return {
        "plugin_name": "电商详情图制作 / Ecommerce Detail Image Maker",
        "current_version": get_local_prompts_version(),
        "remote_url": f"https://github.com/{GITHUB_USER}/{REPO_NAME}",
        "check_update_function": "check_update()",
        "update_function": "download_prompts()",
        "description": "此脚本供 Agent 读取，由 Agent 决定是否执行更新",
        "description_en": "This script is for Agent to read and decide whether to update"
    }


# Agent 可直接读取的信息
AGENT_UPDATE_INFO = update_info_for_agent()

if __name__ == "__main__":
    # 测试
    print("=" * 50)
    print("电商详情图制作 - 更新脚本")
    print("=" * 50)
    print()
    
    info = check_update()
    print(json.dumps(info, ensure_ascii=False, indent=2))
