import flet as ft
import os
import shutil
import json
import subprocess
from datetime import datetime


class EldenRingSaveManager:
    """艾尔登法环存档管理器"""
    
    def __init__(self):
        """初始化应用程序"""
        self.config_file = "config.json"
        self.config = self.load_config()
        
        # 全局变量
        self.save_path = os.path.expanduser("~\\AppData\\Roaming\\EldenRing")
        self.auto_save_enabled = self.config.get("auto_save_enabled", True)
        self.selected_save = None
        
        # UI组件引用（用于在不同方法中访问和更新这些组件）
        self.save_combo = None          # 存档选择下拉框 - 用于显示和选择存档列表
        self.save_status_label = None   # 存档状态标签 - 显示当前选中存档的状态（如"存档合法"、"存档异常"等）
        self.path_status_label = None   # 路径状态标签 - 显示存档路径的检测结果（如"存档路径 ✓ (有存档)"、"存档路径 ✗ (不存在)"等）
        self.launch_btn = None          # 启动游戏按钮 - 用于启动 launchmod_eldenring.bat 脚本
        self.launch_status_label = None # 启动状态标签 - 显示启动脚本的检测状态（如"可启动游戏"、"未找到启动脚本"等）
        self.auto_save_checkbox = None  # 自动保存复选框 - 控制是否启用自动备份功能的开关

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
        self.config["auto_save_enabled"] = self.auto_save_enabled
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def status_message(self, page, message):
        """显示状态消息"""
        page.snack_bar = ft.SnackBar(ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def create_ui(self, page: ft.Page):
        """创建UI界面"""
        page.title = "艾尔登法环存档管理器"
        page.window.width = 400
        page.window.height = 600
        page.window_resizable = False
        page.window.frameless = True
        page.padding = 15

        # 路径信息区域
        path_info = self.create_path_section(page)
        
        # 存档管理区域
        save_management = self.create_save_section(page)
        
        # 启动游戏区域
        launch_section = self.create_launch_section(page)
        
        # 组合所有区域
        page.add(
            path_info,
            ft.Divider(height=1, color="transparent"),
            save_management,
            ft.Divider(height=1, color="transparent"),
            launch_section
        )
        
        # 初始化操作
        self.auto_detect_paths(page)
        self.ensure_save_directories()
        self.refresh_save_list(page)

    def create_path_section(self, page: ft.Page):
        """创建路径信息区域"""
        # 存档路径显示
        self.path_status_label = ft.Text("正在检测...", size=12, color="grey")

        # 包装在 GestureDetector 中使其可点击
        clickable_path_label = ft.GestureDetector(
            content=self.path_status_label,
            on_tap=lambda e: self.on_path_label_click(e, page),
            mouse_cursor=ft.MouseCursor.CLICK  # 鼠标悬停时显示手型光标
        )
        
        path_column = ft.Column([
            ft.Row([
                ft.Text("存档路径:", weight=ft.FontWeight.BOLD, width=80),
                clickable_path_label  # ← 关键修正：使用可点击版本
            ]),
            ft.Row([
                ft.TextButton(
                    "打开工作目录",
                    on_click=lambda e: self.open_folder(os.getcwd()),
                    style=ft.ButtonStyle(color="blue")
                ),
                ft.Container(expand=True),  # 占位符用于右对齐
                ft.TextButton(
                    "重新检测路径",
                    on_click=lambda e: self.auto_detect_paths(page),
                    style=ft.ButtonStyle(color="blue")
                )
            ])
        ])
        
        return ft.Container(
            content=ft.Column([
                ft.Text("路径信息", weight=ft.FontWeight.BOLD, size=16),
                path_column
            ]),
            padding=10,
            border=ft.border.all(1, "outline-variant"),
            border_radius=8
        )
    
    def on_path_label_click(self, e, page):
        """路径标签点击事件处理"""
        # 这里添加您想要的点击逻辑
        # 例如：打开存档文件夹
        if os.path.exists(self.save_path):
            os.startfile(self.save_path)
        else:
            page.snack_bar = ft.SnackBar(ft.Text("存档路径不存在！"))
            page.snack_bar.open = True
            page.update()

    def create_save_section(self, page: ft.Page):
        """创建存档管理区域"""
        # 存档下拉框
        self.save_combo = ft.Dropdown(
            width=300,
            hint_text="选择存档...",
            on_change=lambda e: self.on_save_selected(page, e.data)
        )
        
        # 状态标签
        self.save_status_label = ft.Text("未选择存档", size=12, color="grey")
        
        # 自动保存复选框
        self.auto_save_checkbox = ft.Checkbox(
            label="启用自动保存",
            value=self.auto_save_enabled,
            on_change=lambda e: self.toggle_auto_save(page, e.control.value)
        )
        
        save_column = ft.Column([
            ft.Row([ft.Text("选择存档:"), self.save_combo]),
            ft.Row([self.save_status_label, ft.Container(expand=True), 
                   ft.TextButton("刷新", on_click=lambda e: self.refresh_save_list(page))]),
            ft.Row([
                ft.ElevatedButton("导入存档", on_click=lambda e: self.import_selected_save(page)),
                ft.Checkbox(label="直接覆盖", value=True, width=120),
                ft.ElevatedButton("导出存档", on_click=lambda e: self.export_current_save(page))
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            self.auto_save_checkbox
        ])
        
        return ft.Container(
            content=ft.Column([
                ft.Text("存档管理", weight=ft.FontWeight.BOLD, size=16),
                save_column
            ]),
            padding=10,
            border=ft.border.all(1, "outline-variant"),
            border_radius=8
        )

    def create_launch_section(self, page: ft.Page):
        """创建启动游戏区域"""
        # 启动按钮
        self.launch_btn = ft.ElevatedButton(
            "启动游戏",
            on_click=lambda e: self.launch_game(page),
            disabled=True,
            width=200
        )
        
        # 状态标签
        self.launch_status_label = ft.Text("未找到启动脚本", size=12, color="red")
        
        launch_column = ft.Column([
            ft.Row([self.launch_btn], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                self.launch_status_label,
                ft.Container(expand=True),
                ft.TextButton("刷新状态", on_click=lambda e: self.refresh_launch_status(page))
            ])
        ])
        
        return ft.Container(
            content=ft.Column([
                ft.Text("启动游戏", weight=ft.FontWeight.BOLD, size=16),
                launch_column
            ]),
            padding=10,
            border=ft.border.all(1, "outline-variant"),
            border_radius=8
        )

    def auto_detect_paths(self, page: ft.Page):
        """自动检测路径"""
        if os.path.exists(self.save_path):
            # 检查存档状态
            has_save = self.check_save_exists(self.save_path)
            if has_save:
                self.path_status_label.value = "存档路径 ✓ (有存档)"
                self.path_status_label.color = "green"
            else:
                self.path_status_label.value = "存档路径 ✓ (无存档)"
                self.path_status_label.color = "orange"
        else:
            self.path_status_label.value = "存档路径 ✗ (不存在)"
            self.path_status_label.color = "red"
        
        page.update()

    def check_save_exists(self, save_dir):
        """检查存档是否存在"""
        if not os.path.exists(save_dir):
            return False
        
        for item in os.listdir(save_dir):
            item_path = os.path.join(save_dir, item)
            if os.path.isdir(item_path) and item.isdigit() and len(item) == 17:
                files = os.listdir(item_path)
                if any(f.startswith('ER') for f in files):
                    return True
        return False

    def ensure_save_directories(self):
        """确保存档目录存在"""
        if not os.path.exists("saves"):
            os.makedirs("saves", exist_ok=True)
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path, exist_ok=True)

    def refresh_save_list(self, page: ft.Page):
        """刷新存档列表"""
        saves_dir = "saves"
        if not os.path.exists(saves_dir):
            os.makedirs(saves_dir, exist_ok=True)
            self.save_combo.options = []
            self.save_status_label.value = "存档目录已创建"
            self.save_status_label.color = "orange"
            page.update()
            return
        
        save_folders = []
        for item in os.listdir(saves_dir):
            item_path = os.path.join(saves_dir, item)
            if os.path.isdir(item_path):
                save_folders.append(item)
        
        save_folders.sort(key=lambda x: os.path.getmtime(os.path.join(saves_dir, x)), reverse=True)
        
        self.save_combo.options = [ft.dropdown.Option(folder) for folder in save_folders]
        self.save_combo.value = None
        self.selected_save = None
        
        if save_folders:
            self.save_status_label.value = f"找到{len(save_folders)}个存档"
            self.save_status_label.color = "green"
        else:
            self.save_status_label.value = "无可用存档"
            self.save_status_label.color = "grey"
        
        page.update()

    def on_save_selected(self, page: ft.Page, selected_value):
        """当选择存档时"""
        self.selected_save = selected_value
        if not selected_value:
            self.save_status_label.value = "未选择存档"
            self.save_status_label.color = "grey"
            page.update()
            return
        
        saves_dir = "saves"
        selected_path = os.path.join(saves_dir, selected_value)
        is_valid = self.check_save_validity(selected_path)
        
        if is_valid:
            self.save_status_label.value = "存档合法"
            self.save_status_label.color = "green"
        else:
            self.save_status_label.value = "存档异常"
            self.save_status_label.color = "red"
        
        page.update()

    def check_save_validity(self, save_path):
        """检查存档合法性"""
        if not os.path.exists(save_path):
            return False
        
        eldenring_path = os.path.join(save_path, "EldenRing")
        if os.path.exists(eldenring_path):
            return self._check_eldenring_folder(eldenring_path)
        else:
            return self._check_direct_save_files(save_path)

    def _check_eldenring_folder(self, eldenring_path):
        """检查EldenRing文件夹结构"""
        steam_id_found = False
        for item in os.listdir(eldenring_path):
            item_path = os.path.join(eldenring_path, item)
            if os.path.isdir(item_path) and item.isdigit() and len(item) == 17:
                files = os.listdir(item_path)
                if any(f.startswith('ER') for f in files):
                    steam_id_found = True
                    break
        return steam_id_found

    def _check_direct_save_files(self, save_path):
        """检查直接存档文件结构"""
        steam_id_found = False
        for item in os.listdir(save_path):
            item_path = os.path.join(save_path, item)
            if os.path.isdir(item_path) and item.isdigit() and len(item) == 17:
                files = os.listdir(item_path)
                if any(f.startswith('ER') for f in files):
                    steam_id_found = True
                    break
        return steam_id_found

    def backup_current_save(self):
        """备份当前存档"""
        if not os.path.exists(self.save_path) or not os.listdir(self.save_path):
            return False, "存档目录为空，无需备份"
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir_name = f"{timestamp}_auto_backup"
            backup_dir = os.path.join("saves", backup_dir_name)
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_target = os.path.join(backup_dir, "EldenRing")
            shutil.copytree(self.save_path, backup_target)
            
            return True, f"自动备份成功: {backup_dir_name}"
        except Exception as e:
            return False, f"备份失败: {str(e)}"

    def import_selected_save(self, page: ft.Page):
        """导入选中的存档"""
        if not self.selected_save:
            self.status_message(page, "请先选择存档")
            return
        
        # 简化版确认对话框（Flet 0.28不支持AlertDialog）
        def confirm_import():
            page.dialog.open = False
            page.update()
            
            try:
                selected_path = os.path.join("saves", self.selected_save)
                source_path = os.path.join(selected_path, "EldenRing")
                if not os.path.exists(source_path):
                    source_path = selected_path
                
                # 清理目标目录
                if os.path.exists(self.save_path):
                    shutil.rmtree(self.save_path)
                os.makedirs(self.save_path)
                
                # 复制文件
                for item in os.listdir(source_path):
                    src = os.path.join(source_path, item)
                    dst = os.path.join(self.save_path, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                self.refresh_save_list(page)
                self.auto_detect_paths(page)
                self.status_message(page, "存档导入完成！")
                
            except Exception as e:
                self.status_message(page, f"导入失败: {str(e)}")

        # 创建简单的确认对话框
        confirm_dialog = ft.Container(
            content=ft.Column([
                ft.Text("请确保游戏已关闭，是否继续？"),
                ft.Row([
                    ft.ElevatedButton("取消", on_click=lambda e: setattr(page.dialog, 'open', False)),
                    ft.ElevatedButton("确定", on_click=lambda e: confirm_import())
                ], alignment=ft.MainAxisAlignment.END)
            ]),
            padding=20,
            bgcolor="white",
            border_radius=8,
            width=300
        )
        
        page.dialog = ft.Container(
            content=confirm_dialog,
            bgcolor="black",
            opacity=0.7,
            expand=True,
            alignment=ft.alignment.center
        )
        page.dialog.open = True
        page.update()

    def export_current_save(self, page: ft.Page):
        """导出当前存档"""
        if not os.path.exists(self.save_path) or not os.listdir(self.save_path):
            self.status_message(page, "当前无存档可导出")
            return
        
        # 使用系统文件选择器
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()
            folder_path = filedialog.askdirectory(title="选择导出位置", initialdir="saves")
            root.destroy()
            
            if folder_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_dir_name = f"{timestamp}_manual_backup"
                export_dir = os.path.join(folder_path, export_dir_name)
                os.makedirs(export_dir, exist_ok=True)
                
                export_target = os.path.join(export_dir, "EldenRing")
                os.makedirs(export_target, exist_ok=True)
                
                for item in os.listdir(self.save_path):
                    src = os.path.join(self.save_path, item)
                    dst = os.path.join(export_target, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                self.status_message(page, f"存档已导出到:\n{export_dir}")
        except Exception as e:
            self.status_message(page, f"导出失败: {str(e)}")

    def toggle_auto_save(self, page: ft.Page, value):
        """切换自动保存功能"""
        self.auto_save_enabled = value
        self.save_config()
        status = "已启用" if value else "已禁用"
        self.status_message(page, f"自动保存功能 {status}")

    def refresh_launch_status(self, page: ft.Page):
        """刷新启动游戏状态"""
        launch_script = os.path.join(os.getcwd(), "launchmod_eldenring.bat")
        if os.path.exists(launch_script):
            self.launch_btn.disabled = False
            self.launch_status_label.value = "可启动游戏"
            self.launch_status_label.color = "green"
        else:
            self.launch_btn.disabled = True
            self.launch_status_label.value = "未找到启动脚本"
            self.launch_status_label.color = "red"
        page.update()

    def launch_game(self, page: ft.Page):
        """启动游戏"""
        launch_script = os.path.join(os.getcwd(), "launchmod_eldenring.bat")
        if not os.path.exists(launch_script):
            self.status_message(page, f"未找到启动脚本:\n{launch_script}")
            return
        
        try:
            subprocess.Popen([launch_script], cwd=os.getcwd())
            self.status_message(page, "游戏启动中...")
        except Exception as e:
            self.status_message(page, f"启动游戏失败:\n{str(e)}")

    def open_folder(self, path):
        """打开指定文件夹"""
        if os.path.exists(path):
            os.startfile(path)


def main(page: ft.Page):
    """Flet应用主函数"""
    app = EldenRingSaveManager()
    app.create_ui(page)


if __name__ == "__main__":
    ft.app(target=main)