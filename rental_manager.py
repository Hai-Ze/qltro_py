from flask import Flask, render_template, request, jsonify, Response
import oracledb
import datetime

app = Flask(__name__)

# --- CẤU HÌNH DATABASE ---
DB_CONFIG = {
    "user": "C##QL_TRO",
    "password": "123",
    "dsn": "localhost:1521/orcl"
}

def get_db_connection():
    try:
        conn = oracledb.connect(
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            dsn=DB_CONFIG['dsn']
        )
        return conn
    except Exception as e:
        print(f"Lỗi kết nối: {str(e)}")
        return None

# --- API ENDPOINTS ---

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Không thể kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Sử dụng VIEW V_DS_PHONG đã định nghĩa trong SQL
        cursor.execute("SELECT MA_PHONG, TEN_PHONG, GIA, SO_NGUOI_TOI_DA, SO_NGUOI, TRANG_THAI FROM V_DS_PHONG ORDER BY MA_PHONG")
        columns = [col[0] for col in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(data)
    finally:
        conn.close()

@app.route('/api/contracts', methods=['GET'])
def get_contracts():
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Không thể kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MA_HD, MA_PHONG, TO_CHAR(NGAY_BAT_DAU, 'DD/MM/YYYY'), TO_CHAR(NGAY_KET_THUC, 'DD/MM/YYYY'), TIEN_COC, TRANG_THAI FROM HOP_DONG ORDER BY MA_HD DESC")
        data = []
        for row in cursor.fetchall():
            data.append({
                "ma_hd": row[0], "ma_phong": row[1], "bat_dau": row[2], 
                "ket_thuc": row[3], "tien_coc": row[4], "trang_thai": row[5]
            })
        return jsonify(data)
    finally:
        conn.close()

@app.route('/api/create-contract', methods=['POST'])
def create_contract():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Gọi Procedure P_TAO_HOPDONG
        cursor.callproc("P_TAO_HOPDONG", [int(data['ma_phong']), float(data['tien_coc'])])
        conn.commit()
        return jsonify({"success": True, "message": "Tạo hợp đồng thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/add-tenant', methods=['POST'])
def add_tenant():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Bước 1: Kiểm tra xem người thuê có tồn tại không, nếu không thì tạo mới (Giả lập logic)
        # Ở đây ta giả sử MA_NGUOI đã có hoặc ta dùng sequence
        # Gọi Procedure P_THEM_NGUOI
        cursor.callproc("P_THEM_NGUOI", [int(data['ma_hd']), int(data['ma_nguoi'])])
        conn.commit()
        return jsonify({"success": True, "message": "Thêm người thuê thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/payment', methods=['POST'])
def payment():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Gọi Procedure P_THANH_TOAN
        cursor.callproc("P_THANH_TOAN", [int(data['ma_hd']), float(data['so_tien']), data['noi_dung']])
        conn.commit()
        return jsonify({"success": True, "message": "Thanh toán thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/tenants', methods=['GET'])
def get_tenants():
    conn = get_db_connection()
    if not conn: return jsonify([])
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MA_NGUOI, TEN, CCCD FROM NGUOI_THUE ORDER BY MA_NGUOI")
        data = [{"ma_nguoi": r[0], "ten": r[1], "cccd": r[2]} for r in cursor.fetchall()]
        return jsonify(data)
    finally:
        if conn: conn.close()

@app.route('/api/top-contracts', methods=['GET'])
def get_top_contracts():
    conn = get_db_connection()
    if not conn: return jsonify([])
    try:
        cursor = conn.cursor()
        # Gọi Procedure P_TOP_HOPDONG trong PKG_PHONG_TRO
        # Procedure trả về một SYS_REFCURSOR
        ref_cursor = cursor.var(oracledb.CURSOR)
        cursor.callproc("PKG_PHONG_TRO.P_TOP_HOPDONG", [ref_cursor, 5])
        
        results = ref_cursor.value.fetchall()
        data = [{"ma_hd": r[0], "ma_phong": r[1], "tong_tien": r[2]} for r in results]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/contract-total/<int:ma_hd>', methods=['GET'])
def get_contract_total(ma_hd):
    conn = get_db_connection()
    if not conn: return jsonify({"tong_tien": 0})
    try:
        cursor = conn.cursor()
        # Gọi Function F_TONG_TIEN
        total = cursor.callfunc("F_TONG_TIEN", oracledb.NUMBER, [ma_hd])
        return jsonify({"ma_hd": ma_hd, "tong_tien": total})
    finally:
        if conn: conn.close()

@app.route('/api/add-asset', methods=['POST'])
def add_asset():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "DB Error"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO TAI_SAN (MA_TS, MA_PHONG, TEN_TS, GIA_TRI) VALUES (SEQ_TT.NEXTVAL, :1, :2, :3)", 
                       [int(data['ma_phong']), data['ten'], float(data['gia_tri'])])
        conn.commit()
        return jsonify({"success": True, "message": "Thêm tài sản thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/update-asset', methods=['POST'])
def update_asset():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE TAI_SAN SET TEN_TS = :1, GIA_TRI = :2 WHERE MA_TS = :3", 
                       [data['ten'], float(data['gia_tri']), int(data['ma'])])
        conn.commit()
        return jsonify({"success": True, "message": "Cập nhật tài sản thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/delete-asset/<int:ma>', methods=['POST'])
def delete_asset(ma):
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Kiểm tra xem có đang gắn với hư hỏng nào không
        cursor.execute("SELECT COUNT(*) FROM HU_HONG WHERE MA_TS = :1", [ma])
        if cursor.fetchone()[0] > 0:
            return jsonify({"success": False, "message": "Không thể xóa tài sản đã có lịch sử hư hại!"})
        cursor.execute("DELETE FROM TAI_SAN WHERE MA_TS = :1", [ma])
        conn.commit()
        return jsonify({"success": True, "message": "Xóa tài sản thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/delete-damage/<int:ma>', methods=['POST'])
def delete_damage(ma):
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM HU_HONG WHERE MA_HH = :1", [ma])
        conn.commit()
        return jsonify({"success": True, "message": "Xóa bản ghi hư hỏng thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/check-spot/<int:ma_hd>', methods=['GET'])
def check_spot(ma_hd):
    conn = get_db_connection()
    if not conn: return jsonify({"has_spot": False})
    try:
        cursor = conn.cursor()
        res = cursor.callfunc("F_CON_CHO", oracledb.NUMBER, [ma_hd])
        return jsonify({"ma_hd": ma_hd, "has_spot": bool(res)})
    finally:
        if conn: conn.close()

# --- BỔ SUNG QUẢN LÝ TÀI SẢN & HƯ HỎNG ---

@app.route('/api/assets/<int:ma_phong>', methods=['GET'])
def get_assets(ma_phong):
    conn = get_db_connection()
    if not conn: return jsonify([])
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MA_TS, TEN_TS, GIA_TRI FROM TAI_SAN WHERE MA_PHONG = :1", [ma_phong])
        data = [{"ma_ts": r[0], "ten_ts": r[1], "gia_tri": r[2]} for r in cursor.fetchall()]
        return jsonify(data)
    finally:
        if conn: conn.close()

@app.route('/api/damages', methods=['GET'])
def get_damages():
    conn = get_db_connection()
    if not conn: return jsonify([])
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT H.MA_HH, T.TEN_TS, P.TEN_PHONG, H.NGAY_HH, H.BOI_THUONG 
            FROM HU_HONG H 
            JOIN TAI_SAN T ON H.MA_TS = T.MA_TS
            JOIN PHONG P ON T.MA_PHONG = P.MA_PHONG
        """)
        data = [{"ma_hh": r[0], "ten_ts": r[1], "ten_phong": r[2], "ngay": str(r[3]), "tien": r[4]} for r in cursor.fetchall()]
        return jsonify(data)
    finally:
        if conn: conn.close()

@app.route('/api/report-damage', methods=['POST'])
def report_damage():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Giả định dùng sequence hoặc ID tự tăng cho HU_HONG
        cursor.execute("INSERT INTO HU_HONG (MA_HH, MA_TS, NGAY_HH, BOI_THUONG) VALUES (SEQ_TT.NEXTVAL, :1, SYSDATE, :2)", 
                       [int(data['ma_ts']), float(data['boi_thuong'])])
        conn.commit()
        return jsonify({"success": True, "message": "Báo cáo hư hỏng thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/end-contract/<int:ma_hd>', methods=['POST'])
def end_contract(ma_hd):
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # 1. Cập nhật trạng thái hợp đồng thành HET_HAN
        cursor.execute("UPDATE HOP_DONG SET TRANG_THAI = 'HET_HAN' WHERE MA_HD = :1", [ma_hd])
        # 2. Lấy mã phòng từ hợp đồng
        cursor.execute("SELECT MA_PHONG FROM HOP_DONG WHERE MA_HD = :1", [ma_hd])
        row = cursor.fetchone()
        if row:
            ma_phong = row[0]
            # 3. Cập nhật phòng thành TRONG
            cursor.execute("UPDATE PHONG SET TRANG_THAI = 'TRONG' WHERE MA_PHONG = :1", [ma_phong])
        conn.commit()
        return jsonify({"success": True, "message": "Đã kết thúc hợp đồng và giải phóng phòng!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/add-room', methods=['POST'])
def add_room():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Dùng sequence cho MA_PHONG
        cursor.execute("INSERT INTO PHONG (MA_PHONG, TEN_PHONG, GIA, SO_NGUOI_TOI_DA, TRANG_THAI) VALUES (SEQ_PHONG.NEXTVAL, :1, :2, :3, 'TRONG')", 
                       [data['ten'], float(data['gia']), int(data['max_nguoi'])])
        conn.commit()
        return jsonify({"success": True, "message": "Thêm phòng mới thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/add-tenant-master', methods=['POST'])
def add_tenant_master():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO NGUOI_THUE (MA_NGUOI, TEN, CCCD) VALUES (SEQ_NGUOI.NEXTVAL, :1, :2)", 
                       [data['ten'], data['cccd']])
        conn.commit()
        return jsonify({"success": True, "message": "Thêm khách hàng mới thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        if conn: conn.close()

@app.route('/api/export-contracts')
def export_contracts():
    import csv
    from io import StringIO
    conn = get_db_connection()
    if not conn: return "DB Error", 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM HOP_DONG")
        si = StringIO()
        cw = csv.writer(si)
        cw.writerow([d[0] for d in cursor.description])
        cw.writerows(cursor.fetchall())
        response = Response(si.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=contracts.csv'
        return response
    finally:
        if conn: conn.close()

@app.route('/api/update-room', methods=['POST'])
def update_room():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "DB Error"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE PHONG SET TEN_PHONG = :1, GIA = :2, SO_NGUOI_TOI_DA = :3 WHERE MA_PHONG = :4", 
                       [data['ten'], float(data['gia']), int(data['max_nguoi']), int(data['ma'])])
        conn.commit()
        return jsonify({"success": True, "message": "Cập nhật phòng thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/delete-room/<int:ma>', methods=['POST'])
def delete_room(ma):
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Kiểm tra xem phòng có đang gắn với hợp đồng nào không
        cursor.execute("SELECT COUNT(*) FROM HOP_DONG WHERE MA_PHONG = :1", [ma])
        if cursor.fetchone()[0] > 0:
            return jsonify({"success": False, "message": "Không thể xóa phòng đang có lịch sử hợp đồng!"})
        cursor.execute("DELETE FROM PHONG WHERE MA_PHONG = :1", [ma])
        conn.commit()
        return jsonify({"success": True, "message": "Xóa phòng thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/update-tenant', methods=['POST'])
def update_tenant():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE NGUOI_THUE SET TEN = :1, CCCD = :2 WHERE MA_NGUOI = :3", [data['ten'], data['cccd'], int(data['ma'])])
        conn.commit()
        return jsonify({"success": True, "message": "Cập nhật thông tin khách thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/extend-contract', methods=['POST'])
def extend_contract_api():
    data = request.json
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # Cộng thêm số tháng gia hạn
        cursor.execute("UPDATE HOP_DONG SET KET_THUC = ADD_MONTHS(KET_THUC, :1) WHERE MA_HD = :2", 
                       [int(data['months']), int(data['ma_hd'])])
        conn.commit()
        return jsonify({"success": True, "message": f"Gia hạn thêm {data['months']} tháng thành công!"})
    finally:
        if conn: conn.close()

@app.route('/api/contract-details/<int:ma_hd>')
def get_contract_details(ma_hd):
    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "Lỗi kết nối DB"}), 500
    try:
        cursor = conn.cursor()
        # 1. Danh sách người thuê trong Hợp đồng (từ CHI_TIET_THUE join NGUOI_THUE)
        cursor.execute("""
            SELECT N.TEN, N.CCCD 
            FROM CHI_TIET_THUE C 
            JOIN NGUOI_THUE N ON C.MA_NGUOI = N.MA_NGUOI 
            WHERE C.MA_HD = :1
        """, [ma_hd])
        people = [{"ten": r[0], "cccd": r[1]} for r in cursor.fetchall()]

        # 2. Lịch sử thanh toán của Hợp đồng
        cursor.execute("SELECT MA_TT, NGAY_TT, SO_TIEN, NOI_DUNG FROM THANH_TOAN WHERE MA_HD = :1 ORDER BY NGAY_TT DESC", [ma_hd])
        payments = [{"ma": r[0], "ngay": str(r[1]), "tien": r[2], "note": r[3]} for r in cursor.fetchall()]

        return jsonify({"success": True, "people": people, "payments": payments})
    finally:
        if conn: conn.close()

@app.route('/api/revenue-summary')
def get_revenue_summary():
    conn = get_db_connection()
    if not conn: return jsonify({"total": 0})
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(SO_TIEN) FROM THANH_TOAN")
        row = cursor.fetchone()
        return jsonify({"total": row[0] if row[0] else 0})
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
