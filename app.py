from flask import Flask, request, jsonify, session
from flask_cors import CORS
import mysql.connector
import qrcode
from datetime import date
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:5500"}}, supports_credentials=True)
app.secret_key = 'rahasia_banget'  # Ganti dengan kunci rahasia yang lebih kuat

app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True  # Wajib kalau pakai HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_PATH'] = '/'  # Set path cookie agar bisa diakses di semua route
# app.config['SESSION_COOKIE_DOMAIN'] = 'localhost'  # Ganti dengan domain Anda jika perlu
# app.config['SESSION_COOKIE_NAME'] = 'session_id'  # Nama cookie session
# app.config['SESSION_PERMANENT'] = False  # Session tidak permanen
# app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Waktu hidup session dalam detik (1 jam)
# app.config['SESSION_USE_SIGNER'] = True  # Gunakan signer untuk keamanan tambahan

# Konfigurasi database MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Ganti dengan username database Anda
    'password': '',  # Ganti dengan password database Anda
    'database': 'absensiqr'  # Ganti dengan nama database Anda
}

def get_db_connection():
    """Membuat koneksi ke database MySQL."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        return cnx
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def close_db_connection(cnx):
    """Menutup koneksi database MySQL."""
    if cnx:
        cnx.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query untuk memeriksa pengguna
        query = "SELECT * FROM admins WHERE username = %s"
        cursor.execute(query, (username,))
        admin = cursor.fetchone()

        cursor.close()
        conn.close()

        if admin and admin['password'] == password:  # Jangan gunakan plaintext password di produksi!
            session['logged_in'] = True
            session['user_id'] = admin['id']
            session['kelas'] = admin['kelas']  # Simpan kelas ke session
            print("Session setelah login:", session)  # Debugging: Periksa session
            return jsonify({'message': 'Login berhasil'}), 200
        else:
            return jsonify({'message': 'Username atau password salah'}), 401
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': 'Gagal memproses login'}), 500
    
@app.route('/dashboard')
def dashboard():
    if session.get('logged_in'):
        return jsonify({'message': f"Selamat datang di dashboard admin dengan ID: {session.get('admin_id')}"}), 200
    else:
        return jsonify({'message': 'Akses ditolak, silakan login terlebih dahulu'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Hapus semua data session
    return jsonify({'message': 'Logout berhasil'}), 200

@app.route('/api/tambah-siswa', methods=['POST'])
def tambah_siswa():
    data = request.get_json()
    nama = data.get('nama')
    nisn = data.get('nisn')
    kelas = data.get('kelas')

    if not nama or not nisn or not kelas:
        return jsonify({'message': 'Semua data harus diisi!'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Simpan data siswa ke database
        query = "INSERT INTO siswa (nama, nisn, kelas) VALUES (%s, %s, %s)"
        cursor.execute(query, (nama, nisn, kelas))
        conn.commit()

        # Generate QR Code
        qr_data = f"{nama},{nisn},{kelas}"
        qr = qrcode.make(qr_data)

        # Simpan QR Code sebagai file PNG
        qr_folder = os.path.join(os.getcwd(), 'static', 'qr_codes')
        os.makedirs(qr_folder, exist_ok=True)
        qr_file_path = os.path.join(qr_folder, f"{nisn}.png")
        qr.save(qr_file_path)

        # Simpan URL QR Code ke database
        qr_code_url = f"/static/qr_codes/{nisn}.png"
        update_query = "UPDATE siswa SET qr_code_url = %s WHERE nisn = %s"
        cursor.execute(update_query, (qr_code_url, nisn))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'message': 'Data siswa berhasil disimpan!', 'qr_code': qr_code_url}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': 'Gagal menyimpan data siswa!'}), 500

@app.route('/api/siswa', methods=['GET'])
def get_siswa():
    print("Session saat ini:", session)  # Debugging: Periksa session
    if not session.get('logged_in'):
        return jsonify({'message': 'Anda belum login'}), 401

    kelas = session.get('kelas')  # Ambil kelas dari session
    if not kelas:
        return jsonify({'message': 'Kelas tidak ditemukan dalam session'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query untuk mengambil data siswa berdasarkan kelas
        query = "SELECT nama, nisn FROM siswa WHERE kelas = %s"
        cursor.execute(query, (kelas,))
        siswa = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify(siswa), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': 'Gagal mengambil data siswa!'}), 500
    
    
@app.route('/api/siswa/qrcode', methods=['GET'])
def get_siswa_to_qr():
    print("Session saat ini:", session)  # Debugging: Periksa session
    if not session.get('logged_in'):
        return jsonify({'message': 'Anda belum login'}), 401

    kelas = session.get('kelas')  # Ambil kelas dari session
    if not kelas:
        return jsonify({'message': 'Kelas tidak ditemukan dalam session'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query untuk mengambil data siswa berdasarkan kelas
        query = "SELECT nama, nisn, qr_code_url FROM siswa WHERE kelas = %s"
        cursor.execute(query, (kelas,))
        siswa = cursor.fetchall()

        cursor.close() 
        conn.close()

        return jsonify(siswa), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': 'Gagal mengambil data siswa!'}), 500

@app.route('/api/user', methods=['GET'])
def get_user():
    if not session.get('logged_in'):
        return jsonify({'message': 'Anda belum login'}), 401

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'message': 'User ID tidak ditemukan'}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Ambil data pengguna berdasarkan user_id
        query = "SELECT username, kelas FROM admins WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            return jsonify(user), 200
        else:
            return jsonify({'message': 'Pengguna tidak ditemukan'}), 404
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': 'Terjadi kesalahan server'}), 500

@app.route('/api/tambah-admin', methods=['POST'])
def tambah_admin():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    kelas = data.get('kelas')

    if not username or not password or not kelas:
        return jsonify({'message': 'Semua data harus diisi!'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Simpan data admin ke tabel admins
        query = "INSERT INTO admins (username, password, kelas) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, password, kelas))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'message': 'Admin berhasil ditambahkan!'}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({'message': 'Gagal menambahkan admin!'}), 500

@app.route('/api/submit-absensi', methods=['POST'])
def scan_absen():
    try:
        data = request.get_json()

        if not isinstance(data, list):
            return jsonify({'message': 'Data harus berupa list!'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        for siswa in data:
            nama = siswa.get('nama')
            nisn = siswa.get('nisn')
            kelas = siswa.get('kelas')
            status = siswa.get('status')
            waktu = siswa.get('waktu')  # misalnya '08:00:00'

            if not nama or not status:
                return jsonify({'message': 'Nama dan status harus diisi!'}), 400

            query = """
            INSERT INTO absensi_harian (nama, nisn, kelas, status, tanggal, waktu)
            VALUES (%s, %s, %s, %s, CURDATE(), %s)
            """
            cursor.execute(query, (nama, nisn, kelas, status, waktu))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Absen berhasil disimpan!'}), 200

    except Exception as e:
        print('DB Error:', e)
        return jsonify({'message': f'Gagal menyimpan absen: {str(e)}'}), 500



    
@app.route('/api/siswa-kelas', methods=['GET'])
def get_siswa_by_kelas():
    try:
        kelas = session.get('logged_in')  # atau bisa dari token/login
        kelas1 = session.get('kelas')  # BENAR
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT nama FROM siswa WHERE kelas = %s", (kelas,))
        siswa_list = cursor.fetchall()

        cursor.close()
        conn.close()
        return jsonify(siswa_list), 200
    except Exception as e:
        print("DB Error:", e)
        return jsonify({'message': 'Gagal mengambil data siswa'}), 500


from datetime import timedelta

@app.route('/api/absensi-sudah-scan', methods=['GET'])
def get_siswa_sudah_scan():
    try:
        kelas = session.get('kelas')
        print("Session data sekarang:", dict(session))  # Debug session

        if not kelas:
            return jsonify({'message': 'Kelas tidak ditemukan di session!'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT nama, status, waktu
            FROM absensi_harian
            WHERE DATE(tanggal) = CURDATE() AND kelas = %s
        """
        cursor.execute(query, (kelas,))
        hasil = cursor.fetchall()

        # Konversi 'waktu' ke string jika bertipe timedelta
        for row in hasil:
            if isinstance(row.get('waktu'), timedelta):
                row['waktu'] = str(row['waktu'])

        cursor.close()
        conn.close()

        return jsonify(hasil), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'message': f'Gagal: {str(e)}'}), 500



@app.route('/api/absensi-belum-scan', methods=['GET'])
def get_siswa_belum_scan():
    try:
        kelas = session.get('kelas')
        if not kelas:
            return jsonify({'message': 'Kelas tidak ditemukan di session!'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Ambil semua siswa di kelas
        cursor.execute("SELECT nama FROM siswa WHERE kelas = %s", (kelas,))
        semua_siswa = cursor.fetchall()

        # Ambil nama-nama siswa yang sudah absen hari ini
        cursor.execute("""
            SELECT ah.nama FROM absensi_harian ah
            JOIN siswa s ON ah.nama = s.nama
            WHERE DATE(ah.tanggal) = CURDATE() AND s.kelas = %s
        """, (kelas,))
        siswa_sudah_scan = cursor.fetchall()

        # Normalize nama (hapus spasi & lowercase)
        nama_sudah_scan = {s['nama'].strip().lower() for s in siswa_sudah_scan}

        # Filter siswa yang belum scan
        siswa_belum_scan = [
            siswa for siswa in semua_siswa
            if siswa['nama'].strip().lower() not in nama_sudah_scan
        ]

        cursor.close()
        conn.close()

        return jsonify(siswa_belum_scan), 200
    except Exception as e:
        print("DB Error:", e)
        return jsonify({'message': f'Gagal mengambil data siswa belum scan: {str(e)}'}), 500

 
@app.route('/api/submit-absensi-ortu', methods=['POST'])
def submit_absensi_ortu():
    try:
        kelas = session.get('kelas')
        if not kelas:
            return jsonify({'message': 'Kelas tidak ditemukan di session!'}), 400

        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({'message': 'Data harus berupa list!'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        for siswa in data:
            nama = siswa.get('nama')
            status = siswa.get('status')
            tanggal = siswa.get('tanggal', date.today())

            if not nama or not status:
                return jsonify({'message': 'Nama dan status harus diisi!'}), 400

            query = """
                INSERT INTO absensi_harian_ortu (nama, status, tanggal)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (nama, status, tanggal))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Data absensi berhasil disimpan ke absensi_harian_ortu!'}), 200
    except Exception as e:
        print("DB Error:", e)
        return jsonify({'message': f'Gagal menyimpan data absensi: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
