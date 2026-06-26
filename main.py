import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import json
from datetime import datetime

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        
        # 获取鼠标位置
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        
        # 创建tooltip窗口
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip_window, text=self.text, 
                        background="lightyellow", relief="solid", 
                        borderwidth=1, padx=5, pady=2)
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class EldenRingTool:
    def __init__(self, ui_type="mini"):
        self.root = tk.Tk()
        self.root.title("Elden save v2.1")

        icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
        self.root.iconbitmap(icon_path)
        
        # 配置文件路径

        self.auto_save_var = tk.BooleanVar(value=False)      
        self.import_overwrite_var = tk.BooleanVar(value=True) 

        self.config_file = "config.json"
        self.config = self.load_config()

        # 从配置中加载自动保存和直接覆盖的设置
        self.auto_save_var.set(self.config.get("auto_save", False))
        self.import_overwrite_var.set(self.config.get("import_overwrite", True))
        
        # 全局变量
        self.save_path = os.path.expanduser("~\\AppData\\Roaming\\EldenRing")
        self.ensure_save_dir()   # 检查并创建存档目录
        
        # 根据ui_type选择界面版本
        if ui_type == "mini":
            self.setup_ui()
        else:
            self.setup_ui()

        self.auto_detect_paths()
        self.ensure_save_directories() # 确保存档目录存在
        self.root.after(100, self.initial_save_check)  # 延迟200ms执行
        self.root.after(200, self.initial_launch_check)  # 延迟300ms执行

    #region 程序运行
    def run(self):
        """运行程序"""
        self.root.mainloop()
    #endregion

    #region 界面构建相关函数
    def setup_ui(self):
        """设置UI界面"""
        self.root.geometry("280x330")

        # 路径显示区域
        path_frame = tk.LabelFrame(self.root, text="", padx=10, pady=5)
        path_frame.pack(fill="x", padx=10, pady=6)
        
        # 存档路径 - 第2行第0列（左对齐）
        self.save_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow", font=("Microsoft YaHei", 10, "bold"))
        self.save_label.grid(row=2, column=0, sticky="w")

        # 工具路径 - 第2行第1列
        self.tool_dir_link = tk.Label(path_frame, text="工具路径", fg="gray", cursor="hand2", font=("Microsoft YaHei", 10, "bold"))
        self.tool_dir_link.grid(row=2, column=1, padx=10, sticky="w")
        self.tool_dir_link.bind("<Button-1>", lambda e: self.open_folder(os.getcwd()))
        self.tool_dir_link.bind("<Enter>", lambda e: self.tool_dir_link.config(fg="blue"))
        self.tool_dir_link.bind("<Leave>", lambda e: self.tool_dir_link.config(fg="gray"))

        # 刷新 - 第2行第2列（右对齐）
        self.path_status_label = tk.Label(path_frame, text="刷新", fg="gray", cursor="hand2", font=("Microsoft YaHei", 10, "bold"))
        self.path_status_label.grid(row=2, column=2, sticky="e")
        self.path_status_label.bind("<Button-1>", lambda e: self.auto_detect_paths())
        self.path_status_label.bind("<Enter>", lambda e: self.path_status_label.config(fg="blue"))
        self.path_status_label.bind("<Leave>", lambda e: self.path_status_label.config(fg="gray"))

        # 配置列权重
        path_frame.grid_columnconfigure(0, weight=0)  # 左：内容宽度
        path_frame.grid_columnconfigure(1, weight=1)  # 中：弹性填充
        path_frame.grid_columnconfigure(2, weight=0)  # 右：内容宽度

        # 存档管理区域
        save_frame = tk.LabelFrame(self.root, text="", padx=10, pady=5)
        save_frame.pack(fill="x", padx=10, pady=6)

        # 使用网格布局，更紧凑
        save_inner_frame = tk.Frame(save_frame)
        save_inner_frame.pack(fill="x", padx=0, pady=0)

        # 第1行：选择存档标签
        save_row1 = tk.Frame(save_inner_frame)
        save_row1.pack(fill="x", pady=(0, 5))

        tk.Label(save_row1, text="选择存档:", width=10, anchor="w", font=("Microsoft YaHei", 10, "bold")).pack(side="left")

        # 第1行：下拉框
        save_row1_1 = tk.Frame(save_inner_frame)
        save_row1_1.pack(fill="x", pady=(0, 5))

        # 存档下拉框
        self.save_combo_var = tk.StringVar()
        self.save_combo = ttk.Combobox(save_row1_1, 
                                    textvariable=self.save_combo_var,
                                    state="readonly", width=30, font=("Microsoft YaHei", 10, "normal"))
        self.save_combo.pack(side="left", padx=0)
        self.save_combo.bind("<<ComboboxSelected>>", lambda e: self.on_save_selected())

        # 第2行：状态标签（左）和刷新按钮（右）两端对齐
        save_row2 = tk.Frame(save_inner_frame)
        save_row2.pack(fill="x", pady=(0, 0))

        # 状态标签放在左侧
        self.save_status_label = tk.Label(save_row2, 
                                        text="未选择存档", fg="gray", 
                                        font=("Microsoft YaHei", 10, "normal"))
        self.save_status_label.pack(side="left")

        # 中间的空Frame用于占据剩余空间，实现两端对齐
        tk.Frame(save_row2).pack(side="left", expand=True, fill="x")

        # 刷新链接放在右侧
        self.refresh_save_link = tk.Label(save_row2, 
                                        text="刷新",
                                        fg="gray", cursor="hand2", font=("Microsoft YaHei", 10, "bold"))
        self.refresh_save_link.pack(side="left")
        self.refresh_save_link.bind("<Button-1>", lambda e: self.refresh_save_list())
        self.refresh_save_link.bind("<Enter>", 
                                lambda e: self.refresh_save_link.config(fg="blue"))
        self.refresh_save_link.bind("<Leave>", 
                                lambda e: self.refresh_save_link.config(fg="gray"))

        # 在 save_row3 (导入导出按钮行) 上方添加
        auto_save_row = tk.Frame(save_inner_frame)
        auto_save_row.pack(fill="x", pady=(0, 5))

        auto_save_check = tk.Checkbutton(auto_save_row, text="自动保存", 
                                        variable=self.auto_save_var,
                                        command=self.toggle_auto_save,
                                        font=("Microsoft YaHei", 9, "normal"))
        auto_save_check.pack(side="left")

        # 直接覆盖复选框
        import_overwrite_check = tk.Checkbutton(auto_save_row, text="直接覆盖",
                                            variable=self.import_overwrite_var,
                                            command=self.toggle_overwite,
                                            font=("Microsoft YaHei", 9, "normal"))
        import_overwrite_check.pack(side="left", padx=(0, 15))

        # 第3行：导入存档、导出存档（在同一行）
        save_row3 = tk.Frame(save_inner_frame)
        save_row3.pack(fill="x")


        # 导入存档按钮
        tk.Button(save_row3, text="导入存档", 
                command=self.import_selected_save, width=13, font=("Microsoft YaHei", 10, "bold")).pack(side="left", padx=(0, 0))

        # 导出存档按钮 
        tk.Button(save_row3, text="导出存档", 
                command=self.export_current_save, width=13, font=("Microsoft YaHei", 10, "bold")).pack(side="right")

        # 启动游戏区域 - 放在主界面最底部
        launch_frame = tk.LabelFrame(self.root, text="", padx=10, pady=5)
        launch_frame.pack(fill="x", padx=10, pady=6)

        # 启动游戏按钮（居中）
        self.launch_btn = tk.Button(launch_frame, text="启动游戏", 
                                command=self.launch_game, 
                                state="disabled", width=30,
                                font=("Microsoft YaHei", 11, "bold"))
        self.launch_btn.pack(pady=(0, 2))

        # 刷新按钮和状态标签（在同一行，刷新靠右）
        launch_status_frame = tk.Frame(launch_frame)
        launch_status_frame.pack(fill="x")

        # 状态标签（左）
        self.launch_status_label = tk.Label(launch_status_frame, 
                                            text="",
                                            fg="gray", 
                                            font=("Microsoft YaHei", 10, "normal"))
        self.launch_status_label.pack(side="left")

        # 中间的空Frame用于占据剩余空间
        tk.Frame(launch_status_frame).pack(side="left", expand=True, fill="x")

        # 刷新链接（右）
        self.refresh_launch_link = tk.Label(launch_status_frame, 
                                            text="刷新",
                                            fg="gray", cursor="hand2", 
                                            font=("Microsoft YaHei", 10, "bold"))
        self.refresh_launch_link.pack(side="right")
        self.refresh_launch_link.bind("<Button-1>", lambda e: self.refresh_launch_status())
        self.refresh_launch_link.bind("<Enter>", 
                                    lambda e: self.refresh_launch_link.config(fg="blue"))
        self.refresh_launch_link.bind("<Leave>", 
                                    lambda e: self.refresh_launch_link.config(fg="gray"))

        # 状态栏
        self.status_bar = tk.Label(self.root, text="就绪", bd=1, 
                                  relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def status(self, message):
        """更新状态栏"""
        self.status_bar.config(text=message)
        self.root.update()
    #endregion

    #region 配置文件、目录确认、打开目录相关函数
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        """保存配置文件"""
        try:
            if hasattr(self, 'save_path'):
                self.config["save_path"] = self.save_path
            self.config["auto_save"] = self.auto_save_var.get()
            self.config["import_overwrite"] = self.import_overwrite_var.get()
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # 如果保存失败，可以在状态栏提示，或者简单地忽略
            self.status(f"保存配置失败: {str(e)}")

    def ensure_save_dir(self):
        """确保存档目录存在，如果不存在则创建"""
        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path, exist_ok=True)
                # 可以在这里记录日志或显示状态，但此时GUI可能还没完全初始化
                # 所以我们在auto_detect_paths中统一处理
                return True
            except Exception as e:
                print(f"创建存档目录失败: {e}")
                return False
        return True
    
    def open_folder(self, path):
        """打开文件夹"""
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("警告", "路径不存在！")
    #endregion
    
    #region 游戏路径相关
    def update_path_labels(self):
        """更新路径标签显示"""
        # 存档路径
        if os.path.exists(self.save_path):
            # 检查存档状态
            has_save, save_info = self.check_save_exists(self.save_path)
            if has_save:
                self.save_label.config(text=f"存档路径 ✓ (有存档)", fg="green", cursor="hand2")
            else:
                self.save_label.config(text="存档路径 ✓ (无存档)", fg="orange", cursor="hand2")
            
            if hasattr(self.save_label, 'tooltip'):
                self.save_label.tooltip = None
            self.save_label.tooltip = ToolTip(self.save_label, self.save_path)
            self.save_label.bind("<Button-1>", lambda e: self.open_folder(self.save_path))
        else:
            self.save_label.config(text="存档路径 ✗ (点击手动定位)", fg="red", cursor="hand2")
            self.save_label.bind("<Button-1>", lambda e: self.manual_locate_save())
    
    def auto_detect_paths(self):
        """自动检测存档"""
        self.status("正在检测路径...")
        # 更新路径状态标签为"正在检测..."
        # self.path_status_label.config(text="正在检测...", fg="orange")

        # 检查存档目录状态
        if self.ensure_save_dir():
            save_dir_status = "存档目录就绪"
        else:
            save_dir_status = "存档目录创建失败"
        
        # 更新UI
        # self.path_status_label.config(text="重新检测路径", fg="gray")
        self.update_path_labels()
        self.save_config()
        self.status(f"路径检测完成 - {save_dir_status}")
    
    def ensure_drive_uppercase(self, path):
        """确保Windows路径的盘符为大写"""
        if not path or len(path) < 2:
            return path
        
        # 检查是否有盘符（格式如 "c:" 或 "C:"）
        if path[1] == ':' and path[0].isalpha():
            # 将盘符转为大写
            return path[0].upper() + path[1:]
        
        return path

    def manual_locate_save(self):
        """手动定位存档路径"""
        path = filedialog.askdirectory(title="请选择存档目录")
        if path:
            self.save_path = self.ensure_drive_uppercase(path)
            self.config["save_path"] = self.save_path
            self.update_path_labels()
            self.save_config()

    def check_save_exists(self, save_dir):
        """检查存档目录是否有有效存档"""
        if not os.path.exists(save_dir):
            return False, "目录不存在"
        
        # 检查是否有任何SteamID文件夹（17位数字）
        steam_id_folders = []
        for item in os.listdir(save_dir):
            item_path = os.path.join(save_dir, item)
            if os.path.isdir(item_path) and item.isdigit() and len(item) == 17:
                # 检查文件夹内是否有ER开头的文件
                try:
                    files = os.listdir(item_path)
                    if any(f.startswith('ER') for f in files):
                        steam_id_folders.append(item)
                except (PermissionError, OSError):
                    continue
        
        if steam_id_folders:
            return True, f"{len(steam_id_folders)}个存档"
        else:
            # 检查是否有任何存档文件（直接放在目录下的ER文件）
            er_files = [f for f in os.listdir(save_dir) if f.startswith('ER')]
            if er_files:
                return True, f"{len(er_files)}个ER文件"
            else:
                return False, "无存档"
    #endregion


    #region 存档文件相关函数
    def toggle_auto_save(self):
        """切换自动保存状态"""
        if self.auto_save_var.get():
            self.status("自动保存已启用")
            # 可以在这里启动定时备份
        else:
            self.status("自动保存已禁用")
        self.save_config()

    def toggle_overwite(self):
        """切换直接覆盖状态"""
        if self.import_overwrite_var.get():
            self.status("直接覆盖已启用")
            # 可以在这里启动定时备份
        else:
            self.status("直接覆盖已禁用")
        self.save_config()

    def refresh_save_list(self):
        """刷新存档列表"""
        saves_dir = "saves"
        
        # 如果存档目录不存在，创建它
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir, exist_ok=True)
            self.save_combo['values'] = []
            self.save_combo_var.set("")  # 置空选中内容
            self.save_status_label.config(text="存档目录已创建", fg="orange")
            return
        
        # 获取所有存档文件夹
        save_folders = []
        for item in os.listdir(saves_dir):
            item_path = os.path.join(saves_dir, item)
            if os.path.isdir(item_path):
                save_folders.append(item)
        
        # 按修改时间排序（最新的在前面）
        save_folders.sort(key=lambda x: os.path.getmtime(os.path.join(saves_dir, x)), reverse=True)
        
        if save_folders:
            self.save_combo['values'] = save_folders
            self.save_combo_var.set("")  # 刷新后置空选中内容
            self.save_status_label.config(text=f"找到{len(save_folders)}个存档", fg="green")
        else:
            self.save_combo['values'] = []
            self.save_combo_var.set("")  # 置空选中内容
            self.save_status_label.config(text="无可用存档", fg="gray")

    def on_save_selected(self):
        """当选择存档时的处理"""
        selected = self.save_combo_var.get()
        
        if not selected:
            self.save_status_label.config(text="未选择存档", fg="gray")
            return
        
        saves_dir = "saves"
        selected_path = os.path.join(saves_dir, selected)
        
        # 检查存档是否合法
        is_valid, status_msg, details = self.check_save_validity(selected_path)
        
        if is_valid:
            self.save_status_label.config(text=f"存档合法", fg="green")
        else:
            self.save_status_label.config(text=f"存档异常: {status_msg}", fg="red")

    def check_save_validity(self, save_path):
        """
        检查存档的合法性
        
        Args:
            save_path: 存档文件夹路径
        
        Returns:
            tuple: (is_valid, status_message, details)
        """
        if not os.path.exists(save_path):
            return False, "存档文件夹不存在", ""
        
        # 检查存档文件夹结构
        eldenring_path = os.path.join(save_path, "EldenRing")
        
        # 两种情况：有EldenRing文件夹或直接是存档文件
        if os.path.exists(eldenring_path):
            # 情况1：有EldenRing文件夹
            return self._check_eldenring_folder(eldenring_path)
        else:
            # 情况2：直接是存档文件
            return self._check_direct_save_files(save_path)

    def _check_eldenring_folder(self, eldenring_path):
        """检查EldenRing文件夹结构"""
        if not os.path.exists(eldenring_path):
            return False, "EldenRing文件夹不存在", ""
        
        # 查找SteamID文件夹（17位数字）
        steam_id_found = False
        steam_id_folders = []
        
        for item in os.listdir(eldenring_path):
            item_path = os.path.join(eldenring_path, item)
            if os.path.isdir(item_path):
                # 检查是否是17位数字文件夹
                if item.isdigit() and len(item) == 17:
                    steam_id_found = True
                    steam_id_folders.append(item)
                    
                    # 检查文件夹内是否有ER开头的文件
                    has_er_files = any(f.startswith('ER') for f in os.listdir(item_path))
                    if not has_er_files:
                        return False, f"SteamID文件夹{item}内无ER文件", ""
        
        if not steam_id_found:
            return False, "未找到SteamID文件夹", ""
        
        # 检查GraphicsConfig.xml（可选）
        graphics_config = os.path.join(eldenring_path, "GraphicsConfig.xml")
        
        details = f"{len(steam_id_folders)}个SteamID文件夹"
        return True, "存档合法", details

    def _check_direct_save_files(self, save_path):
        """检查直接存档文件结构"""
        # 查找SteamID文件夹（17位数字）
        steam_id_found = False
        steam_id_folders = []
        
        for item in os.listdir(save_path):
            item_path = os.path.join(save_path, item)
            if os.path.isdir(item_path):
                # 检查是否是17位数字文件夹
                if item.isdigit() and len(item) == 17:
                    steam_id_found = True
                    steam_id_folders.append(item)
                    
                    # 检查文件夹内是否有ER开头的文件
                    has_er_files = any(f.startswith('ER') for f in os.listdir(item_path))
                    if not has_er_files:
                        return False, f"SteamID文件夹{item}内无ER文件", ""
        
        if not steam_id_found:
            return False, "未找到SteamID文件夹", ""
        
        details = f"{len(steam_id_folders)}个SteamID文件夹"
        return True, "存档合法", details

    def backup_current_save(self):
        """备份当前存档"""
        if not os.path.exists(self.save_path):
            return False, "存档目录不存在"
        
        # 检查目录是否为空或有内容
        try:
            items = os.listdir(self.save_path)
            if not items:
                return False, "存档目录为空，无需备份"
            
            # 检查是否有任何有效内容
            has_content = False
            for item in items:
                item_path = os.path.join(self.save_path, item)
                if os.path.isdir(item_path):
                    if os.listdir(item_path):
                        has_content = True
                        break
                elif os.path.getsize(item_path) > 0:
                    has_content = True
                    break
            
            if not has_content:
                return False, "存档目录无有效内容，无需备份"
        except (OSError, PermissionError) as e:
            return False, f"检查存档目录失败: {str(e)}"
        
        try:
            # 创建备份目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir_name = f"{timestamp}_auto_backup"
            backup_dir = os.path.join("saves", backup_dir_name)
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # 复制整个EldenRing文件夹
            backup_target = os.path.join(backup_dir, "EldenRing")
            
            # 如果备份目标已存在，先删除
            if os.path.exists(backup_target):
                success, message = self.delete_save_directory(backup_target, force=True)
                if not success:
                    # 如果删除失败，尝试创建新的备份目录名
                    backup_dir_name = f"{timestamp}_auto_backup_2"
                    backup_dir = os.path.join("saves", backup_dir_name)
                    os.makedirs(backup_dir, exist_ok=True)
                    backup_target = os.path.join(backup_dir, "EldenRing")
            
            shutil.copytree(self.save_path, backup_target)
            
            # 刷新存档列表
            self.refresh_save_list()
            
            return True, f"自动备份成功: {backup_dir_name}"
            
        except Exception as e:
            return False, f"备份失败: {str(e)}"

    def import_selected_save(self):
        """导入选中的存档"""
        selected = self.save_combo_var.get()
        if not selected:
            messagebox.showwarning("警告", "请先选择存档")
            return
        
        saves_dir = "saves"
        selected_path = os.path.join(saves_dir, selected)
        
        # 检查存档合法性
        is_valid, status_msg, details = self.check_save_validity(selected_path)
        if not is_valid:
            messagebox.showwarning("警告", f"存档不合法: {status_msg}")
            return
        
        # 检查游戏是否正在运行
        try:
            import psutil
            game_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name']:
                    proc_name = proc.info['name'].lower()
                    if proc_name in ['eldenring.exe', 'ersc_launcher.exe']:
                        game_running = True
                        break
            
            if game_running:
                response = messagebox.askyesno("游戏正在运行",
                    "检测到游戏正在运行。\n\n"
                    "导入存档需要关闭游戏以避免文件占用问题。\n\n"
                    "是否继续？（强烈建议先关闭游戏）")
                if not response:
                    return
        except ImportError:
            # 如果没有psutil库，提示用户手动检查
            response = messagebox.askyesno("提示",
                "无法自动检测游戏状态。\n\n"
                "导入存档前请确保艾尔登法环游戏已完全关闭。\n\n"
                "游戏是否已关闭？")
            if not response:
                return
        except Exception as e:
            print(f"游戏检测异常: {e}")
            # 检测失败时仍然提示
            response = messagebox.askyesno("提示",
                "游戏状态检测失败。\n\n"
                "导入存档前请确保艾尔登法环游戏已完全关闭。\n\n"
                "游戏是否已关闭？")
            if not response:
                return
        
        # 检查游戏存档目录是否存在
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path, exist_ok=True)
        
        # 检查当前存档目录是否非空
        current_save_has_content = False
        if os.path.exists(self.save_path):
            # 检查目录下是否有任何文件或文件夹
            try:
                current_save_has_content = any(
                    os.path.getsize(os.path.join(self.save_path, f)) > 0 or 
                    os.path.isdir(os.path.join(self.save_path, f))
                    for f in os.listdir(self.save_path)
                )
            except (OSError, PermissionError):
                current_save_has_content = bool(os.listdir(self.save_path))
        
        # 如果已有存档内容且未选择直接覆盖，则询问
        if current_save_has_content and not self.import_overwrite_var.get():
            response = messagebox.askyesnocancel("确认", 
                f"目标存档目录已有文件。\n是否先备份当前存档再导入？\n\n"
                f"点击'是'备份并导入\n点击'否'直接覆盖\n点击'取消'取消操作")
            
            if response is None:  # 取消
                return
            elif response:  # 是，先备份
                success, msg = self.backup_current_save()
                if not success:
                    messagebox.showwarning("警告", f"备份失败: {msg}")
                    return
        
        # 如果直接覆盖被选中且当前存档有内容，则自动备份
        if self.import_overwrite_var.get() and current_save_has_content:
            success, msg = self.backup_current_save()
            if not success:
                messagebox.showwarning("警告", f"自动备份失败: {msg}")
                # 询问是否继续
                if not messagebox.askyesno("警告", "自动备份失败，是否继续导入？"):
                    return
        
        # 导入存档
        try:
            print(f"正在导入存档: {selected}  1")
            
            # 确定源路径
            eldenring_source = os.path.join(selected_path, "EldenRing")
            if os.path.exists(eldenring_source):
                # 情况1：有EldenRing文件夹
                source_path = eldenring_source
            else:
                # 情况2：直接是存档文件
                source_path = selected_path
            print(f"正在导入存档: {selected}  2")
            
            # 清除目标目录 - 使用封装的函数
            print(f"开始清除目标目录: {self.save_path}")
            success, message = self.delete_save_directory(self.save_path, force=True)
            if not success:
                # 如果删除失败，询问用户是否继续
                response = messagebox.askyesno("删除失败",
                    f"清理目标目录失败: {message}\n\n"
                    f"是否尝试继续导入？（可能会导致文件冲突）")
                if not response:
                    return
            print(f"正在导入存档: {selected}  3")
            
            # 复制存档文件
            for item in os.listdir(source_path):
                src = os.path.join(source_path, item)
                dst = os.path.join(self.save_path, item)
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            # 刷新存档列表
            self.refresh_save_list()
            
            # 更新存档路径显示
            self.update_path_labels()
            
            messagebox.showinfo("成功", "存档导入完成！")
            self.status("存档导入完成")
            
        except Exception as e:
            messagebox.showerror("错误", f"导入失败:\n{str(e)}")
            self.status(f"导入失败: {str(e)}")

    def export_current_save(self):
        """导出当前存档"""
        if not os.path.exists(self.save_path) or not os.listdir(self.save_path):
            messagebox.showwarning("警告", "当前无存档可导出")
            return
        
        # 选择保存位置
        save_dir = filedialog.askdirectory(title="选择保存位置", initialdir="saves")
        if not save_dir:
            return
        
        try:
            # 创建导出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir_name = f"{timestamp}_manual_backup"
            export_dir = os.path.join(save_dir, export_dir_name)
            
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # 创建EldenRing文件夹
            export_target = os.path.join(export_dir, "EldenRing")
            if os.path.exists(export_target):
                shutil.rmtree(export_target)
            
            os.makedirs(export_target)
            
            # 复制所有文件到EldenRing文件夹内
            for item in os.listdir(self.save_path):
                src = os.path.join(self.save_path, item)
                dst = os.path.join(export_target, item)
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            # 如果保存位置是saves目录，则刷新列表
            if os.path.abspath(save_dir) == os.path.abspath("saves"):
                self.refresh_save_list()
            
            messagebox.showinfo("成功", f"存档已导出到:\n{export_dir}")
            self.status(f"存档已导出: {export_dir_name}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")
            self.status(f"导出失败: {str(e)}")

    def _auto_backup_current_save(self):
        """自动备份当前存档（在导入前调用）"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir_name = f"{timestamp}_auto_backup"
            backup_dir = os.path.join("saves", backup_dir_name)
            
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            backup_target = os.path.join(backup_dir, "EldenRing")
            if os.path.exists(backup_target):
                shutil.rmtree(backup_target)
            
            shutil.copytree(self.save_path, backup_target)
            
            return True, backup_dir_name
        except Exception as e:
            return False, str(e)
        
    def ensure_save_directories(self):
        """确保存档相关目录存在"""
        # 确保saves目录存在
        if not os.path.exists("saves"):
            os.makedirs("saves", exist_ok=True)
        
        # 确保游戏存档目录存在
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path, exist_ok=True)
    
    def initial_save_check(self):
        """初始检查存档状态"""
        self.refresh_save_list()
    
    def initial_launch_check(self):
        """初始检查启动状态"""
        self.refresh_launch_status()
    
    #endregion

    #region 启动游戏相关函数
    def refresh_launch_status(self):
        """刷新启动游戏状态 """
        bat_file = os.path.join(os.getcwd(), "launchmod_eldenring.bat")
        if os.path.exists(bat_file):
            self.launch_btn.config(state="normal")
            self.launch_status_label.config(text="就绪", fg="green", font=("Microsoft YaHei", 9))
        else:
            self.launch_btn.config(state="disabled")
            self.launch_status_label.config(text="未找到启动文件", fg="red", font=("Microsoft YaHei", 9))

    def launch_game(self):
        """启动游戏 - 执行同目录下的 launchmod_eldenring.bat"""
        bat_file = os.path.join(os.getcwd(), "launchmod_eldenring.bat")
        
        if not os.path.exists(bat_file):
            messagebox.showerror("错误", f"未找到启动文件:\n{bat_file}")
            return
        
        try:
            # 检查游戏是否已经在运行
            if self.check_game_running():
                response = messagebox.askyesno("游戏正在运行", 
                    "检测到游戏正在运行。\n\n是否启动新实例？（不建议）")
                if not response:
                    return
            
            # 禁用按钮，防止多次点击
            self.launch_btn.config(state="disabled")
            self.launch_status_label.config(text="正在启动...", fg="orange")
            
            # 启动批处理文件
            import subprocess
            subprocess.Popen([bat_file], cwd=os.getcwd())
            
            # 设置定时器，3秒后重新启用按钮
            self.root.after(3000, self.enable_launch_button)
            self.status("游戏启动中...")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动游戏失败:\n{str(e)}")
            self.launch_status_label.config(text="启动失败", fg="red")
            self.root.after(3000, self.enable_launch_button)
    def check_game_running(self):
        """检查游戏是否正在运行"""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if proc.info['name']:
                    proc_name = proc.info['name'].lower()
                    if proc_name in ['eldenring.exe', 'ersc_launcher.exe']:
                        return True
            return False
        except ImportError:
            # 如果没有psutil库，简单检查
            try:
                import subprocess
                # Windows命令检查进程
                result = subprocess.run(
                    ['tasklist', '/FI', 'IMAGENAME eq eldenring.exe'], 
                    capture_output=True, text=True
                )
                return 'eldenring.exe' in result.stdout.lower()
            except:
                return False

    #endregion


if __name__ == "__main__":
    # 使用mini界面
    app = EldenRingTool(ui_type="normal")

    # 或者使用原版界面
    # app = EldenRingTool(ui_type="normal")
    # 或者不传参数，默认使用mini（因为默认值设为"mini"）
    # app = EldenRingTool()
    app.run()