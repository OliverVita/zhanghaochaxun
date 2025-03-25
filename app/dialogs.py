from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                           QPushButton, QFileDialog, QMessageBox, QFormLayout,
                           QCheckBox, QGroupBox, QScrollArea, QWidget, QComboBox)
from PyQt5.QtCore import Qt

class AddFieldDialog(QDialog):
    """添加字段对话框"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("添加字段")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 字段名输入
        form_layout = QFormLayout()
        self.field_name_edit = QLineEdit()
        form_layout.addRow("字段名称:", self.field_name_edit)
        
        # 2FA字段复选框
        self.is_2fa_check = QCheckBox("此字段为2FA字段")
        form_layout.addRow("", self.is_2fa_check)
        
        layout.addLayout(form_layout)
        
        # 按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        confirm_btn = QPushButton("确认")
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept_add_field)
    
    def accept_add_field(self):
        field_name = self.field_name_edit.text().strip()
        if not field_name:
            QMessageBox.warning(self, "错误", "字段名不能为空")
            return
        
        is_2fa = self.is_2fa_check.isChecked()
        
        if self.db.add_field(field_name, is_2fa):
            QMessageBox.information(self, "成功", f"字段 '{field_name}' 添加成功")
            self.accept()
        else:
            QMessageBox.warning(self, "错误", f"字段 '{field_name}' 添加失败，可能已存在")


class AddAccountDialog(QDialog):
    """添加账号对话框"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.fields = self.db.get_all_fields()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("添加账号")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 创建滚动区域以容纳字段表单
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        form_layout = QFormLayout(scroll_content)
        
        # 创建各字段的输入框
        self.field_inputs = {}
        for field in self.fields:
            input_field = QLineEdit()
            if field == 'ID':
                input_field.setPlaceholderText("必填")
            self.field_inputs[field] = input_field
            form_layout.addRow(f"{field}:", input_field)
        
        layout.addWidget(scroll)
        
        # 按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        confirm_btn = QPushButton("确认")
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept_add_account)
    
    def accept_add_account(self):
        # 收集数据
        account_data = {}
        for field, input_field in self.field_inputs.items():
            value = input_field.text().strip()
            if field == 'ID' and not value:
                QMessageBox.warning(self, "错误", "ID不能为空")
                return
            account_data[field] = value
        
        # 添加账号
        if self.db.add_account(account_data):
            QMessageBox.information(self, "成功", f"账号 '{account_data['ID']}' 添加成功")
            self.accept()
        else:
            QMessageBox.warning(self, "错误", f"账号添加失败，ID可能已存在")


class EditAccountDialog(QDialog):
    """编辑账号对话框"""
    def __init__(self, db, account_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.account_data = account_data
        self.fields = self.db.get_all_fields()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"编辑账号 - {self.account_data.get('ID', '')}")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 创建滚动区域以容纳字段表单
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        form_layout = QFormLayout(scroll_content)
        
        # 创建各字段的输入框
        self.field_inputs = {}
        for field in self.fields:
            input_field = QLineEdit()
            input_field.setText(self.account_data.get(field, ""))
            if field == 'ID':
                input_field.setReadOnly(True)  # ID不可修改
            self.field_inputs[field] = input_field
            form_layout.addRow(f"{field}:", input_field)
        
        layout.addWidget(scroll)
        
        # 按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        confirm_btn = QPushButton("确认")
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.confirm_edit)
    
    def confirm_edit(self):
        # 收集数据
        updated_data = {}
        for field, input_field in self.field_inputs.items():
            value = input_field.text().strip()
            updated_data[field] = value
        
        # 显示确认对话框
        confirm = ConfirmDialog(updated_data, self)
        if confirm.exec_() == QDialog.Accepted:
            # 更新账号
            if self.db.update_account(updated_data):
                QMessageBox.information(self, "成功", f"账号 '{updated_data['ID']}' 更新成功")
                self.accept()
            else:
                QMessageBox.warning(self, "错误", "账号更新失败")


class ImportDialog(QDialog):
    """导入对话框"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.file_path = ""
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("从Excel导入账号")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # 文件选择部分
        file_layout = QHBoxLayout()
        self.file_label = QLabel("未选择文件")
        file_layout.addWidget(self.file_label, 1)
        
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)
        
        layout.addLayout(file_layout)
        
        # 导入说明
        info_label = QLabel(
            "Excel文件的第一行必须包含字段名，且必须有ID列。\n"
            "如果Excel中包含新字段，将自动添加到系统中。\n"
            "导入时会自动识别带有'2FA'的字段名为2FA字段。"
        )
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        import_btn = QPushButton("导入")
        import_btn.setEnabled(False)
        self.import_btn = import_btn
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(import_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        cancel_btn.clicked.connect(self.reject)
        import_btn.clicked.connect(self.import_excel)
    
    def browse_file(self):
        """选择Excel文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(file_path)
            self.import_btn.setEnabled(True)
    
    def import_excel(self):
        """导入Excel"""
        if not self.file_path:
            QMessageBox.warning(self, "错误", "请先选择Excel文件")
            return
        
        success, message = self.db.import_from_excel(self.file_path)
        if success:
            QMessageBox.information(self, "导入结果", message)
            self.accept()
        else:
            QMessageBox.warning(self, "导入失败", message)


class ConfirmDialog(QDialog):
    """修改确认对话框"""
    def __init__(self, account_data, parent=None):
        super().__init__(parent)
        self.account_data = account_data
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("确认修改")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 提示文本
        prompt = QLabel("请确认以下修改:")
        prompt.setAlignment(Qt.AlignCenter)
        layout.addWidget(prompt)
        
        # 数据预览
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        data_layout = QFormLayout(scroll_content)
        
        for field, value in self.account_data.items():
            data_layout.addRow(f"{field}:", QLabel(value))
        
        layout.addWidget(scroll)
        
        # 按钮
        button_layout = QHBoxLayout()
        cancel_btn = QPushButton("取消")
        confirm_btn = QPushButton("确认")
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        cancel_btn.clicked.connect(self.reject)
        confirm_btn.clicked.connect(self.accept) 