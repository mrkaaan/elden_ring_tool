import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
import zipfile
import winreg
import json
import configparser
from datetime import datetime
import sys
import threading
import time

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
        self.root.title("艾尔登法环工具 v1.0")
        
        # 配置文件路径
        self.config_file = "config.json"
        self.config = self.load_config()
        
        # 全局变量
        self.steam_path = self.config.get("steam_path", "")
        self.game_path = self.config.get("game_path", "")
        self.save_path = os.path.expanduser("~\\AppData\\Roaming\\EldenRing")
        self.ensure_save_dir()   # 检查并创建存档目录
        self.mod_config_path = ""  # 会在检测mod时设置
        
        # 根据ui_type选择界面版本
        if ui_type == "mini":
            self.setup_ui_mini()
        else:
            self.setup_ui()

        self.auto_detect_paths()
        self.ensure_mod_config() # 确保MOD配置存在
        self.ensure_save_directories() # 确保存档目录存在
        self.root.after(100, self.initial_mod_check)  # 延迟100ms执行
        self.root.after(200, self.initial_save_check)  # 延迟200ms执行
        self.root.after(300, self.initial_launch_check)  # 延迟300ms执行

    #region 程序的确认和运行
    def initial_mod_check(self):
        """初始检查MOD状态"""
        self.check_seamless_coop_source_status()
        self.check_seamless_coop_installed_status()

    def run(self):
        """运行程序"""
        self.root.mainloop()
    #endregion

    #region 界面构建相关函数
    def setup_ui(self):
        """设置UI界面"""
        self.root.geometry("300x550")

        # 路径显示区域
        path_frame = tk.LabelFrame(self.root, text="路径信息", padx=10, pady=5)
        path_frame.pack(fill="x", padx=15, pady=2)
        
        # Steam路径
        tk.Label(path_frame, text="Steam路径:").grid(row=0, column=0, sticky="w")
        self.steam_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow")
        self.steam_label.grid(row=0, column=1, sticky="w")

        # 游戏路径
        tk.Label(path_frame, text="游戏路径:").grid(row=1, column=0, sticky="w")
        self.game_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow")
        self.game_label.grid(row=1, column=1, sticky="w", pady=3)

        # 存档路径
        tk.Label(path_frame, text="存档路径:").grid(row=2, column=0, sticky="w")
        self.save_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow")
        self.save_label.grid(row=2, column=1, sticky="w")

        # 工具目录链接和重新检测路径状态标签（使用grid放在同一行）
        link_frame = tk.Frame(path_frame)
        link_frame.grid(row=3, column=0, columnspan=2, pady=(0, 0), sticky="we")

        # 左边：工具目录链接（第0列，左对齐）
        self.tool_dir_link = tk.Label(link_frame, 
                                    text="打开工具目录",
                                    fg="gray", cursor="hand2")
        self.tool_dir_link.grid(row=0, column=0, sticky="w", padx=(0, 25))
        self.tool_dir_link.bind("<Button-1>", lambda e: self.open_folder(os.getcwd()))
        self.tool_dir_link.bind("<Enter>", 
                                lambda e: self.tool_dir_link.config(fg="blue"))
        self.tool_dir_link.bind("<Leave>", 
                                lambda e: self.tool_dir_link.config(fg="gray"))

        # 右边：路径状态标签（第1列，右对齐）
        self.path_status_label = tk.Label(link_frame, 
                                        text="点击重新检测路径",
                                        fg="gray", cursor="hand2")
        self.path_status_label.grid(row=0, column=1, sticky="e")
        self.path_status_label.bind("<Button-1>", lambda e: self.auto_detect_paths())
        self.path_status_label.bind("<Enter>", 
                                    lambda e: self.path_status_label.config(fg="blue"))
        self.path_status_label.bind("<Leave>", 
                                    lambda e: self.path_status_label.config(fg="gray"))

        # 让第1列自动扩展填充空间
        link_frame.grid_columnconfigure(0, weight=0)   # 第0列不扩展
        link_frame.grid_columnconfigure(1, weight=1)   # 第1列扩展，这样就会把右侧标签推到右边
        
        # MOD管理区域
        mod_frame = tk.LabelFrame(self.root, text="MOD管理", padx=10, pady=5)
        mod_frame.pack(fill="x", padx=15, pady=2)

        # 使用网格布局，更整齐
        mod_inner_frame = tk.Frame(mod_frame)
        mod_inner_frame.pack(fill="x")

        # 原MOD文件状态
        tk.Label(mod_inner_frame, text="MOD源文件:", width=10, anchor="w").grid(row=0, column=0, sticky="w", pady=3)
        self.mod_source_status = tk.Label(mod_inner_frame, text="未检测", fg="gray", cursor="hand2")
        self.mod_source_status.grid(row=0, column=1, sticky="w", pady=3)
        self.mod_source_status.bind("<Button-1>", lambda e: self.check_seamless_coop_source_status())

        # 目标目录MOD状态
        tk.Label(mod_inner_frame, text="已安装MOD:", width=10, anchor="w").grid(row=1, column=0, sticky="w", pady=3)
        self.mod_installed_status = tk.Label(mod_inner_frame, text="未检测", fg="gray", cursor="hand2")
        self.mod_installed_status.grid(row=1, column=1, sticky="w", pady=3)
        self.mod_installed_status.bind("<Button-1>", lambda e: self.check_seamless_coop_installed_status())

        # 操作区域 - 放在状态信息下面
        ops_frame = tk.Frame(mod_frame)
        ops_frame.pack(fill="x", pady=(0, 0))

        # 导入MOD按钮
        import_btn_frame = tk.Frame(ops_frame)
        import_btn_frame.pack(fill="x", pady=(0, 0))

        tk.Button(import_btn_frame, text="导入MOD文件", 
                command=self.import_mod_with_option, width=15).pack(side="left", padx=(0, 10))

        # 覆盖选项
        self.overwrite_var = tk.BooleanVar(value=True)  # 默认勾选
        overwrite_check = tk.Checkbutton(import_btn_frame, text="直接覆盖", 
                                        variable=self.overwrite_var)
        overwrite_check.pack(side="left")

        # 配置区域 - 放在导入按钮下方
        config_frame = tk.Frame(ops_frame)
        config_frame.pack(fill="x", pady=(0, 0))

        # 密码设置行
        pass_row = tk.Frame(config_frame)
        pass_row.pack(fill="x", pady=5)

        tk.Label(pass_row, text="设置密码:", width=8, anchor="w").pack(side="left")
        self.password_var = tk.StringVar(value="")
        tk.Entry(pass_row, textvariable=self.password_var, 
                width=10).pack(side="left", padx=5)

        # 修改密码链接
        self.update_pass_link = tk.Label(pass_row, text="修改", 
                                        fg="gray", cursor="hand2")
        self.update_pass_link.pack(side="left", padx=5)
        self.update_pass_link.bind("<Button-1>", lambda e: self.update_password())
        self.update_pass_link.bind("<Enter>", 
                                lambda e: self.update_pass_link.config(fg="blue"))
        self.update_pass_link.bind("<Leave>", 
                                lambda e: self.update_pass_link.config(fg="gray"))

        # 死亡惩罚设置行
        debuff_row = tk.Frame(config_frame)
        debuff_row.pack(fill="x", pady=0)

        tk.Label(debuff_row, text="死亡惩罚:", width=8, anchor="w").pack(side="left")

        # 单选按钮
        debuff_radio_frame = tk.Frame(debuff_row)
        debuff_radio_frame.pack(side="left")

        # 创建单选按钮变量
        self.debuff_var = tk.IntVar(value=-1)  # 初始设置为-1（不选中任何选项）

        # 启用单选按钮
        enable_radio = tk.Radiobutton(debuff_radio_frame, text="启用(1)", 
                                    variable=self.debuff_var, value=1,
                                    command=lambda: self.set_debuff(1))
        enable_radio.pack(side="left", padx=5)

        # 禁用单选按钮
        disable_radio = tk.Radiobutton(debuff_radio_frame, text="禁用(0)", 
                                    variable=self.debuff_var, value=0,
                                    command=lambda: self.set_debuff(0))
        disable_radio.pack(side="left", padx=5)

        # 单选按钮
        debuff_radio_frame = tk.Frame(debuff_row)
        debuff_radio_frame.pack(side="left")
        
        # 存档管理区域
        save_frame = tk.LabelFrame(self.root, text="存档管理", padx=10, pady=5)
        save_frame.pack(fill="x", padx=15, pady=2)

        # 使用网格布局，更紧凑
        save_inner_frame = tk.Frame(save_frame)
        save_inner_frame.pack(fill="x", padx=5, pady=5)

        # 第1行：选择存档标签和下拉框
        save_row1 = tk.Frame(save_inner_frame)
        save_row1.pack(fill="x", pady=(0, 5))

        tk.Label(save_row1, text="选择存档:", width=10, anchor="w").pack(side="left")

        # 存档下拉框
        self.save_combo_var = tk.StringVar()
        self.save_combo = ttk.Combobox(save_row1, 
                                    textvariable=self.save_combo_var,
                                    state="readonly", width=30)
        self.save_combo.pack(side="left", padx=5)
        self.save_combo.bind("<<ComboboxSelected>>", lambda e: self.on_save_selected())

        # 第2行：状态标签（左）和刷新按钮（右）两端对齐
        save_row2 = tk.Frame(save_inner_frame)
        save_row2.pack(fill="x", pady=(0, 0))

        # 状态标签放在左侧
        self.save_status_label = tk.Label(save_row2, 
                                        text="未选择存档", fg="gray", 
                                        font=("Arial", 9))
        self.save_status_label.pack(side="left")

        # 中间的空Frame用于占据剩余空间，实现两端对齐
        tk.Frame(save_row2).pack(side="left", expand=True, fill="x")

        # 刷新链接放在右侧
        self.refresh_save_link = tk.Label(save_row2, 
                                        text="刷新",
                                        fg="gray", cursor="hand2", font=("Arial", 9))
        self.refresh_save_link.pack(side="left")
        self.refresh_save_link.bind("<Button-1>", lambda e: self.refresh_save_list())
        self.refresh_save_link.bind("<Enter>", 
                                lambda e: self.refresh_save_link.config(fg="blue"))
        self.refresh_save_link.bind("<Leave>", 
                                lambda e: self.refresh_save_link.config(fg="gray"))

        # 第3行：导入存档、复选框、导出存档（在同一行）
        save_row3 = tk.Frame(save_inner_frame)
        save_row3.pack(fill="x")

        # 导入存档按钮
        tk.Button(save_row3, text="导入存档", 
                command=self.import_selected_save, width=10).pack(side="left", padx=(0, 5))

        # 直接覆盖复选框 - 紧挨着导入按钮
        self.import_overwrite_var = tk.BooleanVar(value=True)
        import_overwrite_check = tk.Checkbutton(save_row3, text="直接覆盖",
                                            variable=self.import_overwrite_var)
        import_overwrite_check.pack(side="left", padx=(0, 15))

        # 导出存档按钮
        tk.Button(save_row3, text="导出存档", 
                command=self.export_current_save, width=10).pack(side="left")

        # 启动游戏区域 - 放在主界面最底部
        launch_frame = tk.LabelFrame(self.root, text="启动游戏", padx=10, pady=5)
        launch_frame.pack(fill="x", padx=15, pady=(2, 2))

        # 启动游戏按钮（居中）
        self.launch_btn = tk.Button(launch_frame, text="启动游戏", 
                                command=self.launch_game, 
                                state="disabled", width=20)
        self.launch_btn.pack(pady=(0, 2))

        # 刷新按钮和状态标签（在同一行，刷新靠右）
        launch_status_frame = tk.Frame(launch_frame)
        launch_status_frame.pack(fill="x")

        # 状态标签（左）
        self.launch_status_label = tk.Label(launch_status_frame, 
                                            text="MOD未安装",
                                            fg="gray", font=("Arial", 9))
        self.launch_status_label.pack(side="left")

        # 中间的空Frame用于占据剩余空间
        tk.Frame(launch_status_frame).pack(side="left", expand=True, fill="x")

        # 刷新链接（右）
        self.refresh_launch_link = tk.Label(launch_status_frame, 
                                            text="刷新状态",
                                            fg="gray", cursor="hand2", font=("Arial", 9))
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
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
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
        # Steam路径
        if os.path.exists(self.steam_path):
            self.steam_label.config(text="Steam路径 ✓", fg="green", cursor="hand2")
            # 移除之前的tooltip绑定（如果存在）
            if hasattr(self.steam_label, 'tooltip'):
                self.steam_label.tooltip = None
            # 添加新的tooltip
            self.steam_label.tooltip = ToolTip(self.steam_label, self.steam_path)
            self.steam_label.bind("<Button-1>", lambda e: self.open_folder(self.steam_path))
        else:
            self.steam_label.config(text="Steam路径 ✗ (点击手动定位)", fg="red", cursor="hand2")
            self.steam_label.bind("<Button-1>", lambda e: self.manual_locate_steam())
        
        # 游戏路径
        if os.path.exists(self.game_path):
            self.game_label.config(text="游戏路径 ✓", fg="green", cursor="hand2")
            if hasattr(self.game_label, 'tooltip'):
                self.game_label.tooltip = None
            self.game_label.tooltip = ToolTip(self.game_label, self.game_path)
            self.game_label.bind("<Button-1>", lambda e: self.open_folder(self.game_path))
            # 当游戏路径存在时，自动刷新MOD状态
            self.check_seamless_coop_installed_status()
        else:
            self.game_label.config(text="游戏路径 ✗ (点击手动定位)", fg="red", cursor="hand2")
            self.game_label.bind("<Button-1>", lambda e: self.manual_locate_game())
        
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
        """自动检测Steam和游戏路径"""
        self.status("正在检测路径...")
        # 更新路径状态标签为"正在检测..."
        # self.path_status_label.config(text="正在检测...", fg="orange")

        # 从注册表获取Steam路径
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Valve\Steam")
            steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
            self.steam_path =  self.ensure_drive_uppercase(steam_path).replace("/", "\\")
            self.config["steam_path"] = self.steam_path
        except:
            self.steam_path = "未找到Steam路径"
        
        # 查找艾尔登法环游戏路径
        game_path = self.find_elden_ring_path()
        if game_path:
            self.game_path = self.ensure_drive_uppercase(game_path)
            self.config["game_path"] = self.game_path
        else:
            self.game_path = "未找到游戏路径"

        # 检查存档目录状态
        if self.ensure_save_dir():
            save_dir_status = "存档目录就绪"
        else:
            save_dir_status = "存档目录创建失败"
        
        # 更新UI
        # self.path_status_label.config(text="点击重新检测路径", fg="gray")
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

    def find_elden_ring_path(self):
        """查找艾尔登法环游戏路径"""
        possible_paths = [
            os.path.join(self.steam_path, "steamapps", "common", "ELDEN RING", "Game"),
            os.path.join(self.steam_path, "steamapps", "common", "Elden Ring", "Game"),
            "C:\\Program Files (x86)\\Steam\\steamapps\\common\\ELDEN RING\\Game",
            "D:\\Steam\\steamapps\\common\\ELDEN RING\\Game",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果没找到，让用户选择
        # path = filedialog.askdirectory(title="请选择Elden Ring的Game目录")

        if path and os.path.exists(path):
            return path
        return None
    
    def manual_locate_steam(self):
        """手动定位Steam路径"""
        path = filedialog.askdirectory(title="请选择Steam安装目录")
        if path:
            self.steam_path = self.ensure_drive_uppercase(path)
            self.config["steam_path"] = self.steam_path
            self.update_path_labels()
            self.save_config()

    def manual_locate_game(self):
        """手动定位游戏路径"""
        path = filedialog.askdirectory(title="请选择ELDEN RING的Game目录")
        if path:
            self.game_path = self.ensure_drive_uppercase(path)
            self.config["game_path"] = self.game_path
            self.update_path_labels()
            self.save_config()

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

    #region mod文件相关函数
    def ensure_mod_config(self):
        """确保MOD配置存在"""
        if "mods" not in self.config:
            self.config["mods"] = {}
        
        # 添加无缝联机MOD的配置 - 使用树状结构
        if "seamless_coop" not in self.config["mods"]:
            self.config["mods"]["seamless_coop"] = {
                "name": "无缝联机MOD",
                "file_tree": {
                    # 根目录下的文件夹
                    "folders": {
                        "SeamlessCoop": {
                            "files": ["ersc_settings.ini"],  # SeamlessCoop文件夹下的文件
                            "folders": {}  # SeamlessCoop文件夹下的子文件夹
                        }
                    },
                    # 根目录下的文件
                    "files": ["ersc_launcher.exe"]
                },
                "description": "艾尔登法环无缝联机MOD",
                "source_dir": "mods/seamless_coop",  # 源文件存放目录
                "target_dir": "game",  # 游戏目录相对路径
                "config_file": "SeamlessCoop/ersc_settings.ini"  # 配置文件路径
            }
            self.save_config()

    def check_mod_structure(self, directory, file_tree):
        """
        通用的MOD结构检查函数（支持树状结构）
        
        Args:
            directory: 要检查的目录
            file_tree: 树状结构配置，格式：
                {
                    "folders": {
                        "folder1": {
                            "files": ["file1.txt", "file2.txt"],
                            "folders": {}  # 子文件夹
                        }
                    },
                    "files": ["root_file1.exe", "root_file2.dll"]
                }
        
        Returns:
            tuple: (is_valid, status_message, details)
        """
        if not os.path.exists(directory):
            return False, "目录不存在", {}
        
        found_folders = []
        found_files = []
        missing_folders = []
        missing_files = []
        
        # 检查根目录下的文件
        for file in file_tree.get("files", []):
            file_path = os.path.join(directory, file)
            if os.path.exists(file_path):
                found_files.append(file)
            else:
                missing_files.append(file)
        
        # 检查根目录下的文件夹
        for folder_name, folder_config in file_tree.get("folders", {}).items():
            folder_path = os.path.join(directory, folder_name)
            
            if os.path.exists(folder_path):
                found_folders.append(folder_name)
                
                # 递归检查文件夹内的文件
                if "files" in folder_config:
                    for file in folder_config.get("files", []):
                        nested_file_path = os.path.join(folder_path, file)
                        relative_path = f"{folder_name}/{file}"
                        
                        if os.path.exists(nested_file_path):
                            found_files.append(relative_path)
                        else:
                            missing_files.append(relative_path)
                
                # 递归检查子文件夹（如果需要多层嵌套）
                if "folders" in folder_config:
                    # 目前只支持一层嵌套，如果需要多层可以递归调用
                    for subfolder_name, subfolder_config in folder_config.get("folders", {}).items():
                        subfolder_path = os.path.join(folder_path, subfolder_name)
                        relative_path = f"{folder_name}/{subfolder_name}"
                        
                        if os.path.exists(subfolder_path):
                            found_folders.append(relative_path)
                            
                            # 检查子文件夹内的文件
                            if "files" in subfolder_config:
                                for file in subfolder_config.get("files", []):
                                    nested_file_path = os.path.join(subfolder_path, file)
                                    deeper_path = f"{folder_name}/{subfolder_name}/{file}"
                                    
                                    if os.path.exists(nested_file_path):
                                        found_files.append(deeper_path)
                                    else:
                                        missing_files.append(deeper_path)
                        else:
                            missing_folders.append(relative_path)
            else:
                missing_folders.append(folder_name)
        
        # 生成状态信息
        total_required = len(file_tree.get("files", [])) + len(file_tree.get("folders", {}))
        total_found = len(found_folders) + len(found_files)
        
        details = {
            "found_folders": found_folders,
            "found_files": found_files,
            "missing_folders": missing_folders,
            "missing_files": missing_files,
            "total_required": total_required,
            "total_found": total_found
        }
        
        # 判断状态
        if not missing_folders and not missing_files:
            return True, "完整", details
        elif found_folders or found_files:
            # 部分存在
            status_msg = f"部分存在 ({total_found}/{total_required})"
            return False, status_msg, details
        else:
            return False, "未找到所需文件", details
   
    def check_seamless_coop_structure(self, directory):
        """检查无缝联机MOD结构"""
        mod_config = self.config["mods"]["seamless_coop"]
        file_tree = mod_config["file_tree"]
        return self.check_mod_structure(directory, file_tree)

    def check_seamless_coop_source_status(self):
        """检查无缝联机MOD源文件状态"""
        mod_config = self.config["mods"]["seamless_coop"]
        source_dir = mod_config["source_dir"]
        
        # 如果源目录不存在，则不继续执行
        if not os.path.exists(source_dir):
            # os.makedirs(source_dir, exist_ok=True)
            # self.mod_source_status.config(text="MOD源目录已创建", fg="orange")
            return
        
        # 检查MOD结构
        is_valid, status_msg, details = self.check_seamless_coop_structure(source_dir)
        print(is_valid, status_msg, details)

        if is_valid:
            self.mod_source_status.config(text="MOD源文件完整 ✓", fg="green")
        elif details["total_found"] > 0:
            self.mod_source_status.config(text=status_msg, fg="orange")
        else:
            self.mod_source_status.config(text="未找到MOD源文件", fg="red")

    def check_seamless_coop_installed_status(self):
        """检查已安装的无缝联机MOD状态"""
        if not os.path.exists(self.game_path):
            self.mod_installed_status.config(text="游戏路径未找到", fg="red")
            self.update_launch_button_status()
            return
        
        # 检查MOD结构
        is_valid, status_msg, details = self.check_seamless_coop_structure(self.game_path)
        
        if is_valid:
            self.mod_installed_status.config(text="已安装 ✓", fg="green")
            # 加载配置
            self.load_seamless_coop_config()
            # 更新启动按钮状态
            self.update_launch_button_status()
        else:
            if details["total_found"] > 0:
                self.mod_installed_status.config(text=status_msg, fg="orange")
            else:
                self.mod_installed_status.config(text="未安装", fg="red")
            
            # 清空配置显示 - 这里需要清空密码输入框和死亡惩罚单选按钮
            self.password_var.set("")
            self.debuff_var.set(-1)  # 设置为无效值
            
            # 更新启动按钮状态
            self.update_launch_button_status()

    def import_mod(self, source_dir, target_dir, file_tree, overwrite=False):
        """
        通用的MOD导入函数（支持树状结构）
        
        Args:
            source_dir: 源目录
            target_dir: 目标目录
            file_tree: 树状结构配置
            overwrite: 是否直接覆盖，不询问
        
        Returns:
            tuple: (imported_items, skipped_items)
        """
        # 检查源目录
        is_valid, status_msg, details = self.check_mod_structure(source_dir, file_tree)
        if details["total_found"] == 0:
            raise Exception(f"源目录中未找到MOD文件: {status_msg}")
        
        imported_items = []
        skipped_items = []
        
        # 导入根目录下的文件
        for file in file_tree.get("files", []):
            src_path = os.path.join(source_dir, file)
            dst_path = os.path.join(target_dir, file)
            
            # 检查源文件是否存在
            if not os.path.exists(src_path):
                skipped_items.append(f"源文件不存在: {file}")
                continue
            
            imported = self._copy_item(src_path, dst_path, file, overwrite)
            if imported:
                imported_items.append(file)
            else:
                skipped_items.append(f"跳过: {file}")
        
        # 导入文件夹
        for folder_name, folder_config in file_tree.get("folders", {}).items():
            src_folder_path = os.path.join(source_dir, folder_name)
            dst_folder_path = os.path.join(target_dir, folder_name)
            
            # 检查源文件夹是否存在
            if not os.path.exists(src_folder_path):
                skipped_items.append(f"源文件夹不存在: {folder_name}")
                continue
            
            # 导入文件夹本身
            imported = self._copy_item(src_folder_path, dst_folder_path, folder_name, overwrite, is_folder=True)
            if imported:
                imported_items.append(folder_name)
            else:
                skipped_items.append(f"跳过: {folder_name}")
                continue  # 如果文件夹跳过，不再处理其中的文件
            
            # 导入文件夹内的文件
            if "files" in folder_config:
                for file in folder_config.get("files", []):
                    src_file_path = os.path.join(src_folder_path, file)
                    dst_file_path = os.path.join(dst_folder_path, file)
                    
                    # 检查源文件是否存在
                    if not os.path.exists(src_file_path):
                        skipped_items.append(f"源文件不存在: {folder_name}/{file}")
                        continue
                    
                    imported = self._copy_item(src_file_path, dst_file_path, f"{folder_name}/{file}", overwrite)
                    if imported:
                        imported_items.append(f"{folder_name}/{file}")
                    else:
                        skipped_items.append(f"跳过: {folder_name}/{file}")
        
        return imported_items, skipped_items

    def _copy_item(self, src_path, dst_path, item_name, overwrite, is_folder=False):
        """复制单个文件或文件夹"""
        try:
            # 检查目标文件是否存在
            if os.path.exists(dst_path):
                if not overwrite:
                    # 询问是否覆盖
                    response = messagebox.askyesno("覆盖确认", 
                        f"目标文件已存在: {item_name}\n是否覆盖？")
                    if not response:
                        return False
                
                # 删除已存在的文件/文件夹
                if os.path.isdir(dst_path):
                    shutil.rmtree(dst_path)
                else:
                    os.remove(dst_path)
            
            # 复制文件/文件夹
            if is_folder or os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)
            
            return True
        except Exception as e:
            print(f"复制 {item_name} 失败: {str(e)}")
            return False

    def import_seamless_coop_mod(self):
        """导入无缝联机MOD的特化函数"""
        # 检查游戏路径
        if not os.path.exists(self.game_path):
            messagebox.showerror("错误", "请先找到游戏路径！")
            return False
        
        # 获取MOD配置
        mod_config = self.config["mods"]["seamless_coop"]
        source_dir = mod_config["source_dir"]
        file_tree = mod_config["file_tree"]
        
        # 检查源目录
        is_valid, status_msg, details = self.check_seamless_coop_structure(source_dir)
        if details["total_found"] == 0:
            messagebox.showinfo("提示", f"请在以下目录中放置无缝联机MOD文件:\n{source_dir}")
            return False
        
        # 使用覆盖选项
        overwrite_option = self.overwrite_var.get()
        
        try:
            # 导入MOD
            imported_items, skipped_items = self.import_mod(
                source_dir, 
                self.game_path, 
                file_tree, 
                overwrite_option
            )
            
            if imported_items:
                messagebox.showinfo("成功", f"导入完成！\n导入项目: {len(imported_items)}个")
                # 更新状态
                self.check_seamless_coop_installed_status()
                # 更新启动按钮状态
                self.update_launch_button_status()
                return True
            else:
                messagebox.showwarning("警告", "没有文件被导入")
                return False
                
        except Exception as e:
            messagebox.showerror("错误", f"导入失败:\n{str(e)}")
            return False

    def import_mod_with_option(self):
        """界面调用的导入函数（无缝联机MOD特化）"""
        return self.import_seamless_coop_mod()

    #endregion

    #region 存档文件相关函数
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

    #region 编辑mod文件相关函数
    def load_seamless_coop_config(self):
        """加载无缝联机MOD配置"""
        mod_config = self.config["mods"]["seamless_coop"]
        config_file_path = os.path.join(self.game_path, mod_config["config_file"])
        
        if not os.path.exists(config_file_path):
            # 如果配置文件不存在，清空显示
            self.password_var.set("")
            self.debuff_var.set(-1)
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(config_file_path, encoding='utf-8')
            
            # 获取联机密码
            password = ""
            if config.has_section('PASSWORD'):
                password = config.get('PASSWORD', 'cooppassword', fallback='')
                password = password.strip()
            
            self.password_var.set(password)
            
            # 获取死亡惩罚
            debuff_value = -1
            if config.has_section('GAMEPLAY'):
                debuff_str = config.get('GAMEPLAY', 'death_debuffs', fallback='')
                try:
                    debuff_value = int(debuff_str.strip())
                    if debuff_value not in [0, 1]:
                        debuff_value = -1
                except (ValueError, AttributeError):
                    debuff_value = -1
            
            self.debuff_var.set(debuff_value)
            
        except Exception as e:
            print(f"读取MOD配置失败: {str(e)}")
            # 出错时清空显示
            self.password_var.set("")
            self.debuff_var.set(-1)

    def update_password(self):
        """更新联机密码"""
        # 检查是否已安装MOD
        coop_folder = os.path.join(self.game_path, "SeamlessCoop")
        if not os.path.exists(coop_folder):
            messagebox.showwarning("警告", "请先导入MOD文件")
            return
        
        config_file = os.path.join(coop_folder, "ersc_settings.ini")
        
        new_password = self.password_var.get().strip()
        
        # 检查密码是否为空
        if not new_password:
            response = messagebox.askyesno("确认", "密码为空，是否清空配置文件中的密码？")
            if not response:
                return
        
        # 如果密码不为空，验证格式
        elif not new_password.isdigit() or len(new_password) != 4:
            messagebox.showwarning("警告", "请输入4位数字密码")
            return
        
        try:
            config = configparser.ConfigParser()
            # 读取现有配置
            if os.path.exists(config_file):
                config.read(config_file, encoding='utf-8')
            
            # 确保有PASSWORD部分
            if not config.has_section('PASSWORD'):
                config.add_section('PASSWORD')
            
            # 更新密码（即使是空字符串也写入）
            config.set('PASSWORD', 'cooppassword', new_password)
            
            # 写入文件
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            if new_password:
                self.status(f"密码已更新为: {new_password}")
            else:
                self.status("密码已清空")
            
        except Exception as e:
            messagebox.showerror("错误", f"更新密码失败:\n{str(e)}")

    def set_debuff(self, value):
        """设置death_debuffs值"""
        # 检查是否已安装MOD
        coop_folder = os.path.join(self.game_path, "SeamlessCoop")
        if not os.path.exists(coop_folder):
            messagebox.showwarning("警告", "请先导入MOD文件")
            return
        
        # 检查值是否有效
        if value not in [0, 1]:
            return
        
        config_file = os.path.join(coop_folder, "ersc_settings.ini")
        
        try:
            config = configparser.ConfigParser()
            # 读取现有配置
            if os.path.exists(config_file):
                config.read(config_file, encoding='utf-8')
            
            # 确保有GAMEPLAY部分
            if not config.has_section('GAMEPLAY'):
                config.add_section('GAMEPLAY')
            
            # 更新death_debuffs
            config.set('GAMEPLAY', 'death_debuffs', str(value))
            
            # 写入文件
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            self.status(f"死亡惩罚已设置为: {value}")
            
        except Exception as e:
            messagebox.showerror("错误", f"设置失败:\n{str(e)}")

    def delete_save_directory(self, target_path, force=False):
        """
        删除存档目录中的所有内容
        
        Args:
            target_path: 要清理的目标路径
            force: 是否强制删除（即使文件被占用）
        
        Returns:
            tuple: (success, message)
        """
        if not os.path.exists(target_path):
            return True, "目录不存在"
        
        try:
            import stat
            
            def handle_remove_error(func, path, exc_info):
                """处理删除错误"""
                print(f"删除错误: {path}, 错误: {exc_info[1]}")
                
                if force:
                    # 强制删除：更改文件权限
                    try:
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    except Exception as e:
                        print(f"强制删除失败: {e}")
                        raise e
                else:
                    raise exc_info[1]  # 不强制删除则抛出异常
            
            # 删除目录中的所有内容
            for item in os.listdir(target_path):
                item_path = os.path.join(target_path, item)
                
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path, onerror=handle_remove_error)
                    else:
                        try:
                            os.remove(item_path)
                        except PermissionError:
                            if force:
                                os.chmod(item_path, stat.S_IWRITE)
                                os.remove(item_path)
                            else:
                                raise
                except Exception as e:
                    return False, f"删除失败 {item}: {str(e)}"
            
            return True, "删除成功"
            
        except Exception as e:
            return False, f"删除过程中发生错误: {str(e)}"
    #endregion

    #region 启动游戏相关函数
    def refresh_launch_status(self):
        """刷新启动游戏状态"""
        self.check_seamless_coop_installed_status()
        self.update_launch_button_status()

    def update_launch_button_status(self):
        """更新启动游戏按钮状态"""
        # 只检查启动器是否存在
        launcher_path = os.path.join(self.game_path, "ersc_launcher.exe")
        
        if os.path.exists(launcher_path):
            # 同时检查SeamlessCoop文件夹（MOD必要文件）
            coop_folder = os.path.join(self.game_path, "SeamlessCoop")
            if os.path.exists(coop_folder):
                self.launch_btn.config(state="normal")
                self.launch_status_label.config(text="可启动游戏", fg="green")
                return True
            else:
                self.launch_btn.config(state="disabled")
                self.launch_status_label.config(text="缺少MOD文件夹", fg="orange")
                return False
        else:
            self.launch_btn.config(state="disabled")
            self.launch_status_label.config(text="未找到启动器", fg="red")
            return False

    def launch_game(self):
        """启动游戏"""
        launcher_path = os.path.join(self.game_path, "ersc_launcher.exe")
        
        if not os.path.exists(launcher_path):
            messagebox.showerror("错误", f"未找到启动器:\n{launcher_path}")
            return
        
        try:
            # 检查游戏是否已经在运行
            if self.check_game_running():
                response = messagebox.askyesno("游戏正在运行", 
                    "检测到游戏正在运行。\n\n"
                    "是否启动新实例？（不建议）")
                if not response:
                    return
            
            # 禁用按钮，防止多次点击
            self.launch_btn.config(state="disabled")
            self.launch_status_label.config(text="正在启动...", fg="orange")
            
            # 启动游戏
            import subprocess
            subprocess.Popen([launcher_path], cwd=self.game_path)
            
            # 设置定时器，3秒后重新启用按钮
            self.root.after(3000, self.enable_launch_button)
            
            self.status("游戏启动中...")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动游戏失败:\n{str(e)}")
            self.launch_status_label.config(text="启动失败", fg="red")
            # 3秒后恢复按钮
            self.root.after(3000, self.enable_launch_button)

    def enable_launch_button(self):
        """启用启动游戏按钮"""
        self.update_launch_button_status()

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