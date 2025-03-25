import sqlite3
import os
import pandas as pd

class Database:
    def __init__(self, db_path='accounts.db'):
        """初始化数据库连接"""
        self.db_path = db_path
        self.conn = None
        self.initial_fields = ['ID', 'IP', 'web3账号', '统一密码', '谷歌账号', '推特账号', 
                              'discord账号', '个人邮箱', '充值地址OK', '备用谷歌邮箱账号', 
                              'discord账号2FA', '推特账号2FA']
        self.init_db()

    def connect(self):
        """连接数据库"""
        self.conn = sqlite3.connect(self.db_path)
        return self.conn.cursor()

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_db(self):
        """初始化数据库表"""
        # 检查数据库文件是否存在
        db_exists = os.path.exists(self.db_path)
        cursor = self.connect()
        
        if not db_exists:
            print("创建新数据库...")
            # 如果是新数据库，创建表并添加初始字段
            self.create_accounts_table(cursor)
            self.create_fields_table(cursor)
            
            # 添加初始字段 - 直接处理而不是通过add_field方法
            for field in self.initial_fields:
                if field != 'ID':  # ID是主键，不在字段表中
                    # 检查字段是否已存在
                    cursor.execute('SELECT COUNT(*) FROM fields WHERE field_name = ?', (field,))
                    if cursor.fetchone()[0] == 0:
                        # 添加字段到字段表
                        is_2fa = '2FA' in field  # 自动判断是否为2FA字段
                        print(f"添加字段: {field}，2FA标记: {is_2fa}")
                        cursor.execute('INSERT INTO fields (field_name, is_2fa) VALUES (?, ?)', 
                                    (field, 1 if is_2fa else 0))
                        
                        # 向accounts表添加新列
                        try:
                            cursor.execute(f'ALTER TABLE accounts ADD COLUMN "{field}" TEXT')
                        except sqlite3.OperationalError:
                            # 如果列已存在，忽略错误
                            pass
        else:
            print("检查现有数据库...")
            # 已存在的数据库，确保所有2FA相关字段都被正确标记
            cursor.execute('SELECT field_name FROM fields WHERE field_name LIKE "%2FA%"')
            fa_field_names = [row[0] for row in cursor.fetchall()]
            
            cursor.execute('SELECT field_name FROM fields WHERE is_2fa = 1')
            marked_fa_fields = [row[0] for row in cursor.fetchall()]
            
            # 查找包含2FA但未标记的字段
            for field in fa_field_names:
                if field not in marked_fa_fields:
                    print(f"标记字段 '{field}' 为2FA字段")
                    cursor.execute('UPDATE fields SET is_2fa = 1 WHERE field_name = ?', (field,))
        
        # 提交更改并关闭连接
        self.conn.commit()
        self.close()

    def create_accounts_table(self, cursor):
        """创建账号表"""
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            ID TEXT PRIMARY KEY
        )
        ''')

    def create_fields_table(self, cursor):
        """创建字段表"""
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS fields (
            field_name TEXT PRIMARY KEY,
            is_2fa INTEGER DEFAULT 0
        )
        ''')

    def get_all_fields(self):
        """获取所有字段"""
        cursor = self.connect()
        cursor.execute('SELECT field_name FROM fields ORDER BY rowid')
        fields = [row[0] for row in cursor.fetchall()]
        self.close()
        return ['ID'] + fields

    def get_2fa_fields(self):
        """获取所有2FA字段"""
        cursor = self.connect()
        cursor.execute('SELECT field_name FROM fields WHERE is_2fa = 1')
        fields = [row[0] for row in cursor.fetchall()]
        
        # 调试输出
        print(f"数据库中的2FA字段: {fields}")
        
        # 如果没有找到2FA字段，检查是否有字段名包含"2FA"但未正确标记
        if not fields:
            cursor.execute('SELECT field_name FROM fields WHERE field_name LIKE "%2FA%"')
            potential_fields = [row[0] for row in cursor.fetchall()]
            if potential_fields:
                print(f"发现可能的2FA字段未正确标记: {potential_fields}")
                # 自动修正
                for field in potential_fields:
                    print(f"自动标记字段 '{field}' 为2FA字段")
                    self.set_field_2fa(field, True)
                # 重新获取
                cursor.execute('SELECT field_name FROM fields WHERE is_2fa = 1')
                fields = [row[0] for row in cursor.fetchall()]
                print(f"更新后的2FA字段: {fields}")
        
        self.close()
        return fields

    def add_field(self, field_name, is_2fa=0):
        """添加新字段"""
        if field_name == 'ID':
            return False  # ID是主键，不能作为普通字段添加
        
        cursor = self.connect()
        # 检查字段是否已存在
        cursor.execute('SELECT COUNT(*) FROM fields WHERE field_name = ?', (field_name,))
        if cursor.fetchone()[0] > 0:
            self.close()
            return False
        
        # 添加字段到字段表
        cursor.execute('INSERT INTO fields (field_name, is_2fa) VALUES (?, ?)', 
                      (field_name, 1 if is_2fa else 0))
        
        # 向accounts表添加新列
        try:
            cursor.execute(f'ALTER TABLE accounts ADD COLUMN "{field_name}" TEXT')
        except sqlite3.OperationalError:
            # 如果列已存在，忽略错误
            pass
        
        self.conn.commit()
        self.close()
        return True

    def remove_field(self, field_name):
        """删除字段"""
        if field_name == 'ID':
            return False  # ID是主键，不能删除
        
        cursor = self.connect()
        # 从字段表中删除
        cursor.execute('DELETE FROM fields WHERE field_name = ?', (field_name,))
        
        # SQLite不直接支持删除列，需要创建新表并复制数据
        fields = self.get_all_fields()
        if field_name in fields:
            fields.remove(field_name)
            
            # 创建新表
            fields_str = ', '.join([f'"{f}" TEXT' for f in fields])
            cursor.execute(f'CREATE TABLE new_accounts ({fields_str}, PRIMARY KEY(ID))')
            
            # 复制数据
            copy_fields = ', '.join([f'"{f}"' for f in fields])
            cursor.execute(f'INSERT INTO new_accounts ({copy_fields}) SELECT {copy_fields} FROM accounts')
            
            # 替换旧表
            cursor.execute('DROP TABLE accounts')
            cursor.execute('ALTER TABLE new_accounts RENAME TO accounts')
        
        self.conn.commit()
        self.close()
        return True

    def add_account(self, account_data):
        """添加新账号"""
        if 'ID' not in account_data or not account_data['ID']:
            return False  # ID是必需的
        
        cursor = self.connect()
        # 检查ID是否已存在
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE ID = ?', (account_data['ID'],))
        if cursor.fetchone()[0] > 0:
            self.close()
            return False
        
        # 准备SQL语句
        fields = []
        values = []
        params = []
        
        for field, value in account_data.items():
            fields.append(f'"{field}"')
            values.append('?')
            params.append(value)
        
        sql = f'INSERT INTO accounts ({", ".join(fields)}) VALUES ({", ".join(values)})'
        cursor.execute(sql, params)
        self.conn.commit()
        self.close()
        return True

    def update_account(self, account_data):
        """更新账号信息"""
        if 'ID' not in account_data or not account_data['ID']:
            return False  # ID是必需的
        
        cursor = self.connect()
        # 检查ID是否存在
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE ID = ?', (account_data['ID'],))
        if cursor.fetchone()[0] == 0:
            self.close()
            return False
        
        # 准备SQL语句
        update_parts = []
        params = []
        
        for field, value in account_data.items():
            if field != 'ID':  # 不更新ID
                update_parts.append(f'"{field}" = ?')
                params.append(value)
        
        params.append(account_data['ID'])  # WHERE子句的参数
        
        sql = f'UPDATE accounts SET {", ".join(update_parts)} WHERE ID = ?'
        cursor.execute(sql, params)
        self.conn.commit()
        self.close()
        return True

    def query_accounts(self, ids):
        """根据ID列表查询账号信息"""
        if not ids:
            return []
        
        cursor = self.connect()
        placeholders = ', '.join(['?' for _ in ids])
        sql = f'SELECT * FROM accounts WHERE ID IN ({placeholders})'
        cursor.execute(sql, ids)
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            account = {}
            for i, value in enumerate(row):
                account[columns[i]] = value
            results.append(account)
        
        self.close()
        return results

    def get_all_accounts(self):
        """获取所有账号信息"""
        cursor = self.connect()
        cursor.execute('SELECT * FROM accounts')
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            account = {}
            for i, value in enumerate(row):
                account[columns[i]] = value
            results.append(account)
        
        self.close()
        return results

    def import_from_excel(self, file_path):
        """从Excel导入数据"""
        try:
            df = pd.read_excel(file_path)
            
            # 确保必须的列存在
            if 'ID' not in df.columns:
                return False, "Excel文件必须包含ID列"
            
            # 获取现有字段
            existing_fields = self.get_all_fields()
            
            # 添加Excel中的新字段
            for col in df.columns:
                if col not in existing_fields:
                    is_2fa = '2FA' in col  # 自动判断是否为2FA字段
                    self.add_field(col, is_2fa)
            
            # 导入数据
            success_count = 0
            fail_count = 0
            
            for _, row in df.iterrows():
                account_data = {}
                for col in df.columns:
                    value = row[col]
                    # 处理NaN值
                    if pd.isna(value):
                        value = ""
                    account_data[col] = str(value)
                
                if self.add_account(account_data):
                    success_count += 1
                else:
                    fail_count += 1
            
            return True, f"导入完成: {success_count}个成功, {fail_count}个失败"
        
        except Exception as e:
            return False, f"导入错误: {str(e)}"

    def set_field_2fa(self, field_name, is_2fa):
        """设置字段是否为2FA字段"""
        cursor = self.connect()
        cursor.execute('UPDATE fields SET is_2fa = ? WHERE field_name = ?', 
                      (1 if is_2fa else 0, field_name))
        self.conn.commit()
        self.close()
        return True 