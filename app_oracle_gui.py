import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import oracledb
import os
import re

# --- CẤU HÌNH DATABASE (THAY ĐỔI THEO THÔNG TIN CỦA BẠN) ---
DB_USER = "C##QL_TRO"
DB_PASS = "123"
DB_DSN = "localhost:1521/orcl"
# ---------------------------------------------------------

class OracleSQLApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quản Lý Phòng Trọ - Thực Thi Oracle SQL")
        self.root.geometry("800x600")
        self.root.configure(bg="#f0f2f5")

        # Style cho giao diện
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=10, font=("Segoe UI", 10), background="#1877f2", foreground="white")
        style.map("TButton", background=[('active', '#166fe5')])
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), background="#f0f2f5", foreground="#1c1e21")
        style.configure("Log.TLabel", font=("Segoe UI", 9), background="#ffffff")

        # --- Layout ---
        # Header
        header_frame = tk.Frame(root, bg="#f0f2f5", pady=20)
        header_frame.pack(fill=tk.X)
        header_label = ttk.Label(header_frame, text="⚡ QUẢN LÝ THỰC THI SQL ORACLE", style="Header.TLabel")
        header_label.pack()

        # Input Frame (Connection info)
        conn_frame = tk.LabelFrame(root, text="Thông tin kết nối", padx=20, pady=10, bg="#ffffff", font=("Segoe UI", 10, "bold"), fg="#4b4f56")
        conn_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(conn_frame, text="User:", bg="#ffffff").grid(row=0, column=0, sticky=tk.W)
        self.user_entry = tk.Entry(conn_frame, width=20)
        self.user_entry.insert(0, DB_USER)
        self.user_entry.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(conn_frame, text="Password:", bg="#ffffff").grid(row=0, column=2, sticky=tk.W)
        self.pass_entry = tk.Entry(conn_frame, width=20, show="*")
        self.pass_entry.insert(0, DB_PASS)
        self.pass_entry.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(conn_frame, text="DSN:", bg="#ffffff").grid(row=0, column=4, sticky=tk.W)
        self.dsn_entry = tk.Entry(conn_frame, width=30)
        self.dsn_entry.insert(0, DB_DSN)
        self.dsn_entry.grid(row=0, column=5, padx=5, pady=5)

        # Control Frame (Buttons)
        control_frame = tk.Frame(root, bg="#f0f2f5", pady=20)
        control_frame.pack(fill=tk.X, padx=20)

        # Button 1: Thực thi TRO.sql
        btn_schema = ttk.Button(control_frame, text="🚀 Thực thi TRO.sql (Create Table)", 
                               command=lambda: self.execute_sql_file("TRO.sql"))
        btn_schema.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        # Button 2: Thực thi TRO~2.sql
        btn_data = ttk.Button(control_frame, text="📦 Thực thi TRO~2.sql (Data/Proc/Trig)", 
                             command=lambda: self.execute_sql_file("TRO~2.sql"))
        btn_data.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        # Log Frame
        log_frame = tk.LabelFrame(root, text="Báo cáo thực thi (Logs)", padx=10, pady=10, bg="#ffffff", font=("Segoe UI", 10, "bold"), fg="#4b4f56")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.log_text = tk.Text(log_frame, bg="#ffffff", borderwidth=0, font=("Consolas", 10), wrap=tk.WORD)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def parse_sql_script(self, script_text):
        """Tách các lệnh SQL theo dấu ; và các block PL/SQL theo dấu /"""
        # Loại bỏ các dòng chú thích hoặc dòng trắng dư thừa
        lines = script_text.split('\n')
        processed_lines = []
        for line in lines:
            if not line.strip().startswith('--') and line.strip() != "":
                processed_lines.append(line)
        
        full_script = '\n'.join(processed_lines)
        
        # Chiến thuật tách lệnh:
        # Nếu gặp CREATE OR REPLACE (PROCEDURE/FUNCTION/TRIGGER/PACKAGE/BODY) thì tìm dấu / ở dòng riêng biệt
        # Ngược lại tách theo ;
        
        statements = []
        # Regex tìm các khối PL/SQL kết thúc bằng '/' trên dòng mới
        # Cực kỳ quan trọng cho các file SQL Oracle phức tạp
        chunks = re.split(r'\n\s*/\s*\n', full_script)
        
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk: continue
            
            # Nếu trong chunk không chứa từ khóa block (PROCEDURE) và có nhiều ;, tách tiếp
            if not any(k in chunk.upper() for k in ["PROCEDURE", "FUNCTION", "TRIGGER", "PACKAGE", "BODY", "DECLARE", "BEGIN"]):
                sub_stmt = chunk.split(';')
                for s in sub_stmt:
                    if s.strip():
                        statements.append(s.strip())
            else:
                # Giữ nguyên block PL/SQL (xóa ; cuối cùng nếu có trước / )
                if chunk.endswith(';'):
                    statements.append(chunk[:-1].strip())
                else:
                    statements.append(chunk)

        # Lọc lại để loại bỏ phím tắt hoặc dấu thừa
        statements = [s for s in statements if len(s) > 3]
        return statements

    def execute_sql_file(self, filename):
        user = self.user_entry.get()
        password = self.pass_entry.get()
        dsn = self.dsn_entry.get()

        filePath = os.path.join(os.getcwd(), filename)
        if not os.path.exists(filePath):
            messagebox.showerror("Lỗi", f"Không tìm thấy file: {filename}")
            return

        self.log(f"--- Bắt đầu thực thi: {filename} ---")
        
        connection = None
        try:
            # Kết nối DB
            connection = oracledb.connect(user=user, password=password, dsn=dsn)
            cursor = connection.cursor()
            
            with open(filePath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            statements = self.parse_sql_script(content)
            self.log(f"Tìm thấy {len(statements)} câu lệnh/khối lệnh.")

            success_count = 0
            for i, stmt in enumerate(statements):
                try:
                    # Rút gọn để in log
                    short_stmt = stmt.replace('\n', ' ')[:50] + "..."
                    self.log(f"[{i+1}/{len(statements)}] Đang chạy: {short_stmt}")
                    
                    cursor.execute(stmt)
                    success_count += 1
                except oracledb.Error as e:
                    self.log(f"❌ Lỗi tại lệnh {i+1}: {str(e)}")
                    # Nếu lỗi 'table already exists' (ORA-00955) ta có thể bỏ qua
                    if "ORA-00955" in str(e):
                        self.log("   (Bảng đã tồn tại, tiếp tục...)")
                        success_count += 1
                    else:
                        if not messagebox.askyesno("Tiếp tục?", f"Lỗi: {str(e)}\nBạn có muốn bỏ qua lỗi này và tiếp tục không?"):
                            break
            
            connection.commit()
            self.log(f"\n✅ Hoàn tất! Thành công: {success_count}/{len(statements)}")
            messagebox.showinfo("Thành công", f"Đã thực thi {filename} xong!")

        except Exception as e:
            self.log(f"🔥 LỖI HỆ THỐNG: {str(e)}")
            messagebox.showerror("Lỗi", f"Không thể kết nối hoặc thực thi: {str(e)}")
        finally:
            if connection:
                connection.close()
                self.log("🔌 Đã đóng kết nối Database.")

if __name__ == "__main__":
    root = tk.Tk()
    app = OracleSQLApp(root)
    root.mainloop()
