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
        
    def setup_ui(self):
        self.root.geometry("350x430")

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
        
        self.mod_status_label = tk.Label(mod_frame, 
                                        text="点击'获取MOD状态'按钮检测",
                                        fg="gray")
        self.mod_status_label.pack()

        # 创建一个水平容器放第一行的两个按钮
        top_buttons_frame = tk.Frame(mod_frame)
        top_buttons_frame.pack(fill="x", pady=(0, 10))

        # 左边：导入MOD按钮
        tk.Button(top_buttons_frame, text="导入MOD文件", command=self.import_mod,
                width=20).pack(side="left", padx=5)

        # 右边：MOD配置区域（现在只包含获取状态按钮）
        config_frame = tk.Frame(top_buttons_frame)
        config_frame.pack(side="left", padx=10)

        tk.Button(config_frame, text="获取MOD状态", 
                command=self.check_mod_status).pack()
        
        # 联机密码设置
        pass_frame = tk.Frame(mod_frame)
        pass_frame.pack(fill="x", pady=3)
        
        tk.Label(pass_frame, text="联机密码:").pack(side="left")
        self.password_var = tk.StringVar(value="4820")
        tk.Entry(pass_frame, textvariable=self.password_var, 
                width=10).pack(side="left", padx=5)
        tk.Button(pass_frame, text="修改密码", 
                 command=self.update_password).pack(side="left", padx=5)
        
        # death_debuffs设置
        debuff_frame = tk.Frame(mod_frame)
        debuff_frame.pack(fill="x", pady=3)
        
        tk.Label(debuff_frame, text="死亡惩罚:").pack(side="left")
        tk.Button(debuff_frame, text="启用(1)", 
                 command=lambda: self.set_debuff(1)).pack(side="left", padx=5)
        tk.Button(debuff_frame, text="禁用(0)", 
                 command=lambda: self.set_debuff(0)).pack(side="left")
        
        # 存档管理区域
        save_frame = tk.LabelFrame(self.root, text="存档管理", padx=10, pady=5)
        save_frame.pack(fill="x", padx=20, pady=10)
        
        # 导入存档按钮
        tk.Button(save_frame, text="导入存档", command=self.import_save,
                 width=15).pack(side="left", padx=5)
        
        # 导出存档按钮
        tk.Button(save_frame, text="导出存档", command=self.export_save,
                 width=15).pack(side="left", padx=5)
        
        # 状态栏
        self.status_bar = tk.Label(self.root, text="就绪", bd=1, 
                                  relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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
    
    def import_mod(self):
        """导入MOD文件"""
        if not os.path.exists(self.game_path):
            messagebox.showerror("错误", "请先找到游戏路径！")
            return
        
        # 选择MOD文件或文件夹
        file_path = filedialog.askopenfilename(
            title="选择MOD文件（支持.zip, .rar, .7z或文件夹）",
            filetypes=[("所有文件", "*.*"), ("ZIP文件", "*.zip"), 
                      ("RAR文件", "*.rar"), ("7Z文件", "*.7z")]
        )
        
        if not file_path:
            return
        
        self.status("正在导入MOD...")
        
        try:
            # 处理压缩包
            if file_path.lower().endswith(('.zip', '.rar', '.7z')):
                self.extract_and_copy_mod(file_path)
            # 处理文件夹
            elif os.path.isdir(file_path):
                self.copy_mod_from_folder(file_path)
            else:
                # 单个文件
                shutil.copy2(file_path, self.game_path)
            
            self.status("MOD导入完成！")
            messagebox.showinfo("成功", "MOD导入完成！")
            self.check_mod_status()  # 重新检测状态
            
        except Exception as e:
            self.status(f"导入失败: {str(e)}")
            messagebox.showerror("错误", f"导入失败:\n{str(e)}")
    
    def extract_and_copy_mod(self, archive_path):
        """解压并复制MOD文件"""
        temp_dir = "temp_mod_extract"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        os.makedirs(temp_dir)
        
        # 解压文件
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        
        # 查找MOD文件
        mod_files = []
        for root, dirs, files in os.walk(temp_dir):
            # 查找SeamlessCoop文件夹和ersc_launcher.exe
            if "SeamlessCoop" in dirs:
                mod_files.append(os.path.join(root, "SeamlessCoop"))
            if "ersc_launcher.exe" in files:
                mod_files.append(os.path.join(root, "ersc_launcher.exe"))
            
            # 如果当前目录就有这些文件
            for file in files:
                if file in ["ersc_launcher.exe", "SeamlessCoop.dll"]:
                    mod_files.append(os.path.join(root, file))
        
        # 如果没有找到特定文件，使用所有文件
        if not mod_files:
            mod_files = [temp_dir]
        
        # 复制到游戏目录
        for item in mod_files:
            dest = os.path.join(self.game_path, os.path.basename(item))
            if os.path.isdir(item):
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
    
    def copy_mod_from_folder(self, folder_path):
        """从文件夹复制MOD文件"""
        for item in os.listdir(folder_path):
            src = os.path.join(folder_path, item)
            dest = os.path.join(self.game_path, item)
            
            if os.path.isdir(src):
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
    
    def check_mod_status(self):
        """检查MOD状态"""
        mod_folder = os.path.join(self.game_path, "SeamlessCoop")
        config_file = os.path.join(mod_folder, "ersc_settings.ini")
        
        if not os.path.exists(mod_folder):
            self.mod_status_label.config(text="未检测到MOD文件", fg="red")
            return
        
        if not os.path.exists(config_file):
            self.mod_status_label.config(text="找到MOD但缺少配置文件", fg="orange")
            return
        
        self.mod_config_path = config_file
        
        try:
            config = configparser.ConfigParser()
            config.read(config_file, encoding='utf-8')
            
            debuff = config.get('settings', 'death_debuffs', fallback='未找到')
            password = config.get('settings', 'cooppassword', fallback='未找到')
            
            status_text = f"死亡惩罚: {debuff} | 联机密码: {password}"
            self.mod_status_label.config(text=status_text, fg="green")
            
            # 更新密码输入框
            if password != '未找到' and password.isdigit():
                self.password_var.set(password)
                
        except Exception as e:
            self.mod_status_label.config(text=f"读取配置失败: {str(e)}", fg="red")
    
    def update_password(self):
        """更新联机密码"""
        if not self.mod_config_path:
            messagebox.showwarning("警告", "请先检测MOD状态")
            return
        
        new_password = self.password_var.get().strip()
        if not new_password.isdigit() or len(new_password) != 4:
            messagebox.showwarning("警告", "请输入4位数字密码")
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(self.mod_config_path, encoding='utf-8')
            
            if not config.has_section('settings'):
                config.add_section('settings')
            
            config.set('settings', 'cooppassword', new_password)
            
            with open(self.mod_config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            self.status(f"密码已更新为: {new_password}")
            self.check_mod_status()  # 刷新显示
            
        except Exception as e:
            messagebox.showerror("错误", f"更新密码失败:\n{str(e)}")
    
    def set_debuff(self, value):
        """设置death_debuffs值"""
        if not self.mod_config_path:
            messagebox.showwarning("警告", "请先检测MOD状态")
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(self.mod_config_path, encoding='utf-8')
            
            if not config.has_section('settings'):
                config.add_section('settings')
            
            config.set('settings', 'death_debuffs', str(value))
            
            with open(self.mod_config_path, 'w', encoding='utf-8') as f:
                config.write(f)
            
            self.status(f"死亡惩罚已设置为: {value}")
            self.check_mod_status()  # 刷新显示
            
        except Exception as e:
            messagebox.showerror("错误", f"设置失败:\n{str(e)}")
    
    def import_save(self):
        """导入存档"""
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        
        # 让用户选择文件
        file_path = filedialog.askopenfilename(
            title="选择存档文件（可同时选择文件夹）",
            filetypes=[("ZIP文件", "*.zip"), ("RAR文件", "*.rar"), ("所有文件", "*.*")]
        )
        
        # 如果用户取消了选择，尝试让他们选择文件夹
        if not file_path:
            file_path = filedialog.askdirectory(
                title="选择存档文件夹"
            )
        
        if not file_path:
            return
        
        self.status("正在导入存档...")
        
        try:
            # 备份原存档
            backup_path = os.path.join(os.path.dirname(self.save_path), 
                                      "EldenRing_backup")
            if os.path.exists(self.save_path):
                if os.path.exists(backup_path):
                    shutil.rmtree(backup_path)
                shutil.copytree(self.save_path, backup_path)
            
            # 处理不同格式
            if os.path.isdir(file_path):
                # 如果是文件夹
                self.copy_save_from_folder(file_path)
            elif file_path.lower().endswith('.zip'):
                # 解压ZIP
                self.extract_save(file_path)
            else:
                # 其他情况
                messagebox.showwarning("警告", "请选择ZIP文件或EldenRing文件夹")
                return
            
            self.status("存档导入完成！")
            messagebox.showinfo("成功", "存档导入完成！原存档已备份")
            
        except Exception as e:
            self.status(f"导入失败: {str(e)}")
            messagebox.showerror("错误", f"导入失败:\n{str(e)}")
    
    def copy_save_from_folder(self, folder_path):
        """从文件夹复制存档"""
        # 检查是否是EldenRing文件夹
        if os.path.basename(folder_path) == "EldenRing":
            save_folder = folder_path
        else:
            # 查找EldenRing子文件夹
            for item in os.listdir(folder_path):
                if item == "EldenRing":
                    save_folder = os.path.join(folder_path, item)
                    break
            else:
                save_folder = folder_path
        
        # 复制文件
        for item in os.listdir(save_folder):
            src = os.path.join(save_folder, item)
            dest = os.path.join(self.save_path, item)
            
            if os.path.isdir(src):
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
    
    def extract_save(self, zip_path):
        """解压存档ZIP文件"""
        temp_dir = "temp_save_extract"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        os.makedirs(temp_dir)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 查找并复制存档
        self.copy_save_from_folder(temp_dir)
        
        # 清理
        shutil.rmtree(temp_dir)
    
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
    
    def open_folder(self, path):
        """打开文件夹"""
        if os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("警告", "路径不存在！")
    
    def status(self, message):
        """更新状态栏"""
        self.status_bar.config(text=message)
        self.root.update()
    
    def run(self):
        """运行程序"""
        self.root.mainloop()

if __name__ == "__main__":
    # 使用mini界面
    app = EldenRingTool(ui_type="normal")

    # 或者使用原版界面
    # app = EldenRingTool(ui_type="normal")
    # 或者不传参数，默认使用mini（因为默认值设为"mini"）
    # app = EldenRingTool()
    app.run()