import sqlite3
import os
from datetime import datetime

class FabDB:
    def __init__(self, db_path="fab_data.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        """获取数据库连接 (Get Connection)"""
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """初始化表结构 (Init Table Schema)"""
        with self._get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fab_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fab_uid TEXT UNIQUE NOT NULL,       -- 资源唯一UID
                    is_acquired INTEGER DEFAULT 0,       -- 购买状态: 0 未入库, 1 已入库
                    offer_id_1 TEXT,                    -- 第一个 OfferID
                    offer_id_2 TEXT,                    -- 备用 OfferID
                    retry_count INTEGER DEFAULT 0,       -- 购买重试次数
                    last_error TEXT,                     -- 错误日志记录
                    created_at DATETIME,                -- 采集时间
                    updated_at DATETIME,                -- 最后更新时间
                    acquired_at DATETIME                -- 成功购买/入库时间
                )
            ''')
            # 索引优化 (Indexes for performance)
            conn.execute('CREATE INDEX IF NOT EXISTS idx_uid ON fab_assets(fab_uid)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_acquired ON fab_assets(is_acquired)')
            conn.commit()

    def add_uids(self, uids):
        """
        批量插入 UID (Batch Insert)
        返回: (实际新增数量, 已存在的数量)
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        inserted_count = 0
        exist_count = 0
        
        with self._get_conn() as conn:
            for uid in uids:
                try:
                    # 使用 INSERT OR IGNORE 配合 rowcount 判断
                    cursor = conn.execute('''
                        INSERT OR IGNORE INTO fab_assets (fab_uid, created_at, updated_at) 
                        VALUES (?, ?, ?)
                    ''', (uid, now, now))
                    
                    if cursor.rowcount > 0:
                        inserted_count += 1
                    else:
                        exist_count += 1
                except sqlite3.Error:
                    exist_count += 1
            conn.commit()
            
        return inserted_count, exist_count

    def update_asset(self, uid, **kwargs):
        """
        通用更新方法 (Universal Update)
        用法: db.update_asset(uid, is_acquired=1, offer_id_1='xxx')
        """
        if not kwargs:
            return
        
        kwargs['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 动态构建 SQL
        keys = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(uid) # WHERE 条件的占位符值
        
        sql = f"UPDATE fab_assets SET {keys} WHERE fab_uid = ?"
        
        with self._get_conn() as conn:
            conn.execute(sql, values)
            conn.commit()

    def get_unacquired_assets(self):
        """获取所有未购买的 UID"""
        with self._get_conn() as conn:
            cursor = conn.execute('SELECT fab_uid FROM fab_assets WHERE is_acquired = 0')
            return [row[0] for row in cursor.fetchall()]

    def get_stats(self):
        """获取简单的统计信息 (Get Statistics)"""
        with self._get_conn() as conn:
            total = conn.execute('SELECT COUNT(*) FROM fab_assets').fetchone()[0]
            acquired = conn.execute('SELECT COUNT(*) FROM fab_assets WHERE is_acquired = 1').fetchone()[0]
            return {"total": total, "acquired": acquired, "pending": total - acquired}

# 全局单例初始化
db = FabDB()

if __name__ == "__main__":
    # 简单的自我测试
    print("[*] 正在初始化数据库并测试...")
    stats = db.get_stats()
    print(f"[*] 当前库内存量: {stats['total']} | 已入库: {stats['acquired']}")