import customtkinter as ctk

app = ctk.CTk()
app.title("测试窗口")
app.geometry("200x100")
label = ctk.CTkLabel(app, text="customtkinter 安装成功！")
label.pack(pady=30)
app.mainloop()