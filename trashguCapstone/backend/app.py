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
import requests # Library baru untuk memanggil API
from PIL import Image
import io # Library untuk memproses gambar di memori
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

# --- Model Database (Tidak ada perubahan) ---
# ... (kode model User dan ClassificationHistory tetap sama) ...
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

# --- Dekorator Autentikasi (Tidak ada perubahan) ---
# ... (kode token_required tetap sama) ...
def token_required(f):
    # ...
    return f

# --- Fungsi Bantuan Prediksi ML (DIUBAH TOTAL) ---
def predict_image_from_api(image_bytes):
    # Ganti dengan URL API Inference dari Hugging Face Anda
    API_URL = "https://api-inference.huggingface.co/models/username-anda/nama-repo-model-anda" 
    # Ganti dengan token akses Hugging Face Anda
    HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        response.raise_for_status() # Akan error jika status code bukan 2xx
        result = response.json()
        
        # Proses hasil dari Hugging Face
        # Asumsi hasilnya adalah list of dictionaries: [{'label': 'plastic', 'score': 0.99...}]
        if not result or not isinstance(result, list):
            return None, None, 0.0, None, "Respons API tidak valid."
            
        best_prediction = max(result, key=lambda x: x['score'])
        predicted_label_specific = best_prediction['label']
        accuracy = float(best_prediction['score'])

        # Logika pemetaan yang sudah ada
        main_category = REMAP_DICT.get(predicted_label_specific, 'RESIDU')
        suggestions = [HANDLING_SUGGESTIONS.get(predicted_label_specific, HANDLING_SUGGESTIONS['TIDAK DIKETAHUI'])]
        
        return main_category, predicted_label_specific, accuracy, suggestions, None
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error memanggil Hugging Face API: {e}")
        return None, None, 0.0, None, f"Gagal terhubung ke server model: {e}"
    except Exception as e:
        app.logger.error(f"Error memproses respons API: {e}")
        return None, None, 0.0, None, f"Gagal memproses hasil prediksi: {e}"


# --- API Endpoints ---
@app.route('/api/klasifikasi', methods=['POST'])
@token_required
def klasifikasi_sampah_authenticated(current_user):
    if 'image' not in request.files: return jsonify({"error": "Tidak ada file gambar yang dikirim"}), 400
    file = request.files['image']
    if file.filename == '' or not allowed_file(file.filename): return jsonify({"error": "File tidak valid atau tidak diizinkan"}), 400
    
    # Baca gambar sebagai bytes untuk dikirim ke API
    image_bytes = file.read()
    # Simpan juga filenya untuk URL akses
    original_filename = secure_filename(file.filename)
    # ... logika penyimpanan file ...
    
    main_category, specific_category, accuracy, suggestions, error_msg = predict_image_from_api(image_bytes)
    
    # ... sisa logika untuk menyimpan ke database sama seperti sebelumnya ...
    
    return jsonify(response_data), 200

# ... (semua endpoint lain tetap sama) ...

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    app.run(debug=True, port=5000)
