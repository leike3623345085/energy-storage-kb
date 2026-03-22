: 2025
    for file in files[:max_files]:
        file_path = os.path.join(data_dir, file)
        
        # 检查是否已同步（通过飞书文件名判断）
        feishu_filename = f"储能_{file}"
        if feishu_filename in existing_files:
            print(f"  ⏭️ 已同步: {feishu_filename}")
            continue
        
        # 同步到飞书
        print(f"  📤 同步中: {file} → {feishu_filename}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 上传为飞书文档
        result = subprocess.run(
            ['openclaw', 'feishu', 'doc', 'create', 
             '--title', feishu_filename.replace('.md', ''),
             '--content', content],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            synced_count += 1
            print(f"  ✅ 同步成功: {feishu_filename}")
        else:
            print(f"  ❌ 同步失败: {result.stderr}")
    
    print(f"\n📊 同步完成: {synced_count}/{max_files} 个文件")
    return synced_count

if __name__ == "__main__":
    sync_to_feishu(max_files=5)
EOF