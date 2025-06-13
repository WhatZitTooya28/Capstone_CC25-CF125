# File: backend/app.py

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
import requests  # Menggunakan requests untuk memanggil API
from PIL import Image
import io
from collections import Counter

app = Flask(__name__)
CORS(app)

# --- Konfigurasi Aplikasi ---
app.config['SECRET_KEY'] = 'ganti-dengan-kunci-rahasia-super-aman-anda-56789'
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_EXP_DELTA_SECONDS'] = 3600 * 24 

# --- Konfigurasi Database dan Folder Unggah ---
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
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Konfigurasi Model (Sekarang menggunakan data statis) ---
REMAP_DICT = {
    'battery': 'RESIDU', 'biological': 'ORGANIK', 'cardboard': 'ANORGANIK',
    'clothes': 'RESIDU', 'glass': 'ANORGANIK', 'metal': 'ANORGANIK',
    'paper': 'ANORGANIK', 'plastic': 'ANORGANIK', 'shoes': 'RESIDU', 'trash': 'RESIDU'
}
HANDLING_SUGGESTIONS = {
    'battery': 'Baterai bekas mengandung bahan logam berat. Harap kumpulkan dan bawa ke dropbox limbah B3 atau e-waste center agar tidak mencemari lingkungan.',
    'biological': 'Sisa makanan dan bahan organik dapat dikomposkan untuk menjadi pupuk alami yang bermanfaat untuk tanaman.',
    'cardboard': 'Kardus dapat dilipat dan dijual ke pengepul atau diserahkan ke tempat daur ulang. Pastikan kardus kering dan bersih.',
    'clothes': 'Pakaian layak pakai dapat disumbangkan. Jika rusak, buang ke tempat sampah residu.',
    'glass': 'Pisahkan botol dan kaca dengan hati-hati. Serahkan pada tempat daur ulang kaca untuk diproses kembali.',
    'metal': 'Kaleng dan jenis logam lainnya dapat dibersihkan dan dijual ke pengepul logam untuk mengurangi limbah.',
    'paper': 'Kertas bersih dapat dikumpulkan dan dijual ke bank sampah atau tempat daur ulang.',
    'plastic': 'Bersihkan plastik sebelum didaur ulang. Pisahkan dari sampah residu agar proses daur ulang optimal.',
    'shoes': 'Sepatu lama yang masih layak dapat disumbangkan. Jika rusak, buang ke tempat sampah residu.',
    'trash': 'Jenis sampah ini umumnya tidak dapat didaur ulang. Buang sesuai prosedur kebersihan.',
    'TIDAK DIKETAHUI': "Jenis sampah tidak dapat dikenali. Coba ambil gambar dengan lebih jelas."
}

# --- Model Database ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)

    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class ClassificationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    classification_result = db.Column(db.String(50), nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref=db.backref('histories', lazy=True, cascade="all, delete-orphan"))
    specific_name = db.Column(db.String(100), nullable=True)
    suggestion = db.Column(db.Text, nullable=True)

with app.app_context():
    db.create_all()

# --- Dekorator Autentikasi ---
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
        if not token: return jsonify({'message': 'Token tidak ditemukan!', 'error_code': 'TOKEN_MISSING'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
            current_user = User.query.filter_by(username=data['sub']).first()
            if not current_user: return jsonify({'message': 'Pengguna dengan token ini tidak ditemukan.', 'error_code': 'USER_NOT_FOUND'}), 401
        except Exception: return jsonify({'message': 'Token tidak valid!', 'error_code': 'TOKEN_INVALID'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# --- Fungsi Bantuan Prediksi ML (Menggunakan Hugging Face API) ---
def predict_image_from_api(image_bytes):
    # Ganti dengan URL API Inference dan Token dari akun Hugging Face Anda

    # GANTI DENGAN TOKEN ANDA
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes, timeout=25)
        response.raise_for_status()
        result = response.json()
        
        if not result or not isinstance(result, list):
            return None, None, 0.0, None, "Respons API tidak valid."
            
        best_prediction = max(result, key=lambda x: x['score'])
        predicted_label_specific = best_prediction['label']
        accuracy = float(best_prediction['score'])
        main_category = REMAP_DICT.get(predicted_label_specific, 'RESIDU')
        suggestions = [HANDLING_SUGGESTIONS.get(predicted_label_specific, HANDLING_SUGGESTIONS['TIDAK DIKETAHUI'])]
        
        return main_category, predicted_label_specific, accuracy, suggestions, None
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error memanggil Hugging Face API: {e}")
        return None, None, 0.0, None, f"Gagal terhubung ke server model. Model mungkin sedang dimuat, coba beberapa saat lagi."
    except Exception as e:
        app.logger.error(f"Error memproses respons API: {e}")
        return None, None, 0.0, None, f"Gagal memproses hasil prediksi: {e}"


# --- API Endpoints ---
@app.route('/api/register', methods=['POST'])
def register_user():
    data = request.get_json()
    if not data: return jsonify({"error": "Request body tidak valid (bukan JSON)"}), 400
    nama_pengguna = data.get('namaPengguna'); email = data.get('email'); password = data.get('password')
    if not all([nama_pengguna, email, password]): return jsonify({"error": "Data tidak lengkap"}), 400
    if User.query.filter_by(username=nama_pengguna).first(): return jsonify({"error": "Nama pengguna sudah terdaftar"}), 409
    if User.query.filter_by(email=email).first(): return jsonify({"error": "Email sudah terdaftar"}), 409
    new_user = User(username=nama_pengguna, email=email); new_user.set_password(password)
    try:
        db.session.add(new_user); db.session.commit()
        app.logger.info(f"Pengguna terdaftar: {nama_pengguna}")
        return jsonify({"message": f"Pengguna {nama_pengguna} berhasil terdaftar!"}), 201
    except Exception as e:
        db.session.rollback(); app.logger.error(f"Error registrasi: {e}")
        return jsonify({"error": "Gagal mendaftarkan pengguna, coba lagi."}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    data = request.get_json()
    if not data: return jsonify({"error": "Request body tidak valid (bukan JSON)"}), 400
    identifier = data.get('identifier'); password = data.get('password')
    if not all([identifier, password]): return jsonify({"error": "Data tidak lengkap"}), 400
    user_candidate = User.query.filter_by(username=identifier).first()
    if not user_candidate: user_candidate = User.query.filter_by(email=identifier).first()
    if user_candidate and user_candidate.check_password(password):
        payload = {'sub': user_candidate.username, 'email': user_candidate.email, 'user_id': user_candidate.id, 'iat': datetime.datetime.utcnow(), 'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=app.config['JWT_EXP_DELTA_SECONDS'])}
        try:
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])
            app.logger.info(f"Pengguna berhasil login: {user_candidate.username}")
            return jsonify({"message": "Login berhasil!", "token": token, "user": {"namaPengguna": user_candidate.username, "email": user_candidate.email, "id": user_candidate.id, "avatarUrl": user_candidate.avatar_url}}), 200
        except Exception as e:
            app.logger.error(f"Error saat generate token: {e}"); return jsonify({"error": "Gagal membuat token autentikasi"}), 500
    else:
        app.logger.warning(f"Gagal login untuk identifier: {identifier}"); return jsonify({"error": "Nama pengguna/email atau kata sandi salah"}), 401

@app.route('/api/klasifikasi', methods=['POST'])
@token_required
def klasifikasi_sampah_authenticated(current_user):
    if 'image' not in request.files: return jsonify({"error": "Tidak ada file gambar"}), 400
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename): return jsonify({"error": "File tidak valid"}), 400
    
    image_bytes = file.read()
    original_filename = secure_filename(file.filename)
    
    main_category, specific_category, accuracy, suggestions, error_msg = predict_image_from_api(image_bytes)
    if error_msg:
        return jsonify({"error": error_msg}), 500

    try:
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        unique_filename = f"{timestamp_str}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        image_access_url = f"/uploads/{unique_filename}"
        
        new_history = ClassificationHistory(
            user_id=current_user.id,
            filename=original_filename,
            image_url=image_access_url,
            classification_result=main_category,
            accuracy=accuracy,
            specific_name=specific_category.capitalize(),
            suggestion=suggestions[0] if suggestions else "Tidak ada saran penanganan."
        )
        db.session.add(new_history)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Gagal menyimpan riwayat: {e}")
        return jsonify({"error": "Gagal menyimpan riwayat ke database."}), 500

    response_data = { "kategori": main_category, "kategori_spesifik": specific_category, "akurasi": accuracy, "saran_penanganan": suggestions }
    return jsonify(response_data), 200

@app.route('/api/klasifikasi-guest', methods=['POST'])
def klasifikasi_sampah_guest():
    if 'image' not in request.files: return jsonify({"error": "Tidak ada file gambar"}), 400
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename): return jsonify({"error": "File tidak valid"}), 400
    
    image_bytes = file.read()
    main_category, specific_category, accuracy, suggestions, error_msg = predict_image_from_api(image_bytes)
    if error_msg:
        return jsonify({"error": error_msg}), 500
    
    response_data = { "kategori": main_category, "kategori_spesifik": specific_category, "akurasi": accuracy, "saran_penanganan": suggestions }
    return jsonify(response_data), 200
    
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
        if not history_item: return jsonify({"error": "Item riwayat tidak ditemukan atau Anda tidak berhak menghapusnya."}), 404
        if history_item.image_url:
            try:
                filename_only = history_item.image_url.split('/')[-1]
                file_to_delete_path = os.path.join(app.config['UPLOAD_FOLDER'], filename_only)
                if os.path.exists(file_to_delete_path):
                    os.remove(file_to_delete_path)
                    app.logger.info(f"File gambar {file_to_delete_path} berhasil dihapus.")
            except Exception as e_file_delete:
                app.logger.error(f"Failed to delete image file: {e_file_delete}")
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
        _, file_extension = os.path.splitext(file.filename)
        avatar_filename = f"avatar_{current_user.id}{file_extension}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], avatar_filename)
        
        img = Image.open(file)
        img.thumbnail((300, 300))
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
    """Serves uploaded files."""
    safe_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
    requested_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if not requested_path.startswith(safe_path): return jsonify({"error": "File tidak ditemukan"}), 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    app.run(debug=True, port=5000)