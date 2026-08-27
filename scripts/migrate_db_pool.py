#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量迁移脚本：将所有 Go 文件中的 db.Pool.* 调用替换为 db.GlobalDBManager.*
确保文件使用 UTF-8 编码
"""
import os
import re
from pathlib import Path

# 需要处理的目录
TARGET_DIRS = [
    "internal/api",
    "internal/billing",
]

# 替换规则
REPLACEMENTS = [
    (r'db\.Pool\.Exec\(', 'db.GlobalDBManager.Exec('),
    (r'db\.Pool\.QueryRow\(', 'db.GlobalDBManager.QueryRow('),
    (r'db\.Pool\.Query\(', 'db.GlobalDBManager.Query('),
    (r'db\.Pool\.Begin\(', 'db.GlobalDBManager.Begin('),
    (r'db\.ReadPool\(\)\.', 'db.GlobalDBManager.'),  # ReadPool() 也统一走 Manager
]

def migrate_file(file_path):
    """迁移单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replaced_count = 0
        
        for pattern, replacement in REPLACEMENTS:
            matches = len(re.findall(pattern, content))
            if matches > 0:
                content = re.sub(pattern, replacement, content)
                replaced_count += matches
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return replaced_count
        return 0
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0

def main():
    project_root = Path(__file__).parent.parent
    total_replacements = 0
    files_processed = 0
    
    for target_dir in TARGET_DIRS:
        dir_path = project_root / target_dir
        if not dir_path.exists():
            print(f"Directory not found: {dir_path}")
            continue
        
        for go_file in dir_path.rglob("*.go"):
            count = migrate_file(str(go_file))
            if count > 0:
                print(f"[OK] {go_file.relative_to(project_root)}: {count} replacements")
                total_replacements += count
                files_processed += 1
    
    print(f"\n[COMPLETE] Migration completed!")
    print(f"   Files processed: {files_processed}")
    print(f"   Total replacements: {total_replacements}")

if __name__ == "__main__":
    main()
