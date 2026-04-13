import os
import shutil
import json
import winreg
from datetime import datetime
import subprocess
import tkinter.messagebox as messagebox
import customtkinter as ctk
from tkinter import filedialog

# 设置 customtkinter 主题和配色
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class EldenRingManager:
    """
    艾尔登法环存档管理器主类
    
    功能包括：
    - 路径信息管理（存档路径、工作目录、路径检测）
    - 存档管理（导入/导出存档，自动保存选项）
    - 游戏启动（通过 launchmod_eldenring.bat 启动）
    """
    
    def __init__(self):
        """初始化应用程序"""
        self.root = ctk.CTk()
        self.root.title("艾尔登法环存档管理器 v1.0")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # 自定义配色方案
        self.colors = {
            "primary_100": "#1F3A5F",
            "primary_200": "#4d648d", 
            "primary_300": "#acc2ef",
            "accent_100": "#3D5A80",
            "accent_200": "#cee8ff",
            "text_100": "#FFFFFF",
            "text_200": "#e0e0e0",
            "bg_100": "#0F1C2E",
            "bg_200": "#1f2b3e",
            "bg_300": "#374357"
        }
        
        # 配置文件路径
        self.config_file = "config.json"
        self.config = self.load_config()
        
        # 全局变量
        self.save_path = os.path.expanduser("~/AppData/Roaming/EldenRing")
        self.auto_save_enabled = self.config.get("auto_save", True)  # 默认启用自动保存
        
        # 创建界面
        self.setup_ui()
        
        # 初始化
        self.ensure_save_dir()
        self.update_path_labels()
        self.refresh_save_list()
        
    def setup_ui(self):
        """设置用户界面布局"""
        title_font = ("Microsoft YaHei", 12, "bold")
        normal_font = ("Microsoft YaHei", 10)

        # 路径信息区域
        path_frame = ctk.CTkFrame(self.root)
        path_frame.pack(fill="x", padx=15, pady=(10, 5))
        
        path_label = ctk.CTkLabel(path_frame, text="路径信息", font=("Microsoft YaHei", 10))
        path_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # 存档路径显示
        save_path_frame = ctk.CTkFrame(path_frame)
        save_path_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(save_path_frame, text="存档路径:",font=("Microsoft YaHei", 10)).pack(side="left")
        self.save_path_label = ctk.CTkLabel(save_path_frame, text="", wraplength=250,font=("Microsoft YaHei", 10))
        self.save_path_label.pack(side="left", padx=(5, 0))
        
        # 工具目录按钮
        tool_dir_btn = ctk.CTkButton(
            path_frame, 
            text="打开工作目录", 
            width=120,
            command=self.open_tool_directory,
            font=("Microsoft YaHei", 10)
        )
        tool_dir_btn.pack(pady=5)
        
        # 重新检测路径按钮
        detect_btn = ctk.CTkButton(
            path_frame,
            text="重新检测路径",
            width=120,
            command=self.auto_detect_paths,
            font=("Microsoft YaHei", 10)
        )
        detect_btn.pack(pady=(0, 10))
        
        # 存档管理区域
        save_frame = ctk.CTkFrame(self.root)
        save_frame.pack(fill="x", padx=15, pady=5)
        
        save_label = ctk.CTkLabel(save_frame, text="存档管理", font=("Microsoft YaHei", 10))
        save_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # 存档选择下拉框
        combo_frame = ctk.CTkFrame(save_frame)
        combo_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(combo_frame, text="选择存档:",font=("Microsoft YaHei", 10)).pack(side="left")
        self.save_combo_var = ctk.StringVar()
        self.save_combo = ctk.CTkComboBox(
            combo_frame,
            variable=self.save_combo_var,
            values=[],
            width=200,
            command=self.on_save_selected,
            font=("Microsoft YaHei", 10),        # 下拉框本身字体
            dropdown_font=("Microsoft YaHei", 10) # 下拉列表字体
        )
        self.save_combo.pack(side="left", padx=(5, 0))
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            combo_frame,
            text="刷新",
            width=60,
            command=self.refresh_save_list,
            font=("Microsoft YaHei", 10)
        )
        refresh_btn.pack(side="right")
        
        # 状态标签
        self.save_status_label = ctk.CTkLabel(
            save_frame, 
            text="未选择存档",
            text_color="gray",
            font=("Microsoft YaHei", 10)
        )
        self.save_status_label.pack(anchor="w", padx=10)
        
        # 导入/导出按钮和自动保存复选框
        action_frame = ctk.CTkFrame(save_frame)
        action_frame.pack(fill="x", padx=10, pady=5)
        
        # 导入存档按钮
        import_btn = ctk.CTkButton(
            action_frame,
            text="导入存档",
            width=100,
            command=self.import_selected_save,
            font=("Microsoft YaHei", 10)
        )
        import_btn.pack(side="left", padx=(0, 10))
        
        # 自动保存复选框
        self.auto_save_var = ctk.BooleanVar(value=self.auto_save_enabled)
        auto_save_check = ctk.CTkCheckBox(
            action_frame,
            text="自动保存",
            variable=self.auto_save_var,
            command=self.toggle_auto_save,
            font=("Microsoft YaHei", 10)
        )
        auto_save_check.pack(side="left", padx=(0, 10))
        
        # 导出存档按钮
        export_btn = ctk.CTkButton(
            action_frame,
            text="导出存档",
            width=100,
            command=self.export_current_save,
            font=("Microsoft YaHei", 10)
        )
        export_btn.pack(side="left")
        
        # 启动游戏区域
        launch_frame = ctk.CTkFrame(self.root)
        launch_frame.pack(fill="x", padx=15, pady=5)
        
        launch_label = ctk.CTkLabel(launch_frame, text="启动游戏", font=("Microsoft YaHei", 10))
        launch_label.pack(anchor="w", padx=10, pady=(5, 0))
        
        # 启动游戏按钮
        self.launch_btn = ctk.CTkButton(
            launch_frame,
            text="启动游戏",
            height=40,
            font=("Microsoft YaHei", 14, "bold"),
            command=self.launch_game
        )
        self.launch_btn.pack(pady=10, padx=10, fill="x")
        
        # 启动状态标签
        self.launch_status_label = ctk.CTkLabel(
            launch_frame,
            text="准备就绪",
            text_color="green",
            font=("Microsoft YaHei", 10)
        )
        self.launch_status_label.pack(pady=(0, 10))
        
        # 状态栏
        self.status_bar = ctk.CTkLabel(
            self.root,
            text="就绪",
            height=25,
            fg_color=self.colors["bg_200"],
            font=("Microsoft YaHei", 10)
        )
        self.status_bar.pack(side="bottom", fill="x")
        
    def status(self, message):
        """更新状态栏消息"""
        self.status_bar.configure(text=message)
        self.root.update()
        
    #region 配置文件相关函数
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return {}
        return {}
    
    def save_config(self):
        """保存配置文件"""
        self.config["auto_save"] = self.auto_save_enabled
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    #endregion
    
    #region 路径管理相关函数
    def ensure_save_dir(self):
        """确保存档目录存在"""
        if not os.path.exists(self.save_path):
            try:
                os.makedirs(self.save_path, exist_ok=True)
                return True
            except Exception as e:
                print(f"创建存档目录失败: {e}")
                return False
        return True
    
    def update_path_labels(self):
        """更新路径标签显示"""
        if os.path.exists(self.save_path):
            self.save_path_label.configure(text=self.save_path)
        else:
            self.save_path_label.configure(text="存档路径不存在")
    
    def auto_detect_paths(self):
        """自动检测路径"""
        self.status("正在检测路径...")
        self.ensure_save_dir()
        self.update_path_labels()
        self.status("路径检测完成")
    
    def open_tool_directory(self):
        """打开工具工作目录"""
        try:
            os.startfile(os.getcwd())
        except Exception as e:
            messagebox.showwarning("警告", f"无法打开目录: {e}")
    #endregion
    
    #region 存档管理相关函数
    def refresh_save_list(self):
        """刷新存档列表"""
        saves_dir = "saves"
        
        # 创建存档目录（如果不存在）
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir, exist_ok=True)
            self.save_combo.configure(values=[])
            self.save_combo_var.set("")
            self.save_status_label.configure(text="存档目录已创建", text_color="orange")
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
            self.save_combo.configure(values=save_folders)
            self.save_combo_var.set("")
            self.save_status_label.configure(text=f"找到{len(save_folders)}个存档", text_color="green")
        else:
            self.save_combo.configure(values=[])
            self.save_combo_var.set("")
            self.save_status_label.configure(text="无可用存档", text_color="gray")
    
    def on_save_selected(self, choice):
        """当选择存档时的处理"""
        if not choice:
            self.save_status_label.configure(text="未选择存档", text_color="gray")
            return
        
        saves_dir = "saves"
        selected_path = os.path.join(saves_dir, choice)
        
        # 检查存档是否合法
        is_valid, status_msg = self.check_save_validity(selected_path)
        
        if is_valid:
            self.save_status_label.configure(text="存档合法", text_color="green")
        else:
            self.save_status_label.configure(text=f"存档异常: {status_msg}", text_color="red")
    
    def check_save_validity(self, save_path):
        """
        检查存档的合法性
        
        Args:
            save_path: 存档文件夹路径
            
        Returns:
            tuple: (is_valid, status_message)
        """
        if not os.path.exists(save_path):
            return False, "存档文件夹不存在"
        
        # 检查存档文件夹结构
        eldenring_path = os.path.join(save_path, "EldenRing")
        
        # 两种情况：有EldenRing文件夹或直接是存档文件
        if os.path.exists(eldenring_path):
            return self._check_eldenring_folder(eldenring_path)
        else:
            return self._check_direct_save_files(save_path)
    
    def _check_eldenring_folder(self, eldenring_path):
        """检查EldenRing文件夹结构"""
        if not os.path.exists(eldenring_path):
            return False, "EldenRing文件夹不存在"
        
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
                        return False, f"SteamID文件夹{item}内无ER文件"
        
        if not steam_id_found:
            return False, "未找到SteamID文件夹"
        
        return True, "存档合法"
    
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
                        return False, f"SteamID文件夹{item}内无ER文件"
        
        if not steam_id_found:
            return False, "未找到SteamID文件夹"
        
        return True, "存档合法"
    
    def backup_current_save(self):
        """
        备份当前存档（用于自动保存功能）
        
        Returns:
            tuple: (success, message)
        """
        if not os.path.exists(self.save_path):
            return False, "存档目录不存在"
        
        # 检查目录是否有内容
        try:
            items = os.listdir(self.save_path)
            if not items:
                return False, "存档目录为空，无需备份"
            
            # 检查是否有有效内容
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
            
            # 复制整个存档
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
        is_valid, status_msg = self.check_save_validity(selected_path)
        if not is_valid:
            messagebox.showwarning("警告", f"存档不合法: {status_msg}")
            return
        
        # 如果启用了自动保存，在导入前先备份当前存档
        if self.auto_save_enabled:
            success, msg = self.backup_current_save()
            if not success:
                # 如果备份失败，询问是否继续
                if not messagebox.askyesno("警告", f"自动备份失败: {msg}\n是否继续导入？"):
                    return
        
        # 导入存档
        try:
            # 确定源路径
            eldenring_source = os.path.join(selected_path, "EldenRing")
            if os.path.exists(eldenring_source):
                source_path = eldenring_source
            else:
                source_path = selected_path
            
            # 清除目标目录
            if os.path.exists(self.save_path):
                shutil.rmtree(self.save_path)
            
            # 复制存档文件
            shutil.copytree(source_path, self.save_path)
            
            # 刷新界面
            self.refresh_save_list()
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
            
            # 创建EldenRing文件夹并复制文件
            export_target = os.path.join(export_dir, "EldenRing")
            shutil.copytree(self.save_path, export_target)
            
            # 如果保存位置是saves目录，则刷新列表
            if os.path.abspath(save_dir) == os.path.abspath("saves"):
                self.refresh_save_list()
            
            messagebox.showinfo("成功", f"存档已导出到:\n{export_dir}")
            self.status(f"存档已导出: {export_dir_name}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")
            self.status(f"导出失败: {str(e)}")
    #endregion
    
    #region 自动保存功能
    def toggle_auto_save(self):
        """切换自动保存功能"""
        self.auto_save_enabled = self.auto_save_var.get()
        self.save_config()
        status = "已启用" if self.auto_save_enabled else "已禁用"
        self.status(f"自动保存功能 {status}")
    #endregion
    
    #region 游戏启动相关函数
    def launch_game(self):
        """启动游戏（通过 launchmod_eldenring.bat）"""
        bat_file = "launchmod_eldenring.bat"
        
        if not os.path.exists(bat_file):
            messagebox.showerror("错误", f"未找到启动文件:\n{bat_file}\n\n请确保该文件与程序在同一目录下")
            return
        
        try:
            # 启动批处理文件
            subprocess.Popen([bat_file], cwd=os.getcwd())
            self.status("游戏启动中...")
            self.launch_status_label.configure(text="游戏已启动", text_color="green")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动游戏失败:\n{str(e)}")
            self.launch_status_label.configure(text="启动失败", text_color="red")
            self.status(f"启动失败: {str(e)}")
    #endregion
    
    def run(self):
        """运行应用程序"""
        self.root.mainloop()


if __name__ == "__main__":
    app = EldenRingManager()
    app.run()