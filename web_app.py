from flask import Flask, render_template, request, jsonify, Response
import oracledb
import os
import re
import time

app = Flask(__name__)

# --- CẤU HÌNH DATABASE MẶC ĐỊNH ---
DB_CONFIG = {
    "user": "C##QL_TRO",
    "password": "123",
    "dsn": "localhost:1521/orcl"
}

def parse_sql_script(script_text):
    """Tách các lệnh SQL và khối PL/SQL."""
    lines = script_text.split('\n')
    processed_lines = []
    for line in lines:
        if not line.strip().startswith('--') and line.strip() != "":
            processed_lines.append(line)
    
    full_script = '\n'.join(processed_lines)
    
    # Tách các khối PL/SQL kết thúc bằng '/' trên dòng mới
    chunks = re.split(r'\n\s*/\s*\n', full_script)
    statements = []
    
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk: continue
        
        # Nếu là lệnh SQL thường (không chứa PROCEDURE, BEGIN...) thì tách theo ;
        if not any(k in chunk.upper() for k in ["PROCEDURE", "FUNCTION", "TRIGGER", "PACKAGE", "BODY", "DECLARE", "BEGIN"]):
            sub_stmt = chunk.split(';')
            for s in sub_stmt:
                if s.strip():
                    statements.append(s.strip())
        else:
            # Giữ nguyên block PL/SQL
            if chunk.endswith(';'):
                statements.append(chunk[:-1].strip())
            else:
                statements.append(chunk)

    return [s for s in statements if len(s) > 3]

@app.route('/')
def index():
    return render_template('index.html', config=DB_CONFIG)

@app.route('/execute', methods=['POST'])
def execute():
    filename = request.json.get('filename')
    config = request.json.get('config', DB_CONFIG)
    
    filePath = os.path.join(os.getcwd(), filename)
    if not os.path.exists(filePath):
        return jsonify({"success": False, "error": f"Không tìm thấy file: {filename}"})

    def generate():
        yield f"data: --- Bắt đầu thực thi: {filename} ---\n\n"
        connection = None
        try:
            connection = oracledb.connect(
                user=config['user'], 
                password=config['password'], 
                dsn=config['dsn']
            )
            cursor = connection.cursor()
            
            with open(filePath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            statements = parse_sql_script(content)
            yield f"data: Tìm thấy {len(statements)} câu lệnh.\n\n"

            success_count = 0
            for i, stmt in enumerate(statements):
                short_stmt = stmt.replace('\n', ' ')[:50] + "..."
                yield f"data: [{i+1}/{len(statements)}] Đang chạy: {short_stmt}\n\n"
                
                try:
                    cursor.execute(stmt)
                    success_count += 1
                except oracledb.Error as e:
                    err_msg = str(e).replace('\n', ' ')
                    if "ORA-00955" in err_msg:
                        yield f"data: [INFO] Bảng đã tồn tại.\n\n"
                        success_count += 1
                    else:
                        yield f"data: [ERROR] Lỗi tại lệnh {i+1}: {err_msg}\n\n"
                        # Ghi log lỗi nhưng có thể chọn cách xử lý tiếp theo tùy ý
            
            connection.commit()
            yield f"data: FINISH: ✅ Hoàn tất! Thành công {success_count}/{len(statements)}\n\n"
        except Exception as e:
            yield f"data: [EXCEPTION] 🔥 Lỗi hệ thống: {str(e)}\n\n"
        finally:
            if connection:
                connection.close()
                yield f"data: [INFO] Đã đóng kết nối.\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
