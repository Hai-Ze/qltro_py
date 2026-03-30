
import tkinter as tk
from tkinter import ttk, messagebox
import oracledb
import os
import re

class OracleSchemaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Quản Lý Phòng Trọ - Thực Thi Oracle SQL")
        self.root.geometry("800x600")

        # UI Components
        main_frame = tk.Frame(root, pady=20, padx=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(main_frame, text="⚡ QUẢN LÝ THỰC THI SQL ORACLE", font=("Arial", 18, "bold")).pack(pady=20)

        # Connection Info
        conn_frame = tk.LabelFrame(main_frame, text="Thông tin kết nối", padx=10, pady=10)
        conn_frame.pack(fill=tk.X, pady=10)

        tk.Label(conn_frame, text="User:").grid(row=0, column=0, sticky=tk.W)
        self.user_entry = tk.Entry(conn_frame)
        self.user_entry.insert(0, "C##QL_TRO")
        self.user_entry.grid(row=0, column=1, padx=5)

        tk.Label(conn_frame, text="Password:").grid(row=0, column=2, sticky=tk.W)
        self.pass_entry = tk.Entry(conn_frame, show="*")
        self.pass_entry.insert(0, "123")
        self.pass_entry.grid(row=0, column=3, padx=5)

        tk.Label(conn_frame, text="DSN:").grid(row=0, column=4, sticky=tk.W)
        self.dsn_entry = tk.Entry(conn_frame, width=30)
        self.dsn_entry.insert(0, "localhost:1521/orcl")
        self.dsn_entry.grid(row=0, column=5, padx=5)

        # Buttons
        btn_frame = tk.Frame(main_frame, pady=20)
        btn_frame.pack(fill=tk.X)

        self.btn1 = tk.Button(btn_frame, text="🚀 Thực thi TRO.sql (Create Table)", 
                               command=lambda: self.execute_sql_file("TRO.sql"), 
                               bg="#1e88e5", fg="white", font=("Arial", 10, "bold"), height=2, width=30)
        self.btn1.pack(side=tk.LEFT, padx=10)

        self.btn2 = tk.Button(btn_frame, text="📦 Thực thi TRO~2.sql (Data/Proc/Trig)", 
                               command=lambda: self.execute_sql_file("TRO~2.sql"), 
                               bg="#1e88e5", fg="white", font=("Arial", 10, "bold"), height=2, width=30)
        self.btn2.pack(side=tk.LEFT, padx=10)

        self.btn3 = tk.Button(btn_frame, text="🔄 Chuyển đổi qua ERD Mới (Migration)", 
                               command=lambda: self.execute_sql_file("MODERN_ERD_SCHEMA.sql"), 
                               bg="#1e88e5", fg="white", font=("Arial", 10, "bold"), height=2, width=30)
        self.btn3.pack(side=tk.LEFT, padx=10)

        # Logs
        tk.Label(main_frame, text="Báo cáo thực thi (Logs):").pack(anchor=tk.W)
        self.log_text = tk.Text(main_frame, height=15, bg="white", borderwidth=1, relief="solid")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        sb = tk.Scrollbar(self.log_text)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=sb.set)
        sb.config(command=self.log_text.yview)

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def execute_sql_file(self, filename):
        if not os.path.exists(filename):
            messagebox.showerror("Lỗi", f"Không tìm thấy file: {filename}")
            return

        user = self.user_entry.get()
        password = self.pass_entry.get()
        dsn = self.dsn_entry.get()

        self.log_text.delete(1.0, tk.END)
        self.log(f"--- Bắt đầu thực thi file: {filename} ---")
        
        try:
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            cursor = conn.cursor()
            
            with open(filename, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            statements = []
            current_stmt = []
            in_plsql = False
            
            for line in lines:
                clean_line = line.strip()
                if not clean_line or clean_line.startswith('--'):
                    continue
                
                # Kiểm tra bắt đầu khối PL/SQL
                upper_line = clean_line.upper()
                if any(x in upper_line for x in ["BEGIN", "CREATE OR REPLACE FUNCTION", "CREATE OR REPLACE PROCEDURE", "CREATE OR REPLACE TRIGGER"]):
                    in_plsql = True
                
                current_stmt.append(line)
                
                # Check kết thúc
                if in_plsql:
                    if clean_line == '/':
                        stmt = "".join(current_stmt).strip()
                        if stmt.endswith('/'): stmt = stmt[:-1].strip()
                        statements.append(stmt)
                        current_stmt = []
                        in_plsql = False
                else:
                    if clean_line.endswith(';'):
                        stmt = "".join(current_stmt).strip()
                        if stmt.endswith(';'): stmt = stmt[:-1].strip()
                        statements.append(stmt)
                        current_stmt = []
            
            total = 0
            success = 0
            
            for stmt in statements:
                if not stmt: continue
                try:
                    total += 1
                    cursor.execute(stmt)
                    success += 1
                except Exception as e:
                    self.log(f"Lỗi lệnh {total}: {str(e)}")
            
            conn.commit()
            self.log(f"--- Hoàn tất! Thành công: {success}/{total} ---")
            messagebox.showinfo("Hoàn tất", f"Thành công: {success}/{total} lệnh.")
            
        except Exception as e:
            messagebox.showerror("Lỗi kết nối", str(e))
        finally:
            if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = OracleSchemaGUI(root)
    root.mainloop()
