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
        self.root.after(100, self.initial_mod_check)  # 延迟100ms执行

    #region 程序的确认和运行
    def initial_mod_check(self):
        """初始检查MOD状态"""
        self.check_mod_source_status()
        self.check_mod_installed_status()

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
        self.mod_source_status.bind("<Button-1>", lambda e: self.check_mod_source_status())

        # 第2行：目标目录MOD状态
        tk.Label(mod_inner_frame, text="已安装MOD:", width=10, anchor="w").grid(row=1, column=0, sticky="w", pady=3)
        self.mod_installed_status = tk.Label(mod_inner_frame, text="未检测", fg="gray", cursor="hand2")
        self.mod_installed_status.grid(row=1, column=1, sticky="w", pady=3)
        self.mod_installed_status.bind("<Button-1>", lambda e: self.check_mod_installed_status())

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
        # self.steam_label.config(text=self.steam_path)
        # self.game_label.config(text=self.game_path)
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
    def check_mod_source_status(self):
        """检查MOD源文件状态"""
        mods_dir = "mods"
        
        # 如果mods目录不存在，创建它
        if not os.path.exists(mods_dir):
            os.makedirs(mods_dir, exist_ok=True)
            self.mod_source_status.config(text="mods目录已创建", fg="orange")
            return
        
        # 查找MOD文件
        mod_files = self.find_mod_files(mods_dir)
        
        if not mod_files:
            self.mod_source_status.config(text="未找到MOD文件", fg="red")
        else:
            # 分析找到的文件
            has_folder = any(os.path.isdir(f) and os.path.basename(f) == "SeamlessCoop" for f in mod_files)
            has_exe = any(os.path.isfile(f) and os.path.basename(f) == "ersc_launcher.exe" for f in mod_files)
            
            if has_folder and has_exe:
                self.mod_source_status.config(text="完整MOD文件 ✓", fg="green")
            elif has_folder or has_exe:
                status = "部分文件" + ("(有文件夹)" if has_folder else "(有执行文件)")
                self.mod_source_status.config(text=status, fg="orange")
            else:
                # 可能是压缩包或其他文件
                self.mod_source_status.config(text=f"找到{len(mod_files)}个文件", fg="blue")

    def check_mod_installed_status(self):
        """检查已安装的MOD状态"""
        if not os.path.exists(self.game_path):
            self.mod_installed_status.config(text="游戏路径未找到", fg="red")
            return
        
        # 检查关键文件
        coop_folder = os.path.join(self.game_path, "SeamlessCoop")
        coop_exe = os.path.join(self.game_path, "ersc_launcher.exe")
        
        has_folder = os.path.exists(coop_folder)
        has_exe = os.path.exists(coop_exe)
        
        if has_folder and has_exe:
            self.mod_installed_status.config(text="已安装 ✓", fg="green")
            # 检查配置文件
            config_file = os.path.join(coop_folder, "ersc_settings.ini")
            if os.path.exists(config_file):
                self.load_mod_config(config_file)
            else:
                self.mod_password_label.config(text="无配置文件", fg="orange")
                self.mod_debuff_label.config(text="无配置文件", fg="orange")
        elif has_folder or has_exe:
            status = "部分安装" + ("(有文件夹)" if has_folder else "(有执行文件)")
            self.mod_installed_status.config(text=status, fg="orange")
            self.mod_password_label.config(text="-", fg="gray")
            self.mod_debuff_label.config(text="-", fg="gray")
        else:
            self.mod_installed_status.config(text="未安装", fg="red")
            self.mod_password_label.config(text="-", fg="gray")
            self.mod_debuff_label.config(text="-", fg="gray")

    def find_mod_files(self, directory):
        """在目录中查找MOD相关文件"""
        mod_files = []
        
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            
            # 检查是否是MOD相关文件
            if os.path.isdir(item_path) and item == "SeamlessCoop":
                mod_files.append(item_path)
            elif os.path.isfile(item_path) and item == "ersc_launcher.exe":
                mod_files.append(item_path)
            elif os.path.isfile(item_path) and item.lower().endswith(('.zip', '.rar', '.7z')):
                mod_files.append(item_path)
            # 如果目录包含SeamlessCoop或ersc_launcher.exe，也添加到列表
            elif os.path.isdir(item_path):
                sub_files = self.find_mod_files(item_path)
                if sub_files:
                    mod_files.extend(sub_files)
        
        return mod_files

    def import_mod_with_option(self):
        """带选项的导入MOD功能"""
        # 检查游戏路径
        if not os.path.exists(self.game_path):
            messagebox.showerror("错误", "请先找到游戏路径！")
            return
        
        # 选择MOD文件
        file_path = filedialog.askopenfilename(
            title="选择MOD文件",
            filetypes=[("所有文件", "*.*"), ("ZIP文件", "*.zip"), 
                    ("RAR文件", "*.rar"), ("7Z文件", "*.7z")]
        )
        
        if not file_path:
            return
        
        # 检查目标目录是否已有MOD文件
        coop_folder = os.path.join(self.game_path, "SeamlessCoop")
        coop_exe = os.path.join(self.game_path, "ersc_launcher.exe")
        
        has_existing = os.path.exists(coop_folder) or os.path.exists(coop_exe)
        
        # 如果存在已有文件且未勾选"直接覆盖"，则询问
        if has_existing and not self.overwrite_var.get():
            response = messagebox.askyesnocancel("覆盖确认", 
                f"目标目录已存在MOD文件。\n是否覆盖？\n\n" +
                f"点击'是'覆盖，'否'取消操作")
            
            if not response:  # 用户点击"否"或"取消"
                return
        
        # 导入MOD
        try:
            self.import_mod_file(file_path)
            messagebox.showinfo("成功", "MOD导入完成！")
            # 更新状态
            self.check_mod_installed_status()
        except Exception as e:
            messagebox.showerror("错误", f"导入失败:\n{str(e)}")

    def import_mod_file(self, file_path):
        """导入MOD文件的核心函数"""
        temp_dir = "temp_mod_extract"
        
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        os.makedirs(temp_dir)
        
        try:
            # 处理压缩包
            if file_path.lower().endswith('.zip'):
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                source_dir = temp_dir
            else:
                # 假设是文件夹或直接文件
                source_dir = file_path
            
            # 查找MOD文件
            found_files = []
            for root, dirs, files in os.walk(source_dir):
                # 查找SeamlessCoop文件夹
                if "SeamlessCoop" in dirs:
                    src = os.path.join(root, "SeamlessCoop")
                    dst = os.path.join(self.game_path, "SeamlessCoop")
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    found_files.append("SeamlessCoop")
                
                # 查找ersc_launcher.exe
                if "ersc_launcher.exe" in files:
                    src = os.path.join(root, "ersc_launcher.exe")
                    dst = os.path.join(self.game_path, "ersc_launcher.exe")
                    shutil.copy2(src, dst)
                    found_files.append("ersc_launcher.exe")
            
            if not found_files:
                raise Exception("未找到有效的MOD文件")
                
        finally:
            # 清理临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
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
    def load_mod_config(self, config_file):
        """加载MOD配置文件"""
        try:
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            
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