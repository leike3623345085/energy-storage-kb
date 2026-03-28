#!/usr/bin/env python3
"""
紧急清理飞书 Bitable 旧记录 - 修复版
"""
import requests
import time

FEISHU_CONFIG = {
    "app_id": "cli_a934994591785cb3",
    "app_secret": "uBiJm9Xuv6xsNWHdAOq6Hgovp82mrItY",
    "bitable_app_token": "Pqpwbh5tkaSzdrsKvrhcfggVnGe",
    "tables": {
        "crawler": "tblbWZx9H76QpxCl",
        "search": "tblXS2e1FDVJlJ6m",
        "stocks": "tblKruLIh89NgNNL",
        "reports": "tbla0u1wX7kLQJ09"
    }
}

class FeishuCleaner:
    def __init__(self):
        self.access_token = None
        
    def get_access_token(self):
        if self.access_token:
            return self.access_token
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": FEISHU_CONFIG["app_id"],
            "app_secret": FEISHU_CONFIG["app_secret"]
        }
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        result = resp.json()
        if result.get("code") == 0:
            self.access_token = result["tenant_access_token"]
            return self.access_token
        return None
    
    def get_record_count(self, table_id):
        """获取表格记录数"""
        token = self.get_access_token()
        if not token:
            return 0
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"page_size": 1}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)
            result = resp.json()
            if result.get("code") == 0:
                return result.get("data", {}).get("total", 0)
            return 0
        except:
            return 0
    
    def get_all_records(self, table_id):
        """获取所有记录ID"""
        token = self.get_access_token()
        if not token:
            return []
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records"
        headers = {"Authorization": f"Bearer {token}"}
        
        all_records = []
        page_token = None
        
        while True:
            params = {"page_size": 500}
            if page_token:
                params["page_token"] = page_token
            
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=10)
                result = resp.json()
                
                if result.get("code") != 0:
                    print(f"   ⚠️ 获取失败: {result.get('msg')}")
                    break
                
                items = result.get("data", {}).get("items", [])
                all_records.extend(items)
                
                # 检查是否有更多页
                page_token = result.get("data", {}).get("page_token")
                if not page_token or not items:
                    break
                    
            except Exception as e:
                print(f"   ⚠️ 错误: {e}")
                break
        
        return all_records
    
    def delete_record(self, table_id, record_id):
        """删除单条记录"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{FEISHU_CONFIG['bitable_app_token']}/tables/{table_id}/records/{record_id}"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            resp = requests.delete(url, headers=headers, timeout=5)
            return resp.json().get("code") == 0
        except Exception as e:
            return False
    
    def clean_table(self, table_name, table_id, keep_count=15000):
        """清理表格，保留指定数量记录"""
        print(f"\n🧹 清理表格: {table_name} ({table_id})")
        
        # 获取当前记录数
        total = self.get_record_count(table_id)
        print(f"   当前记录数: {total}")
        
        if total <= keep_count:
            print(f"   ✅ 无需清理")
            return 0
        
        need_delete = total - keep_count
        print(f"   目标保留: {keep_count}, 需要删除: {need_delete} 条")
        
        # 获取所有记录
        print(f"   📥 正在获取所有记录...")
        records = self.get_all_records(table_id)
        print(f"   📊 获取到 {len(records)} 条记录")
        
        if len(records) <= keep_count:
            print(f"   ✅ 记录数符合要求")
            return 0
        
        # 删除多余的记录（保留最新的）
        to_delete = records[:-keep_count] if keep_count > 0 else records
        deleted = 0
        
        print(f"   🗑️ 开始删除 {len(to_delete)} 条记录...")
        for i, record in enumerate(to_delete, 1):
            record_id = record.get("record_id")
            if record_id:
                if self.delete_record(table_id, record_id):
                    deleted += 1
                if i % 100 == 0:
                    print(f"      进度: {i}/{len(to_delete)}")
            time.sleep(0.02)
        
        print(f"   ✅ 完成，已删除 {deleted}/{len(to_delete)} 条")
        return deleted

if __name__ == "__main__":
    cleaner = FeishuCleaner()
    
    # 清理爬虫数据表（目标保留15000条）
    cleaner.clean_table("crawler", FEISHU_CONFIG["tables"]["crawler"], 15000)
    
    # 清理搜索数据表（目标保留5000条）
    cleaner.clean_table("search", FEISHU_CONFIG["tables"]["search"], 5000)
    
    print("\n🎉 清理完成")
