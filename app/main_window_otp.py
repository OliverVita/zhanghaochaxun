from app.otp_service import OTPService

class MainWindowOTPService(OTPService):
    """为主窗口提供OTP服务的子类，实现获取原始密钥的方法"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
    
    def _get_original_key(self, account_id, field_name):
        """从主窗口的查询结果获取原始密钥"""
        # 在查询结果中查找对应账号的数据
        for account in self.main_window.query_results:
            if account.get('ID') == account_id:
                # 找到账号后返回对应字段的值
                return account.get(field_name, "")
        return ""
    
    def queue_otp_requests_in_parallel(self, request_items, max_parallel=None):
        """批量队列处理OTP请求（并行模式）"""
        # 设置为并行模式
        self.set_query_mode(is_parallel=True, max_parallel=max_parallel)
        
        # 添加到队列
        for account_id, field_name, key in request_items:
            self.queue_otp_request(account_id, field_name, key) 