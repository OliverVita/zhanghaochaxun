import os
import re
import collections  # 用于队列处理
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QPushButton, QTabWidget, 
                           QTableWidget, QTableWidgetItem, QHeaderView, 
                           QMessageBox, QFileDialog, QDialog, QFormLayout,
                           QCheckBox, QGroupBox, QSplitter, QApplication,
                           QTextEdit, QComboBox, QScrollArea, QFrame, QGridLayout,
                           QInputDialog, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot, QEvent, QObject, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QKeySequence, QIntValidator

from app.database import Database
from app.otp_service import OTPService
from app.main_window_otp import MainWindowOTPService
from app.dialogs import (AddFieldDialog, AddAccountDialog, EditAccountDialog, 
                       ImportDialog, ConfirmDialog)

# 自定义表格类，处理鼠标事件
class CustomTableWidget(QTableWidget):
    """自定义表格控件，正确处理鼠标事件和双击事件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_selection = None
        
    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            # 获取点击的单元格位置
            pos = event.pos()
            item = self.itemAt(pos)
            if item:
                # 记录起始选择位置
                self.start_selection = (item.row(), item.column())
                # 清除之前的选择
                self.clearSelection()
                # 选择当前单元格
                item.setSelected(True)
        # 确保调用原始的mousePressEvent方法，以便正确处理双击
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        if self.start_selection:
            # 获取当前鼠标位置对应的单元格
            pos = event.pos()
            item = self.itemAt(pos)
            if item:
                # 获取起始和结束位置
                start_row, start_col = self.start_selection
                end_row, end_col = item.row(), item.column()
                
                # 清除之前的选择
                self.clearSelection()
                
                # 选择范围内的所有单元格
                for row in range(min(start_row, end_row), max(start_row, end_row) + 1):
                    for col in range(min(start_col, end_col), max(start_col, end_col) + 1):
                        item = self.item(row, col)
                        if item:
                            item.setSelected(True)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        self.start_selection = None
        super().mouseReleaseEvent(event)

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置窗口标题和大小
        self.setWindowTitle("账号查询工具")
        self.setMinimumSize(1000, 600)
        
        # 初始化数据库连接
        self.db = Database('accounts.db')
        
        # 存储查询结果，用于关联账号ID和行号
        self.query_results = []  # 保存完整的查询结果数据
        
        # 初始化OTP服务 - 使用自定义子类
        self.otp_service = MainWindowOTPService(self)
        self.otp_service.otp_updated.connect(self.update_otp_display)
        self.otp_service.otp_request_started.connect(self.show_otp_loading)
        
        # 创建状态栏，用于显示消息
        self.statusBar().showMessage("就绪", 2000)
        
        # 创建UI
        self.setup_ui()
    
    def setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("账号查询系统")
        self.setMinimumSize(1000, 700)
        
        # 设置主窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                background-color: white;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #4a86e8;
            }
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #e1e1e1;
                padding: 8px;
                border: none;
                border-right: 1px solid #ccc;
            }
        """)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 创建标题标签
        title_label = QLabel("账号查询系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title_label)
        
        # 添加作者信息标签
        author_label = QLabel("by:Neuer")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("""
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(author_label)
        
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 创建查询选项卡
        self.create_query_tab()
        
        # 创建管理选项卡
        self.create_manage_tab()
        
        # 显示窗口
        self.setGeometry(100, 100, 1200, 800)
        self.show()
    
    def create_query_tab(self):
        """创建查询选项卡"""
        query_tab = QWidget()
        self.tab_widget.addTab(query_tab, "账号查询")
        
        # 创建布局
        layout = QVBoxLayout(query_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建查询输入部分
        input_group = QGroupBox("请输入要查询的ID")
        input_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        input_layout = QVBoxLayout(input_group)
        
        # 查询输入框
        self.query_input = QTextEdit()
        self.query_input.setPlaceholderText("请输入ID，多个ID可用空格、逗号或换行分隔")
        self.query_input.setMaximumHeight(80)
        input_layout.addWidget(self.query_input)
        
        # 创建一个水平布局用于2FA选项和字段选择按钮
        options_layout = QHBoxLayout()
        
        # 2FA开关
        self.enable_2fa_check = QCheckBox("启用2FA自动查询")
        self.enable_2fa_check.setChecked(True)
        options_layout.addWidget(self.enable_2fa_check)
        
        # 创建2FA查询模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("查询模式:")
        mode_layout.addWidget(mode_label)
        
        self.query_mode_combo = QComboBox()
        self.query_mode_combo.addItem("串行查询")
        self.query_mode_combo.addItem("并行查询")
        self.query_mode_combo.currentIndexChanged.connect(self.on_query_mode_changed)
        mode_layout.addWidget(self.query_mode_combo)
        
        # 并行数量输入框
        self.parallel_count_label = QLabel("并行数量:")
        mode_layout.addWidget(self.parallel_count_label)
        
        self.parallel_count_input = QLineEdit()
        self.parallel_count_input.setPlaceholderText("默认全部")
        self.parallel_count_input.setMaximumWidth(80)
        self.parallel_count_input.setValidator(QIntValidator(1, 100))  # 限制输入1-100之间的整数
        mode_layout.addWidget(self.parallel_count_input)
        
        # 初始设置为串行模式
        self.parallel_count_label.setVisible(False)
        self.parallel_count_input.setVisible(False)
        
        options_layout.addLayout(mode_layout)
        
        # 停止2FA查询按钮
        self.stop_2fa_btn = QPushButton("停止2FA查询")
        self.stop_2fa_btn.clicked.connect(self.stop_2fa_queries)
        self.stop_2fa_btn.setEnabled(False)  # 初始状态禁用
        self.stop_2fa_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        options_layout.addWidget(self.stop_2fa_btn)
        
        # 字段选择按钮
        field_select_btn = QPushButton("选择显示字段")
        field_select_btn.clicked.connect(self.show_field_select_dialog)
        options_layout.addWidget(field_select_btn)
        
        # 添加水平布局到主布局
        input_layout.addLayout(options_layout)
        
        # 查询按钮
        query_button = QPushButton("查询")
        query_button.setMinimumHeight(40)
        query_button.clicked.connect(self.perform_query)
        input_layout.addWidget(query_button)
        
        layout.addWidget(input_group)
        
        # 创建结果显示部分
        results_group = QGroupBox("查询结果")
        results_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        results_layout = QVBoxLayout(results_group)
        
        # 添加结果排序控件
        sort_layout = QHBoxLayout()
        sort_label = QLabel("结果排序:")
        sort_layout.addWidget(sort_label)
        
        # ID升序排序按钮
        id_asc_btn = QPushButton("ID ↑")
        id_asc_btn.setToolTip("按ID从小到大排序")
        id_asc_btn.clicked.connect(lambda: self.sort_results_by_id(False))
        sort_layout.addWidget(id_asc_btn)
        
        # ID降序排序按钮
        id_desc_btn = QPushButton("ID ↓")
        id_desc_btn.setToolTip("按ID从大到小排序")
        id_desc_btn.clicked.connect(lambda: self.sort_results_by_id(True))
        sort_layout.addWidget(id_desc_btn)
        
        # 添加弹性空间
        sort_layout.addStretch()
        
        results_layout.addLayout(sort_layout)
        
        # 结果表格
        self.results_table = CustomTableWidget()
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 修改选择模式为扩展选择
        self.results_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.results_table.setSelectionBehavior(QTableWidget.SelectItems)  # 改为选择单元格
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        
        # 启用表格排序功能
        self.results_table.setSortingEnabled(True)
        
        # 添加复制功能
        self.results_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_results_context_menu)
        self.results_table.installEventFilter(self)
        
        # 添加双击复制功能
        self.results_table.cellDoubleClicked.connect(self.copy_cell_content)
        
        results_layout.addWidget(self.results_table)
        
        layout.addWidget(results_group, 1)  # 结果区域占据更多空间
        
        # 初始化字段选择状态
        self.selected_fields = []  # 用户选择的字段
        self.update_field_selection()  # 初始化选择所有字段
    
    def update_field_selection(self):
        """更新字段选择状态，如果为空则选择所有字段"""
        all_fields = self.db.get_all_fields()
        if not self.selected_fields:
            self.selected_fields = all_fields.copy()
    
    def create_manage_tab(self):
        """创建管理选项卡"""
        manage_tab = QWidget()
        self.tab_widget.addTab(manage_tab, "管理")
        
        # 创建布局
        layout = QVBoxLayout(manage_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 创建功能分区
        functions_layout = QGridLayout()
        functions_layout.setSpacing(15)
        
        # 添加账号功能区
        add_account_group = QGroupBox("添加账号")
        add_account_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        add_account_layout = QVBoxLayout(add_account_group)
        
        # 手动添加按钮
        add_manual_btn = QPushButton("手动添加账号")
        add_manual_btn.clicked.connect(self.show_add_account_dialog)
        add_account_layout.addWidget(add_manual_btn)
        
        # 导入Excel按钮
        import_excel_btn = QPushButton("从Excel导入账号")
        import_excel_btn.clicked.connect(self.show_import_dialog)
        add_account_layout.addWidget(import_excel_btn)
        
        functions_layout.addWidget(add_account_group, 0, 0)
        
        # 字段管理功能区
        field_group = QGroupBox("字段管理")
        field_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        field_layout = QVBoxLayout(field_group)
        
        # 添加字段按钮
        add_field_btn = QPushButton("添加字段")
        add_field_btn.clicked.connect(self.show_add_field_dialog)
        field_layout.addWidget(add_field_btn)
        
        # 删除字段按钮
        remove_field_btn = QPushButton("删除字段")
        remove_field_btn.clicked.connect(self.show_remove_field_dialog)
        field_layout.addWidget(remove_field_btn)
        
        functions_layout.addWidget(field_group, 0, 1)
        
        # 修改账号功能区
        edit_account_group = QGroupBox("修改账号")
        edit_account_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        edit_account_layout = QVBoxLayout(edit_account_group)
        
        # ID输入
        id_layout = QHBoxLayout()
        id_layout.addWidget(QLabel("账号ID:"))
        self.edit_id_input = QLineEdit()
        self.edit_id_input.setPlaceholderText("请输入要修改的账号ID")
        id_layout.addWidget(self.edit_id_input)
        edit_account_layout.addLayout(id_layout)
        
        # 修改按钮
        edit_btn = QPushButton("修改账号")
        edit_btn.clicked.connect(self.show_edit_account_dialog)
        edit_account_layout.addWidget(edit_btn)
        
        functions_layout.addWidget(edit_account_group, 1, 0, 1, 2)
        
        layout.addLayout(functions_layout)
        
        # 添加账号列表区域
        accounts_group = QGroupBox("所有账号")
        accounts_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        accounts_layout = QVBoxLayout(accounts_group)
        
        # 账号列表表格
        self.accounts_table = CustomTableWidget()
        self.accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accounts_table.setAlternatingRowColors(True)
        
        # 添加复制功能
        self.accounts_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounts_table.customContextMenuRequested.connect(self.show_accounts_context_menu)
        self.accounts_table.installEventFilter(self)
        
        # 添加双击复制功能
        self.accounts_table.cellDoubleClicked.connect(self.copy_cell_content)
        
        accounts_layout.addWidget(self.accounts_table)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_accounts_table)
        accounts_layout.addWidget(refresh_btn)
        
        layout.addWidget(accounts_group, 1)  # 表格区域占据更多空间
        
        # 初始加载账号列表
        self.refresh_accounts_table()
    
    def show_field_select_dialog(self):
        """显示字段选择对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("选择显示字段")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout(dialog)
        
        # 说明文字
        label = QLabel("请选择要显示的字段:")
        layout.addWidget(label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # 获取所有字段
        all_fields = self.db.get_all_fields()
        
        # 确保selected_fields包含有效的字段
        self.update_field_selection()
        
        # 创建复选框列表
        self.field_checkboxes = {}
        for field in all_fields:
            checkbox = QCheckBox(field)
            checkbox.setChecked(field in self.selected_fields)
            scroll_layout.addWidget(checkbox)
            self.field_checkboxes[field] = checkbox
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # 全选/取消全选按钮
        buttons_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all_fields)
        buttons_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all_fields)
        buttons_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(buttons_layout)
        
        # 确定和取消按钮
        button_box = QHBoxLayout()
        
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(lambda: self.apply_field_selection(dialog))
        button_box.addWidget(ok_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        button_box.addWidget(cancel_button)
        
        layout.addLayout(button_box)
        
        # 显示对话框
        dialog.exec_()
    
    def select_all_fields(self):
        """全选所有字段"""
        for checkbox in self.field_checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all_fields(self):
        """取消全选"""
        for checkbox in self.field_checkboxes.values():
            checkbox.setChecked(False)
    
    def apply_field_selection(self, dialog):
        """应用字段选择"""
        self.selected_fields = []
        for field, checkbox in self.field_checkboxes.items():
            if checkbox.isChecked():
                self.selected_fields.append(field)
        
        # 至少选择一个字段
        if not self.selected_fields:
            QMessageBox.warning(self, "警告", "请至少选择一个字段")
            return
        
        # 如果当前有查询结果，更新显示
        if self.results_table.rowCount() > 0:
            self.refresh_results_table()
        
        dialog.accept()
    
    def refresh_results_table(self):
        """根据选择的字段刷新结果表格"""
        if not self.query_results or not self.selected_fields:
            return
        
        # 备份当前的OTP数据以便重新显示
        otp_data = {}
        for col in range(self.results_table.columnCount()):
            col_header = self.results_table.horizontalHeaderItem(col).text() if self.results_table.horizontalHeaderItem(col) else ""
            if '-OTP' in col_header:
                original_field = col_header.replace('-OTP', '')
                if original_field in self.selected_fields:
                    for row in range(self.results_table.rowCount()):
                        item = self.results_table.item(row, col)
                        if item:
                            account_id = None
                            # 找到ID列
                            for c in range(self.results_table.columnCount()):
                                if self.results_table.horizontalHeaderItem(c).text() == 'ID':
                                    id_item = self.results_table.item(row, c)
                                    if id_item:
                                        account_id = id_item.text()
                                    break
                            if account_id:
                                otp_data[(account_id, original_field)] = (item.text(), item.data(Qt.UserRole))
        
        # 重新显示结果
        self.display_query_results(self.query_results)
        
        # 恢复OTP数据
        for col in range(self.results_table.columnCount()):
            col_header = self.results_table.horizontalHeaderItem(col).text() if self.results_table.horizontalHeaderItem(col) else ""
            if '-OTP' in col_header:
                original_field = col_header.replace('-OTP', '')
                for row in range(self.results_table.rowCount()):
                    account_id = None
                    # 找到ID列
                    for c in range(self.results_table.columnCount()):
                        if self.results_table.horizontalHeaderItem(c).text() == 'ID':
                            id_item = self.results_table.item(row, c)
                            if id_item:
                                account_id = id_item.text()
                            break
                    if account_id and (account_id, original_field) in otp_data:
                        display_text, otp_value = otp_data[(account_id, original_field)]
                        item = QTableWidgetItem(display_text)
                        item.setData(Qt.UserRole, otp_value)
                        if "(0s)" in display_text or "(1s)" in display_text or "(2s)" in display_text:
                            item.setForeground(QColor(255, 0, 0))
                        else:
                            item.setForeground(QColor(0, 128, 0))
                        self.results_table.setItem(row, col, item)
    
    def on_query_mode_changed(self, index):
        """查询模式改变时的处理"""
        # 如果选择并行查询模式，显示并行数量输入框
        is_parallel = index == 1
        self.parallel_count_label.setVisible(is_parallel)
        self.parallel_count_input.setVisible(is_parallel)

    def perform_query(self):
        """执行查询"""
        # 获取查询输入
        query_text = self.query_input.toPlainText().strip()
        if not query_text:
            QMessageBox.warning(self, "提示", "请输入要查询的ID")
            return
        
        # 解析ID列表（支持空格、逗号、换行分隔）
        ids = re.split(r'[\s,]+', query_text)
        ids = [id.strip() for id in ids if id.strip()]
        
        # 执行查询
        results = self.db.query_accounts(ids)
        
        # 显示结果
        self.display_query_results(results)
        
        # 如果启用了2FA，处理2FA字段
        if self.enable_2fa_check.isChecked():
            # 获取查询模式和并行数量
            is_parallel = self.query_mode_combo.currentIndex() == 1
            parallel_count = None
            if is_parallel and self.parallel_count_input.text():
                try:
                    parallel_count = int(self.parallel_count_input.text())
                    if parallel_count <= 0:
                        parallel_count = None
                except:
                    parallel_count = None
            
            # 处理2FA字段
            self.process_2fa_fields(results, is_parallel, parallel_count)
            
            # 启用停止按钮
            self.stop_2fa_btn.setEnabled(True)
            
            # 显示状态信息
            mode_text = "并行" if is_parallel else "串行"
            count_text = f"({parallel_count}个)" if is_parallel and parallel_count else ""
            self.statusBar().showMessage(f"2FA查询已启动，正在{mode_text}{count_text}获取验证码...", 3000)
    
    def display_query_results(self, results):
        """显示查询结果"""
        if not results:
            self.results_table.setRowCount(0)
            self.results_table.setColumnCount(0)
            QMessageBox.information(self, "查询结果", "未找到匹配的账号")
            return
        
        # 确保selected_fields有效
        self.update_field_selection()
        
        # 只显示选中的字段
        display_fields = self.selected_fields
        
        # 设置表格列数和列标题
        self.results_table.setColumnCount(len(display_fields))
        self.results_table.setHorizontalHeaderLabels(display_fields)
        
        # 设置表格行数
        self.results_table.setRowCount(len(results))
        
        # 填充数据
        for row, account in enumerate(results):
            for col, field in enumerate(display_fields):
                value = account.get(field, "")
                item = QTableWidgetItem(value)
                # 设置2FA字段的背景色
                if '2FA' in field and self.enable_2fa_check.isChecked():
                    item.setBackground(QColor(230, 230, 255))  # 浅蓝色背景
                self.results_table.setItem(row, col, item)
        
        # 调整列宽
        self.results_table.resizeColumnsToContents()
    
    def process_2fa_fields(self, results, is_parallel=False, parallel_count=None):
        """处理2FA字段，可选择串行或并行处理"""
        if not results:
            return
            
        # 存储查询结果，以便后续关联账号ID和OTP
        self.query_results = results
            
        # 获取所有2FA字段
        fa_fields = self.db.get_2fa_fields()
        if not fa_fields:
            print("没有找到2FA字段")
            return
            
        print(f"发现2FA字段: {fa_fields}")  # 调试信息
        
        # 停止所有当前的2FA查询
        self.otp_service.stop_all_timers()
            
        # 创建查询队列
        request_items = []
        for account in results:
            account_id = account.get('ID', '未知')
            print(f"准备处理账号ID: {account_id}的2FA字段")
            
            for field in fa_fields:
                if field in account and account[field]:
                    value = account[field]
                    key = self.otp_service.extract_key_from_2fa_text(value)
                    if key:
                        # 添加账号ID和字段名到队列项
                        request_items.append((account_id, field, key))
                        print(f"账号 {account_id} 的字段 {field} 添加到队列: 密钥={key}")
        
        # 按顺序将请求添加到队列中
        print(f"总共有 {len(request_items)} 个2FA请求")
        
        # 设置查询模式
        self.otp_service.set_query_mode(is_parallel, parallel_count)
        
        # 添加到队列
        for account_id, field, key in request_items:
            self.otp_service.queue_otp_request(account_id, field, key)
    
    def find_row_by_account_id(self, account_id):
        """根据账号ID查找表格中的行号"""
        # 遍历表格查找ID列
        id_column = -1
        for col in range(self.results_table.columnCount()):
            if self.results_table.horizontalHeaderItem(col).text() == 'ID':
                id_column = col
                break
        
        if id_column >= 0:
            # 在ID列中查找匹配的账号
            for row in range(self.results_table.rowCount()):
                item = self.results_table.item(row, id_column)
                if item and item.text() == account_id:
                    return row
        
        # 如果没找到，返回-1
        return -1
    
    def show_otp_loading(self, account_id, field_name):
        """显示OTP加载状态"""
        print(f"显示OTP加载状态: 账号={account_id}, 字段={field_name}")
        
        # 查找账号对应的行
        row = self.find_row_by_account_id(account_id)
        if row < 0:
            print(f"未找到账号 {account_id} 对应的行")
            return
        
        # 找到对应字段的列
        field_column = -1
        for col in range(self.results_table.columnCount()):
            if self.results_table.horizontalHeaderItem(col).text() == field_name:
                field_column = col
                break
        
        if field_column < 0:
            print(f"未找到字段 {field_name} 对应的列")
            return
        
        # 在字段右侧创建或更新OTP列
        otp_column = field_column + 1
        otp_col_name = f"{field_name}-OTP"
        
        # 检查OTP列是否存在，不存在则创建
        if (otp_column >= self.results_table.columnCount() or 
            self.results_table.horizontalHeaderItem(otp_column).text() != otp_col_name):
            self.results_table.insertColumn(otp_column)
            self.results_table.setHorizontalHeaderItem(
                otp_column, QTableWidgetItem(otp_col_name))
        
        # 更新OTP单元格为"查询中..."
        loading_item = QTableWidgetItem("查询中...")
        loading_item.setForeground(QColor(128, 128, 128))  # 灰色表示正在加载
        self.results_table.setItem(row, otp_column, loading_item)
    
    @pyqtSlot(str, str, str, int)
    def update_otp_display(self, account_id, field_name, otp, time_remaining):
        """更新OTP显示"""
        print(f"收到OTP更新信号: 账号={account_id}, 字段={field_name}, OTP={otp}, 时间={time_remaining}")
        
        # 查找账号对应的行
        row = self.find_row_by_account_id(account_id)
        if row < 0:
            print(f"未找到账号 {account_id} 对应的行")
            return
        
        # 找到对应字段的列
        field_column = -1
        for col in range(self.results_table.columnCount()):
            if self.results_table.horizontalHeaderItem(col).text() == field_name:
                field_column = col
                break
        
        if field_column < 0:
            print(f"未找到字段 {field_name} 对应的列")
            return
        
        # 在字段右侧创建或更新OTP列
        otp_column = field_column + 1
        otp_col_name = f"{field_name}-OTP"
        
        # 检查OTP列是否存在，不存在则创建
        if (otp_column >= self.results_table.columnCount() or 
            self.results_table.horizontalHeaderItem(otp_column).text() != otp_col_name):
            self.results_table.insertColumn(otp_column)
            self.results_table.setHorizontalHeaderItem(
                otp_column, QTableWidgetItem(otp_col_name))
        
        # 更新OTP单元格 - 使用自定义数据存储纯OTP码
        display_text = f"{otp} ({time_remaining}s)"
        print(f"更新OTP显示: {display_text} 账号ID={account_id} 行={row}")
        
        item = QTableWidgetItem(display_text)
        item.setData(Qt.UserRole, otp)  # 存储纯OTP码用于复制
        
        # 设置不同的颜色以区分过期状态
        if time_remaining < 10:
            item.setForeground(QColor(255, 0, 0))  # 红色表示即将过期
        else:
            item.setForeground(QColor(0, 128, 0))  # 绿色表示正常
        
        self.results_table.setItem(row, otp_column, item)
        
        # 确保停止按钮是启用状态（因为有活动的2FA查询）
        self.stop_2fa_btn.setEnabled(True)
    
    def show_add_field_dialog(self):
        """显示添加字段对话框"""
        dialog = AddFieldDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_accounts_table()
    
    def show_remove_field_dialog(self):
        """显示删除字段对话框"""
        # 获取所有可删除字段（排除ID）
        fields = self.db.get_all_fields()
        if 'ID' in fields:
            fields.remove('ID')
        
        if not fields:
            QMessageBox.information(self, "提示", "没有可删除的字段")
            return
        
        # 选择要删除的字段
        field, ok = QInputDialog.getItem(
            self, "删除字段", "请选择要删除的字段:", fields, 0, False)
        
        if ok and field:
            # 确认删除
            confirm = QMessageBox.question(
                self, "确认删除", f"确定要删除字段 '{field}' 吗？这将删除所有账号中的此字段数据！",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if confirm == QMessageBox.Yes:
                if self.db.remove_field(field):
                    QMessageBox.information(self, "成功", f"字段 '{field}' 已删除")
                    self.refresh_accounts_table()
                else:
                    QMessageBox.warning(self, "错误", "删除字段失败")
    
    def show_add_account_dialog(self):
        """显示添加账号对话框"""
        dialog = AddAccountDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_accounts_table()
    
    def show_edit_account_dialog(self):
        """显示编辑账号对话框"""
        account_id = self.edit_id_input.text().strip()
        if not account_id:
            # 如果未输入ID，尝试从选中的行获取
            selected_rows = self.accounts_table.selectionModel().selectedRows()
            if selected_rows:
                row = selected_rows[0].row()
                # 获取ID列索引
                id_col = 0
                for col in range(self.accounts_table.columnCount()):
                    if self.accounts_table.horizontalHeaderItem(col).text() == 'ID':
                        id_col = col
                        break
                account_id = self.accounts_table.item(row, id_col).text()
            
        if not account_id:
            QMessageBox.warning(self, "提示", "请输入要修改的账号ID或在列表中选择一行")
            return
        
        # 查询该账号信息
        results = self.db.query_accounts([account_id])
        if not results:
            QMessageBox.warning(self, "错误", f"找不到ID为 '{account_id}' 的账号")
            return
        
        # 打开编辑对话框
        dialog = EditAccountDialog(self.db, results[0], self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_accounts_table()
            # 如果当前有查询结果，刷新查询结果
            if self.results_table.rowCount() > 0:
                self.perform_query()
    
    def show_import_dialog(self):
        """显示导入对话框"""
        dialog = ImportDialog(self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_accounts_table()
    
    def refresh_accounts_table(self):
        """刷新账号列表"""
        # 获取所有账号
        accounts = self.db.get_all_accounts()
        
        # 获取所有字段
        fields = self.db.get_all_fields()
        
        # 设置表格列数和列标题
        self.accounts_table.setColumnCount(len(fields))
        self.accounts_table.setHorizontalHeaderLabels(fields)
        
        # 设置表格行数
        self.accounts_table.setRowCount(len(accounts))
        
        # 填充数据
        for row, account in enumerate(accounts):
            for col, field in enumerate(fields):
                value = account.get(field, "")
                item = QTableWidgetItem(value)
                self.accounts_table.setItem(row, col, item)
        
        # 调整列宽
        self.accounts_table.resizeColumnsToContents()
    
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        # 停止所有计时器
        self.otp_service.stop_all_timers()
        event.accept()
    
    def eventFilter(self, source, event):
        """事件过滤器，处理键盘事件"""
        if (event.type() == QEvent.KeyPress and
            event.matches(QKeySequence.Copy)):
            # 处理复制操作
            if source in [self.results_table, self.accounts_table]:
                self.copy_selection(source)
                return True
        return super().eventFilter(source, event)
    
    def copy_cell_content(self, row, column):
        """双击单元格时复制内容"""
        # 获取发送信号的表格对象
        table = self.sender()
        if not table:
            return
            
        # 调用带表格参数的方法
        self.copy_cell_content_with_table(row, column, table)
    
    def copy_cell_content_with_table(self, row, column, table):
        """带表格参数的单元格复制方法"""
        if not table:
            return
            
        item = table.item(row, column)
        if not item:
            return
            
        # 检查是否是OTP列（包含-OTP）
        header_text = table.horizontalHeaderItem(column).text() if table.horizontalHeaderItem(column) else ""
        if "OTP" in header_text and item.data(Qt.UserRole):
            # 如果是OTP列且有存储的纯OTP值，则复制纯OTP值
            text = item.data(Qt.UserRole)
        else:
            # 否则复制显示文本
            text = item.text()
            
        # 复制到剪贴板
        QApplication.clipboard().setText(text)
        
        # 显示复制成功的提示（状态栏）
        self.statusBar().showMessage(f"已复制: {text}", 2000)
        
        # 显示带有自动关闭倒计时的提示窗口
        self.show_auto_close_message(f"已复制内容到剪贴板: {text}")
    
    def show_auto_close_message(self, message, timeout=3):
        """显示自动关闭的消息窗口，带有倒计时"""
        # 创建消息框
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("复制成功")
        msg_box.setIcon(QMessageBox.Information)
        
        # 设置初始文本（带倒计时）
        msg_box.setText(f"{message}\n\n窗口将在 {timeout} 秒后自动关闭...")
        
        # 显示消息框（非模态，不阻塞）
        msg_box.setModal(False)
        msg_box.show()
        
        # 创建计时器进行倒计时
        self.close_timer = QTimer()
        self.close_timer.timeout.connect(lambda: self.update_countdown(msg_box, message, timeout))
        
        # 保存起始时间和消息框引用
        self.countdown_start_time = timeout
        self.countdown_current_time = timeout
        
        # 启动计时器（每秒更新一次）
        self.close_timer.start(1000)
    
    def update_countdown(self, msg_box, message, total_time):
        """更新倒计时文本并在时间到时关闭窗口"""
        # 减少倒计时
        self.countdown_current_time -= 1
        
        if self.countdown_current_time <= 0:
            # 时间到，关闭消息框和计时器
            self.close_timer.stop()
            msg_box.close()
        else:
            # 更新倒计时文本
            msg_box.setText(f"{message}\n\n窗口将在 {self.countdown_current_time} 秒后自动关闭...")
    
    def copy_selection(self, table):
        """复制表格选中内容"""
        selection = table.selectedIndexes()
        if not selection:
            return
            
        # 按行列整理选中的单元格
        rows = sorted(set(index.row() for index in selection))
        columns = sorted(set(index.column() for index in selection))
        
        # 构建数据矩阵
        table_data = []
        for r in rows:
            row_data = []
            for c in columns:
                try:
                    item = table.item(r, c)
                    if item is not None:
                        # 检查是否是OTP列
                        header_text = table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else ""
                        if "OTP" in header_text and item.data(Qt.UserRole):
                            # 如果是OTP列且有存储的纯OTP值，则复制纯OTP值
                            row_data.append(item.data(Qt.UserRole))
                        else:
                            row_data.append(item.text())
                    else:
                        row_data.append("")
                except:
                    row_data.append("")
            table_data.append('\t'.join(row_data))
        
        # 复制到剪贴板
        text = '\n'.join(table_data)
        QApplication.clipboard().setText(text)
        
        # 提示复制成功
        self.statusBar().showMessage(f"已复制内容到剪贴板，共{len(rows)}行{len(columns)}列", 2000)
        
        # 显示带有自动关闭倒计时的提示窗口
        self.show_auto_close_message(f"已复制内容到剪贴板，共{len(rows)}行{len(columns)}列")
        
        # 打印调试信息
        print(f"已复制内容到剪贴板，共{len(rows)}行{len(columns)}列")
    
    def show_results_context_menu(self, position):
        """显示结果表格的上下文菜单"""
        menu = QMenu()
        
        # 获取选中的单元格
        selected_items = self.results_table.selectedIndexes()
        if selected_items:
            # 单个单元格复制
            if len(selected_items) == 1:
                row = selected_items[0].row()
                column = selected_items[0].column()
                item = self.results_table.item(row, column)
                if item:
                    copy_cell_action = QAction("复制单元格", self)
                    copy_cell_action.triggered.connect(lambda: self.copy_cell_content_with_table(row, column, self.results_table))
                    menu.addAction(copy_cell_action)
            
            # 常规复制（多选）
            copy_action = QAction("复制选中内容", self)
            copy_action.triggered.connect(lambda: self.copy_selection(self.results_table))
            menu.addAction(copy_action)
            
            # 复制带标题行的选项
            copy_with_headers_action = QAction("复制(包含标题行)", self)
            copy_with_headers_action.triggered.connect(lambda: self.copy_selection_with_headers(self.results_table))
            menu.addAction(copy_with_headers_action)
            
            # 添加分隔线
            menu.addSeparator()
            
            # 按ID排序选项
            sort_asc_action = QAction("按ID从小到大排序", self)
            sort_asc_action.triggered.connect(lambda: self.sort_results_by_id(False))
            menu.addAction(sort_asc_action)
            
            sort_desc_action = QAction("按ID从大到小排序", self)
            sort_desc_action.triggered.connect(lambda: self.sort_results_by_id(True))
            menu.addAction(sort_desc_action)
        
        menu.exec_(self.results_table.mapToGlobal(position))
    
    def show_accounts_context_menu(self, position):
        """显示账号表格的上下文菜单"""
        menu = QMenu()
        
        # 获取选中的单元格
        selected_items = self.accounts_table.selectedIndexes()
        if selected_items:
            # 单个单元格复制
            if len(selected_items) == 1:
                row = selected_items[0].row()
                column = selected_items[0].column()
                item = self.accounts_table.item(row, column)
                if item:
                    copy_cell_action = QAction("复制单元格", self)
                    copy_cell_action.triggered.connect(lambda: self.copy_cell_content_with_table(row, column, self.accounts_table))
                    menu.addAction(copy_cell_action)
            
            # 常规复制（多选）
            copy_action = QAction("复制选中内容", self)
            copy_action.triggered.connect(lambda: self.copy_selection(self.accounts_table))
            menu.addAction(copy_action)
            
            # 复制带标题行的选项
            copy_with_headers_action = QAction("复制(包含标题行)", self)
            copy_with_headers_action.triggered.connect(lambda: self.copy_selection_with_headers(self.accounts_table))
            menu.addAction(copy_with_headers_action)
        
        menu.exec_(self.accounts_table.mapToGlobal(position))
    
    def copy_selection_with_headers(self, table):
        """复制表格选中内容(包含标题行)"""
        selection = table.selectedIndexes()
        if not selection:
            return
            
        # 按行列整理选中的单元格
        rows = sorted(set(index.row() for index in selection))
        columns = sorted(set(index.column() for index in selection))
        
        # 构建标题行
        header_row = []
        for c in columns:
            try:
                header_item = table.horizontalHeaderItem(c)
                if header_item is not None:
                    header_row.append(header_item.text())
                else:
                    header_row.append(f"列 {c+1}")
            except:
                header_row.append(f"列 {c+1}")
        
        # 构建数据行
        table_data = ['\t'.join(header_row)]  # 先添加标题行
        
        for r in rows:
            row_data = []
            for c in columns:
                try:
                    item = table.item(r, c)
                    if item is not None:
                        # 检查是否是OTP列
                        header_text = table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else ""
                        if "OTP" in header_text and item.data(Qt.UserRole):
                            # 如果是OTP列且有存储的纯OTP值，则复制纯OTP值
                            row_data.append(item.data(Qt.UserRole))
                        else:
                            row_data.append(item.text())
                    else:
                        row_data.append("")
                except:
                    row_data.append("")
            table_data.append('\t'.join(row_data))
        
        # 复制到剪贴板
        text = '\n'.join(table_data)
        QApplication.clipboard().setText(text)
        
        # 提示复制成功 
        self.statusBar().showMessage(f"已复制内容(包含标题行)到剪贴板，共{len(rows)}行{len(columns)}列", 2000)
        
        # 显示带有自动关闭倒计时的提示窗口
        self.show_auto_close_message(f"已复制内容(包含标题行)到剪贴板，共{len(rows)}行{len(columns)}列")
        
        # 打印调试信息
        print(f"已复制内容(包含标题行)到剪贴板:\n{text}")
    
    def mark_otp_columns_as_stopped(self):
        """将所有OTP列标记为已停止状态"""
        for col in range(self.results_table.columnCount()):
            col_header = self.results_table.horizontalHeaderItem(col).text() if self.results_table.horizontalHeaderItem(col) else ""
            if '-OTP' in col_header:
                for row in range(self.results_table.rowCount()):
                    item = self.results_table.item(row, col)
                    if item:
                        current_text = item.text()
                        if "查询中" in current_text:
                            item.setText("查询已停止")
                            item.setForeground(QColor(128, 128, 128))  # 灰色
                        elif "(" in current_text and ")" in current_text:
                            # 保留OTP码但标记为已停止
                            otp_value = item.data(Qt.UserRole)
                            item.setText(f"{otp_value} (已停止)")
                            item.setForeground(QColor(128, 128, 128))  # 灰色
    
    def stop_2fa_queries(self):
        """停止所有2FA查询"""
        # 停止所有计时器和查询队列
        self.otp_service.stop_all_timers()
        
        # 禁用停止按钮
        self.stop_2fa_btn.setEnabled(False)
        
        # 显示状态信息
        self.statusBar().showMessage("已停止所有2FA查询", 3000)
        QMessageBox.information(self, "操作成功", "已停止所有2FA查询和自动更新")
        
        # 更新OTP列，标记为已停止
        self.mark_otp_columns_as_stopped() 
    
    def sort_results_by_id(self, descending=False):
        """按ID排序查询结果"""
        import re
        
        if not self.query_results:
            return
            
        # 临时禁用排序，避免性能问题
        self.results_table.setSortingEnabled(False)
        
        # 查找ID列索引
        id_column = -1
        for col in range(self.results_table.columnCount()):
            if self.results_table.horizontalHeaderItem(col).text() == 'ID':
                id_column = col
                break
                
        if id_column < 0:
            self.statusBar().showMessage("无法找到ID列进行排序", 3000)
            self.results_table.setSortingEnabled(True)
            return
        
        # 自然排序函数，处理字母数字混合ID
        def natural_keys(account):
            id_value = account.get('ID', '0') or '0'
            
            # 尝试作为纯数字处理
            try:
                return (0, int(id_value), '')
            except ValueError:
                pass
                
            # 分解ID为字母和数字部分
            def atoi(text):
                return int(text) if text.isdigit() else text
                
            # 使用正则表达式分割ID成为字母和数字部分
            parts = re.split(r'(\d+)', id_value)
            # 转换数字部分为整数
            parts = [atoi(part) for part in parts]
            # 添加ID类型标记(1表示混合ID)
            return (1,) + tuple(parts)
            
        # 排序结果
        self.query_results.sort(key=natural_keys, reverse=descending)
            
        # 备份OTP数据
        otp_data = self.backup_otp_data()
            
        # 重新显示排序后的结果
        self.display_query_results(self.query_results)
            
        # 恢复OTP数据
        self.restore_otp_data(otp_data)
            
        # 重新开启排序功能
        self.results_table.setSortingEnabled(True)
            
        # 显示排序成功消息
        order_text = "从大到小" if descending else "从小到大"
        self.statusBar().showMessage(f"已按ID{order_text}排序完成", 3000)
    
    def backup_otp_data(self):
        """备份OTP数据"""
        otp_data = {}
        for col in range(self.results_table.columnCount()):
            col_header = self.results_table.horizontalHeaderItem(col).text() if self.results_table.horizontalHeaderItem(col) else ""
            if '-OTP' in col_header:
                original_field = col_header.replace('-OTP', '')
                for row in range(self.results_table.rowCount()):
                    item = self.results_table.item(row, col)
                    if item:
                        account_id = None
                        # 找到ID列
                        for c in range(self.results_table.columnCount()):
                            if self.results_table.horizontalHeaderItem(c).text() == 'ID':
                                id_item = self.results_table.item(row, c)
                                if id_item:
                                    account_id = id_item.text()
                                    break
                        if account_id:
                            # 保存文本和用户数据
                            otp_data[(account_id, original_field)] = {
                                'text': item.text(),
                                'otp': item.data(Qt.UserRole),
                                'color': item.foreground().color()
                            }
        return otp_data
    
    def restore_otp_data(self, otp_data):
        """恢复OTP数据"""
        for col in range(self.results_table.columnCount()):
            col_header = self.results_table.horizontalHeaderItem(col).text() if self.results_table.horizontalHeaderItem(col) else ""
            if '-OTP' in col_header:
                original_field = col_header.replace('-OTP', '')
                for row in range(self.results_table.rowCount()):
                    account_id = None
                    # 找到ID列
                    for c in range(self.results_table.columnCount()):
                        if self.results_table.horizontalHeaderItem(c).text() == 'ID':
                            id_item = self.results_table.item(row, c)
                            if id_item:
                                account_id = id_item.text()
                            break
                    
                    if account_id and (account_id, original_field) in otp_data:
                        data = otp_data[(account_id, original_field)]
                        item = QTableWidgetItem(data['text'])
                        item.setData(Qt.UserRole, data['otp'])
                        item.setForeground(data['color'])
                        self.results_table.setItem(row, col, item) 