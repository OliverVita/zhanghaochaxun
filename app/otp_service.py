import requests
import re
import json
import queue
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, pyqtSlot

class OTPWorker(QThread):
    """OTP查询工作线程"""
    otp_result = pyqtSignal(str, str, str, int)  # 账号ID, 字段名, OTP码, 剩余时间
    request_completed = pyqtSignal()  # 请求完成信号
    
    def __init__(self, url, account_id, field_name, parent=None):
        super().__init__(parent)
        self.url = url
        self.account_id = account_id
        self.field_name = field_name
        
    def run(self):
        """执行OTP请求"""
        try:
            print(f"工作线程请求OTP: {self.url} 账号: {self.account_id}")
            response = requests.get(self.url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("ok") and "data" in data:
                    otp = data["data"].get("otp", "")
                    time_remaining = int(data["data"].get("timeRemaining", 0))
                    
                    # 发送结果信号
                    self.otp_result.emit(self.account_id, self.field_name, otp, time_remaining)
                    print(f"成功获取OTP: 账号={self.account_id}, 字段={self.field_name}")
                else:
                    # API返回错误
                    print(f"API返回错误: {data}")
            else:
                print(f"API请求失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"OTP请求异常: {str(e)}")
        
        # 无论成功失败，都发出完成信号
        self.request_completed.emit()


class OTPService(QObject):
    """2FA验证码服务"""
    otp_updated = pyqtSignal(str, str, str, int)  # 账号ID, 字段名, OTP码, 剩余时间
    otp_request_started = pyqtSignal(str, str)  # 账号ID, 字段名 - 请求开始信号
    request_completed = pyqtSignal()  # 请求完成信号，用于串行处理
    
    def __init__(self):
        super().__init__()
        self.timers = {}  # (账号ID, 字段名) -> QTimer
        self.otp_data = {}  # (账号ID, 字段名) -> (OTP码, 剩余时间)
        self.request_queue = queue.Queue()  # 请求队列
        self.is_processing = False  # 是否正在处理请求
        self.workers = []  # 工作线程列表
        
        # 并行查询设置
        self.is_parallel = False  # 是否使用并行模式
        self.max_parallel = None  # 最大并行查询数量（None表示不限制）
        self.active_requests = 0  # 当前活动请求数量
        
        # 连接请求完成信号
        self.request_completed.connect(self.process_next_request)
    
    def set_query_mode(self, is_parallel=False, max_parallel=None):
        """设置查询模式"""
        self.is_parallel = is_parallel
        self.max_parallel = max_parallel if max_parallel and max_parallel > 0 else None
        print(f"设置查询模式: {'并行' if is_parallel else '串行'}, 最大并行数: {max_parallel if max_parallel else '不限'}")
        
        # 重置请求计数
        self.active_requests = 0
    
    def extract_key_from_2fa_text(self, text):
        """从2FA文本中提取密钥"""
        if not text:
            return None
        
        print(f"正在解析2FA文本: {text}")  # 调试输出
        
        # 尝试匹配完整URL格式 - 支持多种大小写和数字组合
        url_patterns = [
            r'https://2fa\.fb\.rip/([A-Za-z0-9]+)',
            r'https://2fa\.fb\.rip/([a-z0-9]+)',
            r'https://2fa\.fb\.rip/([A-Z0-9]+)'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, text)
            if match:
                key = match.group(1)
                print(f"从完整URL匹配到密钥: {key}")
                return key
            
        # 尝试匹配简短格式
        short_patterns = [
            r'2fa\.fb\.rip/([A-Za-z0-9]+)',
            r'2fa\.fb\.rip/([a-z0-9]+)',
            r'2fa\.fb\.rip/([A-Z0-9]+)'
        ]
        
        for pattern in short_patterns:
            match = re.search(pattern, text)
            if match:
                key = match.group(1)
                print(f"从简短格式匹配到密钥: {key}")
                return key
        
        # 如果是纯字母数字，可能就是密钥本身
        clean_text = text.strip()
        if clean_text.isalnum():
            print(f"文本本身可能是密钥: {clean_text}")
            return clean_text
            
        print(f"无法从文本中提取密钥: {text}")
        return None
    
    def queue_otp_request(self, account_id, field_name, key):
        """将OTP请求加入队列"""
        print(f"将请求加入队列: 账号={account_id}, 字段={field_name}, 密钥={key}")
        self.request_queue.put((account_id, field_name, key))
        
        # 如果当前没有正在处理的请求，开始处理
        if not self.is_processing:
            self.process_next_request()
        else:
            # 发出请求开始信号（显示"查询中..."）
            self.otp_request_started.emit(account_id, field_name)
    
    @pyqtSlot()
    def process_next_request(self):
        """处理队列中的下一个请求"""
        # 如果队列为空，标记为不处理状态
        if self.request_queue.empty():
            self.is_processing = False
            return
        
        # 串行模式时，仅处理一个请求
        if not self.is_parallel:
            # 标记为正在处理
            self.is_processing = True
            
            # 获取下一个请求
            account_id, field_name, key = self.request_queue.get()
            print(f"正在处理队列中的请求(串行): 账号={account_id}, 字段={field_name}, 密钥={key}")
            
            # 发出请求开始信号（显示"查询中..."）
            self.otp_request_started.emit(account_id, field_name)
            
            # 执行OTP获取（异步）
            self.get_otp_async(account_id, field_name, key)
        else:
            # 并行模式，处理多个请求
            self.is_processing = True
            
            # 计算可处理的请求数
            if self.max_parallel is not None:
                max_to_process = max(0, self.max_parallel - self.active_requests)
            else:
                # 处理队列中的所有请求
                max_to_process = self.request_queue.qsize()
            
            print(f"并行处理下一批请求，数量: {max_to_process}，当前活动请求: {self.active_requests}")
            
            # 处理请求
            for _ in range(max_to_process):
                if self.request_queue.empty():
                    break
                
                # 获取下一个请求
                account_id, field_name, key = self.request_queue.get()
                print(f"正在处理队列中的请求(并行): 账号={account_id}, 字段={field_name}, 密钥={key}")
                
                # 发出请求开始信号（显示"查询中..."）
                self.otp_request_started.emit(account_id, field_name)
                
                # 执行OTP获取（异步）
                self.get_otp_async(account_id, field_name, key)
                
                # 增加活动请求计数
                self.active_requests += 1
    
    def get_otp_async(self, account_id, field_name, key):
        """异步获取OTP验证码"""
        if not key:
            self.request_completed.emit()
            return
        
        print(f"开始异步获取OTP: 账号={account_id}, 字段={field_name}, 密钥={key}")
        
        # 创建URL
        url = f"https://2fa.fb.rip/api/otp/{key}"
        
        # 创建并启动工作线程
        worker = OTPWorker(url, account_id, field_name, self)
        
        # 连接信号
        worker.otp_result.connect(self.handle_otp_result)
        worker.request_completed.connect(lambda: self.handle_worker_completed(worker))
        
        # 保存并启动工作线程
        self.workers.append(worker)
        worker.start()
    
    def handle_otp_result(self, account_id, field_name, otp, time_remaining):
        """处理OTP结果"""
        key = (account_id, field_name)
        
        # 保存OTP数据
        self.otp_data[key] = (otp, time_remaining)
        
        # 发出信号
        self.otp_updated.emit(account_id, field_name, otp, time_remaining)
        
        # 设置计时器
        self.setup_timer(account_id, field_name, otp, time_remaining)
    
    def handle_worker_completed(self, worker):
        """处理工作线程完成"""
        # 从列表中移除工作线程
        if worker in self.workers:
            self.workers.remove(worker)
            worker.deleteLater()
        
        # 减少活动请求计数（并行模式）
        if self.is_parallel:
            self.active_requests = max(0, self.active_requests - 1)
        
        # 继续处理队列中的下一个请求
        QTimer.singleShot(1000, self.request_completed.emit)  # 延迟1秒再处理下一个，避免请求过快
    
    def get_otp(self, account_id, field_name, key):
        """获取OTP验证码（已弃用，保留兼容性）"""
        print("警告: 使用了同步API方法，建议使用异步方法")
        self.get_otp_async(account_id, field_name, key)
    
    def setup_timer(self, account_id, field_name, otp, time_remaining):
        """设置计时器"""
        key = (account_id, field_name)
        
        # 如果已经有计时器，先停止
        if key in self.timers:
            self.timers[key].stop()
        
        # 创建新计时器
        timer = QTimer(self)
        self.timers[key] = timer
        
        # 计时器计数
        count = [time_remaining]
        
        def update_countdown():
            count[0] -= 1
            if count[0] <= 0:
                # 时间到，重新获取OTP
                timer.stop()
                self.queue_otp_request(account_id, field_name, self.extract_key_from_2fa_text(self._get_original_key(account_id, field_name)))
            else:
                # 更新OTP数据和发出信号
                if key in self.otp_data:
                    otp_val, _ = self.otp_data[key]
                    self.otp_data[key] = (otp_val, count[0])
                    self.otp_updated.emit(account_id, field_name, otp_val, count[0])
        
        # 连接信号槽并启动计时器
        timer.timeout.connect(update_countdown)
        timer.start(1000)  # 每秒触发一次
    
    def _get_original_key(self, account_id, field_name):
        """从原始数据源获取密钥文本（需要子类实现）"""
        # 此方法需要主窗口提供
        return ""
    
    def stop_all_timers(self):
        """停止所有计时器"""
        for timer in self.timers.values():
            timer.stop()
        self.timers.clear()
        self.otp_data.clear()
        self.is_processing = False  # 停止处理
        self.active_requests = 0   # 重置活动请求计数
        
        # 停止所有工作线程
        for worker in self.workers:
            worker.terminate()
            worker.wait()
            worker.deleteLater()
        self.workers.clear()
        
        # 清空队列
        while not self.request_queue.empty():
            try:
                self.request_queue.get_nowait()
            except queue.Empty:
                break 