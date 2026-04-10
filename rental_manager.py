
from flask import Flask, render_template, request, jsonify
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
        conn = oracledb.connect(user=DB_CONFIG['user'], password=DB_CONFIG['password'], dsn=DB_CONFIG['dsn'])
        return conn
    except Exception as e:
        print(f"Lỗi kết nối: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('dashboard.html')

# --- API PHÒNG ---
@app.route('/api/rooms', methods=['GET'])
def get_rooms():
    conn = get_db_connection()
    if not conn: return jsonify([])
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM V_DS_PHONG ORDER BY MA_PHONG")
        columns = [col[0].lower() for col in cursor.description]
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(data)
    finally:
        conn.close()

@app.route('/api/room-types', methods=['GET'])
def get_types():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MA_LOAI, TEN, GIA FROM LOAI_PHONG")
        return jsonify([{"ma": r[0], "ten": r[1], "gia": r[2]} for r in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/add-room', methods=['POST'])
def add_room():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO PHONG (MA_PHONG, TEN_PHONG, TRANG_THAI, SO_NGUOI_TOI_DA, TANG, MA_LOAI, DIEN_HT, NUOC_HT)
            VALUES (SEQ_PHONG.NEXTVAL, :1, 'TRONG', :2, :3, :4, 0, 0)
        """, [data['ten_phong'], data['max_nguoi'], data['tang'], data['ma_loai']])
        conn.commit()
        return jsonify({"success": True, "message": "Đã tạo phòng mới!"})
    finally:
        conn.close()

@app.route('/api/add-tenant', methods=['POST'])
def add_tenant():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO NGUOI_THUE (MA_KH, HO_TEN, SDT, CCCD) VALUES (SEQ_KH.NEXTVAL, :1, :2, :3)",
                    [data['ho_ten'], data['sdt'], data['cccd']])
        conn.commit()
        return jsonify({"success": True, "message": "Đã thêm khách hàng mới!"})
    finally:
        conn.close()

# API Lấy danh sách tài sản (kèm ID để xóa)
@app.route('/api/assets/<int:ma_phong>', methods=['GET'])
def get_assets(ma_phong):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MA_TS, TEN_TS, TINH_TRANG, GIA_TRI, TI_LE_MOI FROM TAI_SAN WHERE MA_PHONG = :1", [ma_phong])
        return jsonify([{"ma_ts": r[0], "ten": r[1], "tinh_trang": r[2], "gia_tri": r[3], "ti_le": r[4]} for r in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/add-asset', methods=['POST'])
def add_asset():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO TAI_SAN (MA_TS, TEN_TS, TINH_TRANG, GIA_TRI, TI_LE_MOI, MA_PHONG) VALUES (SEQ_TS.NEXTVAL, :1, :2, :3, :4, :5)",
                    [data['ten'], data['tinh_trang'], data['gia_tri'], data['ti_le'], data['ma_phong']])
        conn.commit()
        return jsonify({"success": True, "message": "Đã ghi nhận tài sản!"})
    finally:
        conn.close()

@app.route('/api/delete-asset/<int:ma_ts>', methods=['DELETE'])
def delete_asset(ma_ts):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM TAI_SAN WHERE MA_TS = :1", [ma_ts])
        conn.commit()
        return jsonify({"success": True, "message": "Đã xóa đồ đạc!"})
    finally:
        conn.close()

@app.route('/api/update-meters', methods=['POST'])
def update_meters():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE PHONG SET DIEN_HT = :1, NUOC_HT = :2 WHERE MA_PHONG = :3", 
                    [data['dien'], data['nuoc'], data['ma_phong']])
        conn.commit()
        return jsonify({"success": True, "message": "Đã cập nhật chỉ số đồng hồ!"})
    finally:
        conn.close()

# --- API HÓA ĐƠN ĐA DỊCH VỤ ---
@app.route('/api/create-bill', methods=['POST'])
def create_bill():
    data = request.json # {ma_phong, thang_nam}
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # 1. Lấy hợp đồng & giá phòng
        cur.execute("SELECT MA_HD, GIA_PHONG FROM HOP_DONG WHERE MA_PHONG = :1 AND TRANG_THAI = 'CON_HIEU_LUC'", [data['ma_phong']])
        hd = cur.fetchone()
        if not hd: return jsonify({"success": False, "message": "Phòng trống, không thể tạo hóa đơn!"})
        ma_hd, gia_p = hd[0], hd[1]

        # 2. Lấy chỉ số điện nước hiện tại từ PHONG
        cur.execute("SELECT DIEN_HT, NUOC_HT FROM PHONG WHERE MA_PHONG = :1", [data['ma_phong']])
        p = cur.fetchone()
        
        # 3. Lấy chỉ số cũ từ hóa đơn trước
        cur.execute("SELECT D_MOI, N_MOI FROM HOA_DON WHERE MA_HD = :1 ORDER BY MA_HD_BILL DESC FETCH FIRST 1 ROWS ONLY", [ma_hd])
        old = cur.fetchone()
        d_cu, n_cu = (old[0], old[1]) if old else (0, 0)

        # 4. Lấy đơn giá dịch vụ (Điện: ID 1, Nước: ID 2, Rác: ID 3, Wifi: ID 4)
        cur.execute("SELECT MA_DV, DON_GIA FROM DICH_VU")
        prices = {r[0]: r[1] for r in cur.fetchall()}

        # 5. Tính toán chi phí
        t_dien = (p[0] - d_cu) * prices.get(1, 4000)
        t_nuoc = (p[1] - n_cu) * prices.get(2, 25000)
        t_khac = prices.get(3, 0) + prices.get(4, 0) # Rác + Wifi
        tong = gia_p + t_dien + t_nuoc + t_khac

        # 6. Insert vào bảng HOA_DON
        bill_id = cur.var(int)
        cur.execute("""
            INSERT INTO HOA_DON (MA_HD_BILL, MA_HD, THANG_NAM, TONG_TIEN, TRANG_THAI, D_CU, D_MOI, N_CU, N_MOI)
            VALUES (SEQ_HOADON.NEXTVAL, :1, :2, :3, 'CHUA_TRA', :4, :5, :6, :7)
            RETURNING MA_HD_BILL INTO :8
        """, [ma_hd, data['thang_nam'], tong, d_cu, p[0], n_cu, p[1], bill_id])
        
        # 7. Insert chi tiết dịch vụ (CT) - Tùy chọn để ghi log đầy đủ
        real_bill_id = bill_id.getvalue()[0]
        conn.commit()
        return jsonify({"success": True, "message": f"Hóa đơn {data['thang_nam']} đã xuất: {tong:,}đ"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        conn.close()

@app.route('/api/bills', methods=['GET'])
def get_bills():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT B.*, P.TEN_PHONG, K.HO_TEN
            FROM HOA_DON B 
            JOIN HOP_DONG H ON B.MA_HD = H.MA_HD
            JOIN PHONG P ON H.MA_PHONG = P.MA_PHONG
            JOIN NGUOI_THUE K ON H.MA_KH = K.MA_KH
            ORDER BY B.MA_HD_BILL DESC
        """)
        columns = [col[0].lower() for col in cur.description]
        return jsonify([dict(zip(columns, row)) for row in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/payment', methods=['POST'])
def payment():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # CHỐT: Cập nhật trạng thái DA_TRA cho đúng BILL_ID
        cur.execute("UPDATE HOA_DON SET TRANG_THAI = 'DA_TRA' WHERE MA_HD_BILL = :1", [int(data['ma_hd'])])
        conn.commit()
        return jsonify({"success": True, "message": "Thanh toán thành công! Trình duyệt sẽ tự động cập nhật."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        conn.close()

# --- CÁC API KHÁCH & HỢP ĐỒNG ---
@app.route('/api/tenants')
def get_tenants():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MA_KH, HO_TEN, SDT, CCCD FROM NGUOI_THUE ORDER BY MA_KH")
        return jsonify([{"ma_kh":r[0], "ho_ten":r[1], "sdt":r[2], "cccd":r[3]} for r in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/contracts')
def get_contracts():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MA_HD, MA_PHONG, HO_TEN, TEN_PHONG, NGAY_KY, TIEN_COC, GIA_PHONG, TRANG_THAI FROM V_HOPDONG")
        columns = [col[0].lower() for col in cur.description]
        return jsonify([dict(zip(columns, row)) for row in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/contract-detail/<int:ma_phong>')
def get_contract_detail(ma_phong):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MA_HD, HO_TEN, TIEN_COC, GIA_PHONG FROM V_HOPDONG WHERE MA_PHONG = :1 AND TRANG_THAI = 'CON_HIEU_LUC'", [ma_phong])
        r = cur.fetchone()
        if r: return jsonify({"ma_hd":r[0], "ho_ten":r[1], "tien_coc":r[2], "gia_phong":r[3]})
        return jsonify(None)
    finally:
        conn.close()

@app.route('/api/occupants/<int:ma_phong>')
def get_occupants(ma_phong):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # 1. Lấy MA_KH của chủ hợp đồng trước
        cur.execute("SELECT MA_KH FROM HOP_DONG WHERE MA_PHONG = :1 AND TRANG_THAI = 'CON_HIEU_LUC'", [ma_phong])
        owner_row = cur.fetchone()
        owner_id = owner_row[0] if owner_row else -1

        # 2. Lấy danh sách thành viên + Chủ hợp đồng (để hiện thị đầy đủ)
        # Chúng ta dùng UNION để lấy cả chủ và các thành viên phụ
        sql = """
            SELECT -1 as MA_TV, K.HO_TEN, K.CCCD, K.MA_KH, 1 as IS_OWNER
            FROM NGUOI_THUE K WHERE K.MA_KH = :owner_id
            UNION ALL
            SELECT T.MA_TV, K.HO_TEN, K.CCCD, K.MA_KH, 0 as IS_OWNER
            FROM THANH_VIEN T JOIN NGUOI_THUE K ON T.MA_KH = K.MA_KH 
            WHERE T.MA_PHONG = :ma_p
        """
        cur.execute(sql, {"owner_id": owner_id, "ma_p": ma_phong})
        return jsonify([{"ma_tv":r[0], "ho_ten":r[1], "cccd":r[2], "ma_kh":r[3], "is_owner": r[4]} for r in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/add-occupant', methods=['POST'])
def add_occ():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO THANH_VIEN (MA_TV, MA_PHONG, MA_KH) VALUES (SEQ_TV.NEXTVAL, :1, :2)", [data['ma_phong'], data['ma_kh']])
        conn.commit()
        return jsonify({"success": True, "message": "Gắn người ở thành công!"})
    finally:
        conn.close()

@app.route('/api/delete-occupant/<int:ma_tv>', methods=['DELETE'])
def del_occ(ma_tv):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM THANH_VIEN WHERE MA_TV = :1", [ma_tv])
        conn.commit()
        return jsonify({"success": True, "message": "Đã xóa!"})
    finally:
        conn.close()

@app.route('/api/revenue-summary')
def rev():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Tính tổng thu
        cur.execute("SELECT SUM(TONG_TIEN) FROM HOA_DON WHERE TRANG_THAI = 'DA_TRA'")
        thu = cur.fetchone()[0] or 0
        
        # Tính tổng chi
        cur.execute("SELECT SUM(SO_TIEN) FROM CHI_PHI")
        chi = cur.fetchone()[0] or 0
        
        return jsonify({
            "total_revenue": thu,
            "total_expense": chi,
            "net_profit": thu - chi
        })
    finally:
        conn.close()

@app.route('/api/top-contracts')
def top():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT P.TEN_PHONG, K.HO_TEN, B.TONG_TIEN 
            FROM HOA_DON B JOIN HOP_DONG H ON B.MA_HD = H.MA_HD JOIN PHONG P ON H.MA_PHONG = P.MA_PHONG JOIN NGUOI_THUE K ON H.MA_KH = K.MA_KH 
            WHERE B.TRANG_THAI = 'DA_TRA' ORDER BY B.TONG_TIEN DESC FETCH FIRST 5 ROWS ONLY
        """)
        return jsonify([{"ma_hd":r[0], "ho_ten":r[1], "tong_tien":r[2]} for r in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/create-contract', methods=['POST'])
def create_c():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Dùng tham số có tên (named binds) để tránh lỗi DPY-4009
        cur.execute("""
            INSERT INTO HOP_DONG (MA_HD, MA_PHONG, MA_KH, NGAY_KY, NGAY_HET_HAN, TIEN_COC, GIA_PHONG, TRANG_THAI)
            SELECT SEQ_HD.NEXTVAL, :ma, :kh, SYSDATE, SYSDATE+365, L.GIA_DAT_COC, L.GIA, 'CON_HIEU_LUC'
            FROM PHONG P JOIN LOAI_PHONG L ON P.MA_LOAI = L.MA_LOAI 
            WHERE P.MA_PHONG = :ma
        """, {"ma": int(data['ma_phong']), "kh": int(data['ma_kh'])})
        
        cur.execute("UPDATE PHONG SET TRANG_THAI = 'DA_THUE' WHERE MA_PHONG = :ma", {"ma": int(data['ma_phong'])})
        conn.commit()
        return jsonify({"success": True, "message": "Hợp đồng đã được ký thành công!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    finally:
        conn.close()

# --- API CHI PHÍ ---
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT MA_CHI_PHI, LOAI_CHI_PHI, SO_TIEN, TO_CHAR(NGAY_CHI, 'DD/MM/YYYY'), GHI_CHU FROM CHI_PHI ORDER BY NGAY_CHI DESC")
        return jsonify([{"ma":r[0], "loai":r[1], "tien":r[2], "ngay":r[3], "ghi_chu":r[4]} for r in cur.fetchall()])
    finally:
        conn.close()

@app.route('/api/add-expense', methods=['POST'])
def add_expense():
    data = request.json
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO CHI_PHI (MA_CHI_PHI, LOAI_CHI_PHI, SO_TIEN, GHI_CHU) VALUES (SEQ_CHIPHI.NEXTVAL, :1, :2, :3)",
                    [data['loai'], data['tien'], data['ghi_chu']])
        conn.commit()
        return jsonify({"success": True, "message": "Đã ghi nhận chi phí!"})
    finally:
        conn.close()

@app.route('/api/delete-expense/<int:ma_cp>', methods=['DELETE'])
def delete_expense(ma_cp):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM CHI_PHI WHERE MA_CHI_PHI = :1", [ma_cp])
        conn.commit()
        return jsonify({"success": True, "message": "Đã xóa chi phí!"})
    finally:
        conn.close()

@app.route('/api/end-contract/<int:ma_hd>', methods=['POST'])
def end_c(ma_hd):
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE PHONG SET TRANG_THAI = 'TRONG' WHERE MA_PHONG = (SELECT MA_PHONG FROM HOP_DONG WHERE MA_HD = :1)", [ma_hd])
        cur.execute("UPDATE HOP_DONG SET TRANG_THAI = 'HET_HAN' WHERE MA_HD = :1", [ma_hd])
        conn.commit()
        return jsonify({"success": True, "message": "Đã giải phóng phòng!"})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
