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
        self.root.after(100, self.initial_mod_check)  # 延迟100ms执行

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
        self.root.geometry("350x600")

        # 路径显示区域
        path_frame = tk.LabelFrame(self.root, text="路径信息", padx=10, pady=10)
        path_frame.pack(fill="x", padx=20, pady=2)
        
        # Steam路径
        tk.Label(path_frame, text="Steam路径:").grid(row=0, column=0, sticky="w")
        self.steam_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow")
        self.steam_label.grid(row=0, column=1, sticky="w")
        
        # 游戏路径
        tk.Label(path_frame, text="游戏路径:").grid(row=1, column=0, sticky="w", pady=3)
        self.game_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow")
        self.game_label.grid(row=1, column=1, sticky="w", pady=3)

        # 存档路径
        tk.Label(path_frame, text="存档路径:").grid(row=2, column=0, sticky="w")
        self.save_label = tk.Label(path_frame, text="正在检测...", fg="gray", cursor="arrow")
        self.save_label.grid(row=2, column=1, sticky="w")

        # 重新检测路径按钮 - 放在路径区域最下方
        self.path_status_label = tk.Label(path_frame, 
                                        text="就绪 (点击重新检测路径)",
                                        fg="gray", cursor="hand2")
        self.path_status_label.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="w")
        
        # 绑定点击事件到状态标签
        self.path_status_label.bind("<Button-1>", lambda e: self.auto_detect_paths())
        
        # 添加悬停效果
        self.path_status_label.bind("<Enter>", 
                                    lambda e: self.path_status_label.config(fg="blue"))
        self.path_status_label.bind("<Leave>", 
                                    lambda e: self.path_status_label.config(fg="gray"))
        
        # MOD管理区域
        mod_frame = tk.LabelFrame(self.root, text="MOD管理", padx=10, pady=5)
        mod_frame.pack(fill="x", padx=20, pady=3)

        # 使用网格布局，更整齐
        mod_inner_frame = tk.Frame(mod_frame)
        mod_inner_frame.pack(fill="x", padx=5, pady=5)

        # 第1行：原MOD文件状态
        tk.Label(mod_inner_frame, text="MOD源文件:", width=10, anchor="w").grid(row=0, column=0, sticky="w", pady=3)
        self.mod_source_status = tk.Label(mod_inner_frame, text="未检测", fg="gray", cursor="hand2")
        self.mod_source_status.grid(row=0, column=1, sticky="w", pady=3)
        self.mod_source_status.bind("<Button-1>", lambda e: self.check_seamless_coop_source_status())

        # 第2行：目标目录MOD状态
        tk.Label(mod_inner_frame, text="已安装MOD:", width=10, anchor="w").grid(row=1, column=0, sticky="w", pady=3)
        self.mod_installed_status = tk.Label(mod_inner_frame, text="未检测", fg="gray", cursor="hand2")
        self.mod_installed_status.grid(row=1, column=1, sticky="w", pady=3)
        self.mod_installed_status.bind("<Button-1>", lambda e: self.check_seamless_coop_installed_status())

        # 第3行：联机密码
        tk.Label(mod_inner_frame, text="联机密码:", width=10, anchor="w").grid(row=2, column=0, sticky="w", pady=3)
        self.mod_password_label = tk.Label(mod_inner_frame, text="未设置", fg="gray")
        self.mod_password_label.grid(row=2, column=1, sticky="w", pady=3)

        # 第4行：死亡惩罚
        tk.Label(mod_inner_frame, text="死亡惩罚:", width=10, anchor="w").grid(row=3, column=0, sticky="w", pady=3)
        self.mod_debuff_label = tk.Label(mod_inner_frame, text="未设置", fg="gray")
        self.mod_debuff_label.grid(row=3, column=1, sticky="w", pady=3)

        # 操作区域
        mod_ops_frame = tk.Frame(mod_frame)
        mod_ops_frame.pack(fill="x", padx=5, pady=10)

        # 导入MOD按钮
        self.import_mod_btn = tk.Button(mod_ops_frame, text="导入MOD文件", 
                                    command=self.import_mod_with_option, width=15)
        self.import_mod_btn.pack(side="left", padx=5)

        # 覆盖选项
        self.overwrite_var = tk.BooleanVar(value=True)  # 默认勾选
        self.overwrite_check = tk.Checkbutton(mod_ops_frame, text="直接覆盖不询问", 
                                            variable=self.overwrite_var)
        self.overwrite_check.pack(side="left", padx=5)

        # 密码修改区域
        mod_config_frame = tk.Frame(mod_frame)
        mod_config_frame.pack(fill="x", padx=5, pady=5)

        # 密码设置
        pass_row = tk.Frame(mod_config_frame)
        pass_row.pack(fill="x", pady=3)

        tk.Label(pass_row, text="设置密码:", width=10, anchor="w").pack(side="left")
        self.password_var = tk.StringVar(value="4820")
        tk.Entry(pass_row, textvariable=self.password_var, 
                width=10).pack(side="left", padx=5)
        tk.Button(pass_row, text="修改", 
                command=self.update_password, width=6).pack(side="left")

        # death_debuffs设置
        debuff_row = tk.Frame(mod_config_frame)
        debuff_row.pack(fill="x", pady=3)

        tk.Label(debuff_row, text="死亡惩罚:", width=10, anchor="w").pack(side="left")
        tk.Button(debuff_row, text="启用(1)", 
                command=lambda: self.set_debuff(1), width=8).pack(side="left", padx=2)
        tk.Button(debuff_row, text="禁用(0)", 
                command=lambda: self.set_debuff(0), width=8).pack(side="left")
        
        # 存档管理区域
        save_frame = tk.LabelFrame(self.root, text="存档管理", padx=10, pady=5)
        save_frame.pack(fill="x", padx=20, pady=10)
        
        # 导入存档按钮
        tk.Button(save_frame, text="导入存档", command=None,
                 width=15).pack(side="left", padx=5)
        
        # 导出存档按钮
        tk.Button(save_frame, text="导出存档", command=self.export_save,
                 width=15).pack(side="left", padx=5)
        
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
        else:
            self.game_label.config(text="游戏路径 ✗ (点击手动定位)", fg="red", cursor="hand2")
            self.game_label.bind("<Button-1>", lambda e: self.manual_locate_game())
        
        # 存档路径
        if os.path.exists(self.save_path):
            self.save_label.config(text="存档路径 ✓", fg="green", cursor="hand2")
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
        self.path_status_label.config(text="检测完成 (点击重新检测路径)", fg="gray")
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
            return
        
        # 检查游戏目录中的MOD结构
        is_valid, status_msg, details = self.check_seamless_coop_structure(self.game_path)
        
        if is_valid:
            self.mod_installed_status.config(text="已安装 ✓", fg="green")
            # 加载配置
            self.load_seamless_coop_config()
        else:
            if details["total_found"] > 0:
                self.mod_installed_status.config(text=status_msg, fg="orange")
            else:
                self.mod_installed_status.config(text="未安装", fg="red")
            
            # 清空配置显示
            self.mod_password_label.config(text="-", fg="gray")
            self.mod_debuff_label.config(text="-", fg="gray")

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
    def export_save(self):
        """导出存档"""
        if not os.path.exists(self.save_path):
            messagebox.showwarning("警告", "未找到存档目录")
            return
        
        # 选择保存位置
        save_dir = filedialog.askdirectory(title="选择保存位置")
        if not save_dir:
            return
        
        # 创建备份文件夹
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_folder = f"{timestamp}_存档备份"
        backup_path = os.path.join(save_dir, backup_folder)
        
        if not os.path.exists(backup_path):
            os.makedirs(backup_path)
        
        self.status("正在导出存档...")
        
        try:
            # 复制存档
            dest_save = os.path.join(backup_path, "EldenRing")
            if os.path.exists(dest_save):
                shutil.rmtree(dest_save)
            
            shutil.copytree(self.save_path, dest_save)
            
            # 创建ZIP文件
            zip_filename = os.path.join(save_dir, f"{backup_folder}.zip")
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(dest_save):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, dest_save)
                        zipf.write(file_path, arcname)
            
            self.status(f"存档已导出到: {zip_filename}")
            messagebox.showinfo("成功", f"存档已导出到:\n{zip_filename}")
            
        except Exception as e:
            self.status(f"导出失败: {str(e)}")
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")
    #endregion

    #region 编辑mod文件相关函数
    def load_seamless_coop_config(self):
        """加载无缝联机MOD配置"""
        mod_config = self.config["mods"]["seamless_coop"]
        config_file_path = os.path.join(self.game_path, mod_config["config_file"])
        
        if not os.path.exists(config_file_path):
            self.mod_password_label.config(text="无配置文件", fg="orange")
            self.mod_debuff_label.config(text="无配置文件", fg="orange")
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(config_file_path, encoding='utf-8')
            
            # 获取联机密码
            password = config.get('settings', 'cooppassword', fallback='未设置')
            self.mod_password_label.config(text=password, fg="green")
            
            # 获取死亡惩罚
            debuff = config.get('settings', 'death_debuffs', fallback='未设置')
            self.mod_debuff_label.config(text=debuff, fg="green")
            
            # 更新输入框
            if password != '未设置' and password.isdigit():
                self.password_var.set(password)
                
        except Exception as e:
            self.mod_password_label.config(text=f"读取失败", fg="red")
            self.mod_debuff_label.config(text=f"读取失败", fg="red")

    def update_password(self):
        """更新联机密码"""
        # 检查是否已安装MOD
        coop_folder = os.path.join(self.game_path, "SeamlessCoop")
        if not os.path.exists(coop_folder):
            messagebox.showwarning("警告", "请先导入MOD文件")
            return
        
        config_file = os.path.join(coop_folder, "ersc_settings.ini")
        
        new_password = self.password_var.get().strip()
        if not new_password.isdigit() or len(new_password) != 4:
            messagebox.showwarning("警告", "请输入4位数字密码")
            return
        
        try:
            config = configparser.ConfigParser()
            # 如果配置文件不存在，创建它
            if not os.path.exists(config_file):
                config['settings'] = {}
            
            config.read(config_file, encoding='utf-8')
            
            if not config.has_section('settings'):
                config.add_section('settings')
            
            config.set('settings', 'cooppassword', new_password)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # 更新显示
            self.mod_password_label.config(text=new_password, fg="green")
            self.status(f"密码已更新为: {new_password}")
            
        except Exception as e:
            messagebox.showerror("错误", f"更新密码失败:\n{str(e)}")

    def set_debuff(self, value):
        """设置death_debuffs值"""
        # 检查是否已安装MOD
        coop_folder = os.path.join(self.game_path, "SeamlessCoop")
        if not os.path.exists(coop_folder):
            messagebox.showwarning("警告", "请先导入MOD文件")
            return
        
        config_file = os.path.join(coop_folder, "ersc_settings.ini")
        
        try:
            config = configparser.ConfigParser()
            # 如果配置文件不存在，创建它
            if not os.path.exists(config_file):
                config['settings'] = {}
            
            config.read(config_file, encoding='utf-8')
            
            if not config.has_section('settings'):
                config.add_section('settings')
            
            config.set('settings', 'death_debuffs', str(value))
            
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            
            # 更新显示
            self.mod_debuff_label.config(text=str(value), fg="green")
            self.status(f"死亡惩罚已设置为: {value}")
            
        except Exception as e:
            messagebox.showerror("错误", f"设置失败:\n{str(e)}")
    #endregion




if __name__ == "__main__":
    # 使用mini界面
    app = EldenRingTool(ui_type="normal")

    # 或者使用原版界面
    # app = EldenRingTool(ui_type="normal")
    # 或者不传参数，默认使用mini（因为默认值设为"mini"）
    # app = EldenRingTool()
    app.run()