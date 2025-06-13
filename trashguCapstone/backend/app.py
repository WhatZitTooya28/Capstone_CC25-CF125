# File: backend/app.py (Ini adalah file yang akan diunggah ke PythonAnywhere)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import datetime
import jwt
from functools import wraps
import logging
import random
from collections import Counter
# import requests  # Hapus atau komentari ini
# import numpy as np # Pertahankan ini untuk random choice

app = Flask(__name__)
CORS(app)

# --- Konfigurasi Aplikasi ---
app.config['SECRET_KEY'] = 'ganti-dengan-kunci-rahasia-super-aman-anda-56789'  # Ganti ini dengan kunci rahasia yang kuat!
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_EXP_DELTA_SECONDS'] = 3600 * 24  # Token berlaku 24 jam

# --- Konfigurasi Database dan Folder Upload ---
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
if not os.path.exists(instance_path):
    os.makedirs(instance_path)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "trashgu.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

UPLOAD_FOLDER = os.path.join(instance_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Batas ukuran file 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Konfigurasi Label dan Saran Penanganan Sampah ---
CLASS_LABELS = ['battery', 'biological', 'cardboard', 'clothes', 'glass', 'metal', 'paper', 'plastic', 'shoes', 'trash']
REMAP_DICT = {
    'battery': 'RESIDU', 'biological': 'ORGANIK', 'cardboard': 'ANORGANIK',
    'clothes': 'RESIDU', 'glass': 'ANORGANIK', 'metal': 'ANORGANIK',
    'paper': 'ANORGANIK', 'plastic': 'ANORGANIK', 'shoes': 'RESIDU', 'trash': 'RESIDU'
}
HANDLING_SUGGESTIONS = {
    'battery': 'Baterai bekas mengandung bahan logam berat seperti merkuri, timbal, kadmium, dan litium. Harap kumpulkan, pisahkan, dan bawa ke dropbox limbah B3 atau e-waste center agar tidak mencemari lingkungan.',
    'biological': 'Sisa makanan dan bahan organik dapat dikomposkan untuk menjadi pupuk alami. Ini membantu dalam mengurangi intensitas sampah serta menghasilkan pupuk alami yang bermanfaat untuk tanaman.',
    'cardboard': 'Kardus yang sudah tidak digunakan dapat dilipat dan dijual ke pengepul atau diserahkan ke tempat daur ulang. Pastikan kardus kering dan bersih.',
    'clothes': 'Pakaian lama yang masih layak digunakan dapat disumbangkan atau digunakan kembali. Apabila sudah rusak, sebaiknya dibuang ke dalam tempat sampah jenis residu.',
    'glass': 'Harap pisahkan dan kumpulkan botol dan kaca dengan hati-hati. Pastikan tidak pecah dan serahkan pada tempat daur ulang kaca supaya dapat diproses kembali.',
    'metal': 'Kaleng dan jenis logam lainnya dapat dibersihkan dan dijual ke pengepul logam. Ini dapat membantu mengurangi limbah.',
    'paper': 'Kertas bersih dapat dikumpulkan dan dijual ke bank sampah atau tempat daur ulang. Pastikan kertas tidak tercampur dengan jenis sampah lain.',
    'plastic': 'Plastik harus dibersihkan dulu sebelum didaur ulang. Pisahkan plastik dengan jenis sampah residu supaya proses daur ulang dapat berjalan dengan baik.',
    'shoes': 'Sepatu lama yang masih layak dapat disumbangkan, sedangkan jika sudah rusak buang pada tempat sampah residu.',
    'trash': 'Jenis sampah ini umumnya tidak dapat didaur ulang. Buang sesuai dengan prosedur kebersihan dan jangan campur dengan sampah yang bisa didaur ulang.',
    'TIDAK DIKETAHUI': "Jenis sampah tidak dapat dikenali. Coba ambil gambar dengan lebih jelas atau dari sudut yang berbeda."
}

# --- Database Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ClassificationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    classification_result = db.Column(db.String(50), nullable=False) # Kategori utama: ORGANIK/ANORGANIK/RESIDU
    accuracy = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref=db.backref('histories', lazy=True, cascade="all, delete-orphan"))
    specific_name = db.Column(db.String(100), nullable=True) # Nama spesifik: battery/plastic/paper dll.
    suggestion = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()

# --- Authentication Decorator ---
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
            app.logger.error(f"Error decoding token: {e}")
            return jsonify({'message': 'Masalah saat validasi token.', 'error_code': 'TOKEN_VALIDATION_ERROR'}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# --- Fungsi Prediksi ML (Sekarang Dummy Classifier) ---
# HUGGING_FACE_API_URL = "https://api-inference.huggingface.co/models/PebriA/trashgu-classification-model" # Hapus/komentari
# HUGGING_FACE_API_KEY = "hf_YOUR_API_TOKEN_HERE" # Hapus/komentari

def predict_image(image_path):
    # Tidak perlu membaca gambar atau memanggil API eksternal lagi
    # Langsung kembalikan hasil dummy
    
    # Pilih label spesifik secara acak dari CLASS_LABELS
    predicted_label_specific = random.choice(CLASS_LABELS) 
    
    # Tentukan confidence acak
    raw_confidence = random.uniform(0.50, 0.98) 
    
    is_anomaly = False # Selalu False untuk dummy
    
    # Remap ke kategori utama (ORGANIK, ANORGANIK, RESIDU)
    main_category = REMAP_DICT.get(predicted_label_specific, 'RESIDU')
    
    # Gunakan simulasi akurasi Anda
    simulated_accuracy = 0.50 + (raw_confidence * (0.98 - 0.50))
    
    suggestions = [HANDLING_SUGGESTIONS.get(predicted_label_specific, HANDLING_SUGGESTIONS['TIDAK DIKETAHUI'])]
    
    app.logger.info(f"DEBUG: Returning dummy prediction: {predicted_label_specific} (Category: {main_category})")
    
    return main_category, predicted_label_specific, simulated_accuracy, suggestions, None # Tidak ada error_msg

# --- API Endpoints ---
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body tidak valid (bukan JSON)"}), 400

    nama_pengguna = data.get('namaPengguna')
    email = data.get('email')
    password = data.get('password')

    if not all([nama_pengguna, email, password]):
        return jsonify({"error": "Data tidak lengkap"}), 400

    if User.query.filter_by(username=nama_pengguna).first():
        return jsonify({"error": "Nama pengguna sudah terdaftar"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email sudah terdaftar"}), 409

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
        return jsonify({"error": "Gagal mendaftarkan pengguna, coba lagi."}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body tidak valid (bukan JSON)"}), 400

    identifier = data.get('identifier')
    password = data.get('password')

    if not all([identifier, password]):
        return jsonify({"error": "Data tidak lengkap"}), 400

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
            return jsonify({"message": "Login berhasil!", "token": token, "user": {"namaPengguna": user_candidate.username, "email": user_candidate.email, "id": user_candidate.id, "avatarUrl": user_candidate.avatar_url}}), 200
        except Exception as e:
            app.logger.error(f"Error saat generate token:{e}")
            return jsonify({"error": "Gagal membuat token autentikasi"}), 500
    else:
        app.logger.warning(f"Gagal login untuk identifier: {identifier}")
        return jsonify({"error": "Nama pengguna/email atau kata sandi salah"}), 401

@app.route('/api/klasifikasi', methods=['POST'])
@token_required
def klasifikasi_sampah_authenticated(current_user):
    if 'image' not in request.files:
        return jsonify({"error": "Tidak ada file gambar yang dikirim"}), 400

    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "File tidak valid atau tidak diizinkan"}), 400
    
    # Simpan file secara sementara untuk dikirim ke dummy classifier
    original_filename = secure_filename(file.filename)
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    unique_filename = f"{timestamp_str}_{original_filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    
    try:
        file.save(file_path)
        image_access_url = f"/uploads/{unique_filename}"
    except Exception as e:
        app.logger.error(f"Failed to save file: {e}")
        return jsonify({"error": "Gagal menyimpan file gambar"}), 500

    # Panggil fungsi prediksi yang sekarang mengembalikan hasil dummy
    main_category, specific_category, accuracy, suggestions, error_msg = predict_image(file_path)
    
    # Hapus file sementara setelah prediksi (untuk menjaga kuota disk)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            app.logger.info(f"Temporary file {file_path} removed after classification.")
        except Exception as e_remove:
            app.logger.error(f"Failed to remove temp file {file_path}: {e_remove}")

    if error_msg:
        return jsonify({"error": error_msg, "error_code": "PREDICTION_FAILED"}), 500
    
    # Simpan riwayat ke database (hanya untuk authenticated users)
    try:
        new_history = ClassificationHistory(
            user_id=current_user.id,
            filename=original_filename,
            image_url=image_access_url, # URL ini akan merujuk ke file yang diupload (sudah dihapus), jadi ini mungkin perlu disesuaikan jika gambar tidak disimpan permanen
            classification_result=main_category,
            accuracy=accuracy,
            specific_name=specific_category.capitalize(),
            suggestion=suggestions[0] if suggestions else "Tidak ada saran penanganan."
        )
        db.session.add(new_history)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Failed to save history: {e}")
        return jsonify({"error": "Gagal menyimpan riwayat ke database."}), 500

    response_data = {
        "kategori": main_category,
        "kategori_spesifik": specific_category,
        "akurasi": accuracy,
        "saran_penanganan": suggestions,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "nama_file_asli": original_filename,
        "image_url_preview": image_access_url, # Ini akan bekerja jika Anda memiliki mekanisme untuk menyimpan gambar riwayat secara permanen di cloud storage
    }
    return jsonify(response_data), 200

# Endpoint baru untuk pengguna tamu
@app.route('/api/klasifikasi-guest', methods=['POST'])
def klasifikasi_sampah_guest():
    if 'image' not in request.files:
        return jsonify({"error": "Tidak ada file gambar yang dikirim"}), 400

    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "File tidak valid atau tidak diizinkan"}), 400
    
    # Membuat nama file sementara untuk tamu
    original_filename = secure_filename(file.filename)
    temp_filename = f"guest_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}_{original_filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_filename)
    
    try:
        file.save(file_path)
        # Prediksi gambar (dummy)
        main_category, specific_category, accuracy, suggestions, error_msg = predict_image(file_path)
        
        if error_msg:
            return jsonify({"error": error_msg, "error_code": "PREDICTION_FAILED"}), 500
        
        # Mengembalikan hasil tanpa menyimpan ke database
        response_data = {
            "kategori": main_category,
            "kategori_spesifik": specific_category,
            "akurasi": accuracy,
            "saran_penanganan": suggestions,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "nama_file_asli": original_filename
        }
        return jsonify(response_data), 200
    except Exception as e:
        app.logger.error(f"Error during guest classification: {e}")
        return jsonify({"error": "Terjadi kesalahan saat memproses gambar."}), 500
    finally:
        # Menghapus file sementara setelah prediksi selesai (PENTING untuk menjaga kuota disk)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                app.logger.info(f"Temporary guest file {file_path} removed.")
            except Exception as e_remove:
                app.logger.error(f"Failed to remove temp guest file {file_path}: {e_remove}")

@app.route('/api/history', methods=['GET'])
@token_required
def get_history(current_user):
    try:
        histories = ClassificationHistory.query.filter_by(user_id=current_user.id).order_by(ClassificationHistory.timestamp.desc()).all()
        output = []
        for history_item in histories:
            output.append({
                'id': history_item.id,
                'filename': history_item.filename,
                'image_url': history_item.image_url,
                'classification_result': history_item.classification_result,
                'accuracy': history_item.accuracy,
                'timestamp': history_item.timestamp.isoformat(),
                'specific_waste_name': history_item.specific_name,
                'handling_suggestion': history_item.suggestion,
            })
        return jsonify({'histories': output}), 200
    except Exception as e:
        app.logger.error(f"Error fetching history: {e}")
        return jsonify({"error": "Gagal mengambil data riwayat."}), 500

@app.route('/api/statistics', methods=['GET'])
@token_required
def get_statistics(current_user):
    try:
        user_histories = ClassificationHistory.query.filter_by(user_id=current_user.id).all()
        if not user_histories:
            return jsonify({"total_classifications": 0, "category_counts": {"ORGANIK": 0, "ANORGANIK": 0, "RESIDU": 0}}), 200
        
        total_classifications = len(user_histories)
        category_list = [h.classification_result for h in user_histories]
        category_counts = Counter(category_list)
        
        final_counts = {
            "ORGANIK": category_counts.get("ORGANIK", 0),
            "ANORGANIK": category_counts.get("ANORGANIK", 0),
            "RESIDU": category_counts.get("RESIDU", 0)
        }
        return jsonify({"total_classifications": total_classifications, "category_counts": final_counts}), 200
    except Exception as e:
        app.logger.error(f"Error calculating statistics for user {current_user.username}: {e}")
        return jsonify({"error": "Gagal menghitung statistik."}), 500

@app.route('/api/history/<int:history_id>', methods=['DELETE'])
@token_required
def delete_history_item(current_user, history_id):
    try:
        history_item = ClassificationHistory.query.filter_by(id=history_id, user_id=current_user.id).first()
        if not history_item:
            return jsonify({"error": "Item riwayat tidak ditemukan atau Anda tidak berhak menghapusnya."}), 404

        # Perhatian: Karena gambar sekarang hanya disimpan sementara,
        # 'image_url' di DB mungkin tidak lagi merujuk ke file fisik yang ada.
        # Jika Anda ingin gambar riwayat tetap bisa diakses, Anda perlu mengunggahnya
        # ke layanan cloud storage (misalnya Firebase Storage, AWS S3) secara permanen
        # dan menyimpan URL cloud-nya di DB, bukan path lokal.
        if history_item.image_url and history_item.image_url.startswith('/uploads/'):
            try:
                filename_only = history_item.image_url.split('/')[-1]
                file_to_delete_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_only)
                if os.path.exists(file_to_delete_path):
                    os.remove(file_to_delete_path)
                    app.logger.info(f"File gambar {file_to_delete_path} berhasil dihapus.")
                else:
                    app.logger.warning(f"File {file_to_delete_path} not found for deletion.")
            except Exception as e_file_delete:
                app.logger.error(f"Failed to delete image file (might already be gone): {e_file_delete}")

        db.session.delete(history_item)
        db.session.commit()
        app.logger.info(f"History item ID: {history_id} deleted by user {current_user.username}")
        return jsonify({"message": "Item riwayat berhasil dihapus."}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting history item: {e}")
        return jsonify({"error": "Gagal menghapus item riwayat."}), 500
        
@app.route('/api/user/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    data = request.get_json()
    if not data or not all(k in data for k in ['old_password', 'new_password']):
        return jsonify({"error": "Data tidak lengkap."}), 400
    
    if not current_user.check_password(data['old_password']):
        return jsonify({"error": "Kata sandi lama salah."}), 401
    
    if len(data['new_password']) < 8:
        return jsonify({"error": "Kata sandi baru minimal 8 karakter."}), 400

    try:
        current_user.set_password(data['new_password'])
        db.session.commit()
        return jsonify({"message": "Kata sandi berhasil diubah."}), 200
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error changing password for user {current_user.username}: {e}")
        return jsonify({"error": "Gagal mengubah kata sandi."}), 500

@app.route('/api/user/avatar', methods=['POST'])
@token_required
def upload_avatar(current_user):
    if 'avatar' not in request.files:
        return jsonify({"error": "Tidak ada file gambar yang dikirim."}), 400
    
    file = request.files['avatar']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error": "File tidak valid atau tidak diizinkan."}), 400
        
    try:
        # Menggunakan Pillow (tetap di sini karena hanya untuk resize avatar, bukan inferensi ML)
        from PIL import Image
        
        _, file_extension = os.path.splitext(file.filename)
        avatar_filename = f"avatar_{current_user.id}{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
        
        img = Image.open(file)
        img.thumbnail((300, 300))  # Ubah ukuran avatar
        img.save(file_path)

        avatar_access_url = f"/uploads/{avatar_filename}"
        
        current_user.avatar_url = avatar_access_url
        db.session.commit()

        return jsonify({"message": "Foto profil berhasil diunggah.", "avatarUrl": avatar_access_url}), 200
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error uploading avatar for user {current_user.username}: {e}")
        return jsonify({"error": "Gagal mengunggah foto profil."}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Melayani file yang diunggah."""
    safe_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
    requested_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    # Memastikan path yang diminta tidak keluar dari UPLOAD_FOLDER
    if not requested_path.startswith(safe_path):
        return jsonify({"error": "File tidak ditemukan"}), 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    app.run(debug=True, port=5000)
