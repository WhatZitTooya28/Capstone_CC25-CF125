# File: backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename # Untuk mengamankan nama file
import os
import random
import datetime
import jwt
from functools import wraps
import logging

app = Flask(__name__)
CORS(app)

# --- Konfigurasi Aplikasi ---
app.config['SECRET_KEY'] = 'ganti-dengan-kunci-rahasia-super-aman-anda-56789'  # GANTI INI!
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_EXP_DELTA_SECONDS'] = 3600 * 24  # Token berlaku 1 hari

# Konfigurasi Database SQLite
# Menentukan path absolut untuk database di dalam folder 'instance'
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "trashgu.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Konfigurasi Folder Upload
# Menentukan path absolut untuk folder uploads di dalam folder 'instance'
UPLOAD_FOLDER = os.path.join(instance_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Batas ukuran file 16MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Model Database ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ClassificationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=True)
    image_url = db.Column(db.String(255), nullable=True) # Path relatif dari UPLOAD_FOLDER
    classification_result = db.Column(db.String(50), nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # Tambahkan field untuk saran penanganan jika ingin disimpan langsung di DB
    # saran_penanganan_text = db.Column(db.Text, nullable=True) 
    
    user = db.relationship('User', backref=db.backref('histories', lazy=True, cascade="all, delete-orphan"))

# --- Buat tabel database jika belum ada ---
with app.app_context():
    db.create_all()

# --- Fungsi Helper untuk Token JWT ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Token tidak ditemukan!', 'error_code': 'TOKEN_MISSING'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
            current_user = User.query.filter_by(username=data['sub']).first()
            if not current_user:
                return jsonify({'message': 'Pengguna dengan token ini tidak ditemukan.', 'error_code': 'USER_NOT_FOUND'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token sudah kedaluwarsa!', 'error_code': 'TOKEN_EXPIRED'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid!', 'error_code': 'TOKEN_INVALID'}), 401
        except Exception as e:
            print(f"Error saat decode token: {e}") 
            return jsonify({'message': 'Masalah saat validasi token.', 'error_code': 'TOKEN_VALIDATION_ERROR'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# --- Endpoint Aplikasi ---
dummy_results_info = {
    "ORGANIK": {"saran_penanganan": ["Jadikan kompos untuk pupuk tanaman.", "Bisa diberikan sebagai pakan ternak (jika sesuai).", "Buang ke tempat sampah khusus organik."]},
    "ANORGANIK": {"saran_penanganan": ["Pisahkan berdasarkan jenis material (plastik, kertas, logam, kaca).", "Bersihkan dari sisa kotoran atau cairan.", "Serahkan ke bank sampah atau fasilitas daur ulang terdekat."]},
    "TIDAK DIKETAHUI": {"saran_penanganan": ["Jenis sampah tidak dapat dikenali dengan pasti. Coba ambil gambar dengan lebih jelas atau dari sudut yang berbeda."]}
}

@app.route('/api/klasifikasi', methods=['POST'])
@token_required
def klasifikasi_sampah(current_user):
    if 'image' not in request.files:
        return jsonify({"error": "Tidak ada file gambar yang dikirim", "error_code": "NO_IMAGE_FILE"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"error": "Tidak ada file yang dipilih", "error_code": "NO_FILE_SELECTED"}), 400
    
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        unique_filename = f"{timestamp_str}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(file_path)
            image_access_url = f"/uploads/{unique_filename}" 
        except Exception as e:
            app.logger.error(f"Gagal menyimpan file: {e}")
            return jsonify({"error": "Gagal menyimpan file gambar", "error_code": "FILE_SAVE_ERROR"}), 500

        kategori_prediksi = random.choice(["ORGANIK", "ANORGANIK"])
        akurasi_prediksi = round(random.uniform(0.75, 0.99), 2)
        saran = dummy_results_info.get(kategori_prediksi, dummy_results_info["TIDAK DIKETAHUI"])["saran_penanganan"]
        
        try:
            new_history = ClassificationHistory(
                user_id=current_user.id,
                filename=original_filename, 
                image_url=image_access_url, 
                classification_result=kategori_prediksi,
                accuracy=akurasi_prediksi
                # Jika ingin menyimpan saran langsung:
                # saran_penanganan_text = ", ".join(saran) 
            )
            db.session.add(new_history)
            db.session.commit()
            app.logger.info(f"Riwayat klasifikasi disimpan untuk user {current_user.username}, file: {original_filename}")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Gagal menyimpan riwayat: {e}")
        
        hasil = {
            "kategori": kategori_prediksi,
            "akurasi": akurasi_prediksi,
            "saran_penanganan": saran,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "nama_file_asli": original_filename,
            "image_url_preview": image_access_url, 
            "error": None
        }
        return jsonify(hasil), 200
    
    elif file and not allowed_file(file.filename):
        return jsonify({"error": "Jenis file tidak diizinkan. Hanya PNG, JPG, JPEG, GIF.", "error_code": "INVALID_FILE_TYPE"}), 400
        
    return jsonify({"error": "Terjadi kesalahan yang tidak diketahui", "error_code": "UNKNOWN_CLASSIFICATION_ERROR"}), 500

@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body tidak valid (bukan JSON)", "error_code": "INVALID_JSON"}), 400
    
    nama_pengguna = data.get('namaPengguna')
    email = data.get('email')
    password = data.get('password')
    
    if not all([nama_pengguna, email, password]):
        return jsonify({"error": "Data tidak lengkap (namaPengguna, email, password diperlukan)", "error_code": "MISSING_FIELDS"}), 400
    
    if User.query.filter_by(username=nama_pengguna).first():
        return jsonify({"error": "Nama pengguna sudah terdaftar", "error_code": "USERNAME_EXISTS"}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email sudah terdaftar", "error_code": "EMAIL_EXISTS"}), 409
    
    new_user = User(username=nama_pengguna, email=email)
    new_user.set_password(password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        app.logger.info(f"Pengguna terdaftar: {nama_pengguna}")
        return jsonify({"message": f"Pengguna {nama_pengguna} berhasil terdaftar!"}), 201
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error registrasi: {e}")
        return jsonify({"error": "Gagal mendaftarkan pengguna, coba lagi.", "error_code": "REGISTRATION_FAILED"}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body tidak valid (bukan JSON)", "error_code": "INVALID_JSON"}), 400
        
    identifier = data.get('identifier') 
    password = data.get('password')
    
    if not all([identifier, password]):
        return jsonify({"error": "Data tidak lengkap (identifier, password diperlukan)", "error_code": "MISSING_FIELDS"}), 400
    
    user_candidate = User.query.filter_by(username=identifier).first()
    if not user_candidate:
        user_candidate = User.query.filter_by(email=identifier).first()
    
    if user_candidate and user_candidate.check_password(password):
        payload = {
            'sub': user_candidate.username, 
            'email': user_candidate.email,
            'user_id': user_candidate.id, 
            'iat': datetime.datetime.utcnow(), 
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXP_DELTA_SECONDS'])
        }
        try:
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
            app.logger.info(f"Pengguna berhasil login: {user_candidate.username}")
            return jsonify({
                "message": "Login berhasil!",
                "token": token,
                "user": {"namaPengguna": user_candidate.username, "email": user_candidate.email, "id": user_candidate.id}
            }), 200
        except Exception as e:
            app.logger.error(f"Error saat generate token: {e}")
            return jsonify({"error": "Gagal membuat token autentikasi", "error_code": "TOKEN_GENERATION_FAILED"}), 500
    else:
        app.logger.warning(f"Gagal login untuk identifier: {identifier}")
        return jsonify({"error": "Nama pengguna/email atau kata sandi salah", "error_code": "INVALID_CREDENTIALS"}), 401

# --- Endpoint untuk Riwayat Klasifikasi ---
@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user):
    try:
        histories = ClassificationHistory.query.filter_by(user_id=current_user.id).order_by(ClassificationHistory.timestamp.desc()).all()
        output = []
        for history_item in histories:
            # Dapatkan saran penanganan berdasarkan hasil klasifikasi
            saran = dummy_results_info.get(history_item.classification_result, dummy_results_info["TIDAK DIKETAHUI"])["saran_penanganan"]
            output.append({
                'id': history_item.id,
                'filename': history_item.filename,
                'image_url': history_item.image_url, 
                'classification_result': history_item.classification_result,
                'accuracy': history_item.accuracy,
                'timestamp': history_item.timestamp.isoformat(),
                'saran_penanganan': saran # Tambahkan saran penanganan
            })
        return jsonify({'histories': output}), 200
    except Exception as e:
        app.logger.error(f"Error mengambil riwayat untuk user {current_user.username}: {e}")
        return jsonify({"error": "Gagal mengambil data riwayat.", "error_code": "HISTORY_FETCH_FAILED"}), 500

@app.route('/api/history/<int:history_id>', methods=['DELETE'])
@token_required
def delete_history_item(current_user, history_id):
    try:
        history_item = ClassificationHistory.query.filter_by(id=history_id, user_id=current_user.id).first()
        
        if not history_item:
            return jsonify({"error": "Item riwayat tidak ditemukan atau Anda tidak berhak menghapusnya.", "error_code": "HISTORY_ITEM_NOT_FOUND_OR_FORBIDDEN"}), 404
        
        if history_item.image_url:
            try:
                filename_only = history_item.image_url.split('/')[-1]
                file_to_delete_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_only)
                if os.path.exists(file_to_delete_path):
                    os.remove(file_to_delete_path)
                    app.logger.info(f"File gambar {file_to_delete_path} berhasil dihapus untuk history item ID: {history_id}")
                else:
                    app.logger.warning(f"File gambar {file_to_delete_path} tidak ditemukan saat mencoba menghapus history item ID: {history_id}")
            except Exception as e_file_delete:
                app.logger.error(f"Gagal menghapus file gambar {history_item.image_url} untuk history item ID: {history_id}. Error: {e_file_delete}")

        db.session.delete(history_item)
        db.session.commit()
        app.logger.info(f"Item riwayat ID: {history_id} berhasil dihapus oleh pengguna {current_user.username}")
        return jsonify({"message": "Item riwayat berhasil dihapus."}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error menghapus item riwayat ID {history_id} untuk user {current_user.username}: {e}")
        return jsonify({"error": "Gagal menghapus item riwayat.", "error_code": "HISTORY_DELETE_FAILED"}), 500

from flask import send_from_directory
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    safe_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
    requested_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if not requested_path.startswith(safe_path):
        return jsonify({"error": "File tidak ditemukan"}), 404
        
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    app.run(debug=True, port=5000)

