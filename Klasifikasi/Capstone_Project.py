# -*- coding: utf-8 -*-
"""Salinan dari Capstone_Project + deteksi anomali.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1xX1lM4aU749kPtXnV4ZCoFfzBX74AoY7

# Capstone Project TrashGu
- **ID Group Team:** CC25-CF125
- **Anggota Team:**
1. (ML) MC299D5X1601 - Agistia Ronna Aniqa
2. (ML) MC299D5X1752 - Evi Afiyatus Solihah
3. (ML) MC299D5X1751 - Rahmah Fauziah
4. (FEBE) FC265D5Y1786 - Fajar Anugrah
5. (FEBE) FC265D5Y1103 - M Reza Pahlevi
6. (FEBE) FC265D5Y1796 - Pebri Andika

## Install PIP
"""

# Menginstal berbagai library Python yang dibutuhkan
!pip install tensorflow tensorflowjs keras opendatasets pandas numpy matplotlib Pillow scipy scikit-learn seaborn

"""## Import Semua Packages/Library yang Digunakan"""

# Library yang sering digunakan
import os, shutil
import zipfile
import random
from random import sample
import shutil
from shutil import copyfile
import pathlib
from pathlib import Path
import uuid
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from tqdm.notebook import tqdm as tq

# Libraries untuk pemrosesan data gambar
import cv2
from PIL import Image, ImageOps
import skimage
from skimage import io
from skimage.transform import resize
from skimage.transform import rotate, AffineTransform, warp
from skimage import img_as_ubyte
from skimage.exposure import adjust_gamma
from skimage.util import random_noise

# Libraries untuk pembangunan model
import keras
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
import tensorflow as tf
from tensorflow.keras import Model, layers
from tensorflow.keras.preprocessing import image
from tensorflow.keras.preprocessing.image import ImageDataGenerator, img_to_array, load_img
from tensorflow.keras.optimizers import Adam, RMSprop, SGD
from tensorflow.keras.layers import InputLayer, Conv2D, SeparableConv2D, MaxPooling2D, MaxPool2D, Dense, Flatten, Dropout, BatchNormalization, GlobalAveragePooling2D
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.applications import MobileNet
from tensorflow.keras.applications.densenet import DenseNet121
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.callbacks import ModelCheckpoint, Callback, EarlyStopping, ReduceLROnPlateau
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models

# menonaktifkan warning yang mungkin muncul, seperti warning FutureWarning.
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

"""## Data Preparation"""

# Import module yang disediakan google colab untuk kebutuhan upload file
from google.colab import files
files.upload()

!mkdir -p ~/.kaggle
!cp kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json

# Download kaggle dataset and unzip the file
# !cp kaggle.json ~/.kaggle/

# !chmod 600 ~/.kaggle/kaggle.json
!kaggle datasets download -d mostafaabla/garbage-classification
!unzip garbage-classification.zip

# Download kaggle dataset and unzip the file
# !cp kaggle.json ~/.kaggle/

# !chmod 600 ~/.kaggle/kaggle.json
!kaggle datasets download -d sumn2u/garbage-classification-v2
!unzip garbage-classification-v2.zip

# Lokasi folder asal dan target
base_path = "/content/garbage_classification"
target_folder = os.path.join(base_path, "glass")
os.makedirs(target_folder, exist_ok=True)

# Folder-foler glass varian
glass_variants = ["brown-glass", "green-glass", "white-glass"]

# Gabungkan isi semua varian ke folder "glass"
for variant in glass_variants:
    variant_path = os.path.join(base_path, variant)
    for filename in os.listdir(variant_path):
        src = os.path.join(variant_path, filename)

        if not os.path.isfile(src):
            continue

        dst = os.path.join(target_folder, filename)

        # Hindari overwrite
        if os.path.exists(dst):
            base, ext = os.path.splitext(filename)
            i = 1
            while os.path.exists(dst):
                dst = os.path.join(target_folder, f"{base}_{i}{ext}")
                i += 1

        shutil.copy2(src, dst)

print("Penyatuan folder glass selesai.")

folders_to_delete = ["brown-glass", "green-glass", "white-glass"]
base_path = "/content/garbage_classification"

for folder in folders_to_delete:
    full_path = os.path.join(base_path, folder)
    if os.path.exists(full_path):
        shutil.rmtree(full_path)
        print(f"Folder '{folder}' dihapus.")
    else:
        print(f"Folder '{folder}' tidak ditemukan.")

# Path dua folder utama yang akan digabung
source_dirs = ["/content/garbage_classification", "/content/garbage-dataset"]
target_dir = "/content/combined_dataset"

# Buat folder gabungan
os.makedirs(target_dir, exist_ok=True)

# Gabungkan semua folder label
for src_dir in source_dirs:
    for label in os.listdir(src_dir):
        src_label_path = os.path.join(src_dir, label)

        if not os.path.isdir(src_label_path):
            continue  # Lewati file jika ada

        dst_label_path = os.path.join(target_dir, label)
        os.makedirs(dst_label_path, exist_ok=True)

        for filename in os.listdir(src_label_path):
            src_file = os.path.join(src_label_path, filename)

            if not os.path.isfile(src_file):
                continue

            dst_file = os.path.join(dst_label_path, filename)

            # Hindari overwrite jika nama file sama
            if os.path.exists(dst_file):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(dst_file):
                    dst_file = os.path.join(dst_label_path, f"{base}_{i}{ext}")
                    i += 1

            shutil.copy2(src_file, dst_file)

print("Penggabungan selesai. Folder gabungan ada di:", target_dir)

# Membuat kamus yang menyimpan gambar untuk setiap kelas dalam data
lung_image = {}

# Tentukan path sumber train
path = "/content/combined_dataset"
for i in os.listdir(path):
    lung_image[i] = os.listdir(os.path.join(path, i))

# Menampilkan secara acak 5 gambar di bawah setiap dari 2 kelas dari data.
# Anda akan melihat gambar yang berbeda setiap kali kode ini dijalankan.
path = "/content/combined_dataset"

# Menampilkan secara acak 5 gambar di bawah setiap kelas dari data latih
fig, axs = plt.subplots(len(lung_image.keys()), 5, figsize=(15, 15))

for i, class_name in enumerate(os.listdir(path)):
    images = np.random.choice(lung_image[class_name], 5, replace=False)

    for j, image_name in enumerate(images):
        img_path = os.path.join(path, class_name, image_name)
        img = Image.open(img_path)
        axs[i, j].imshow(img)
        axs[i, j].set(xlabel=class_name, xticks=[], yticks=[])


fig.tight_layout()

import glob

base_dir = "/content/combined_dataset"
data = []

for label in os.listdir(base_dir):
    label_folder = os.path.join(base_dir, label)
    if not os.path.isdir(label_folder):
        continue
    for file in os.listdir(label_folder):
        if file.endswith((".jpg", ".jpeg", ".png")):
            path = os.path.join(label_folder, file)
            data.append({'path': path, 'file_name': file, 'labels': label})

distribution_train = pd.DataFrame(data)

# --- Fungsi augmentasi sederhana ---
def augment_and_save(src_path, save_dir):
    img = Image.open(src_path)

    # Pilih augmentasi secara acak
    op = random.choice(['flip', 'rotate'])
    if op == 'flip':
        aug = ImageOps.mirror(img)
    else:
        angle = random.choice([90, 180, 270])
        aug = img.rotate(angle, expand=True)

    # Konversi ke RGB jika bukan RGB
    if aug.mode != 'RGB':
        aug = aug.convert("RGB")

    # Simpan dengan nama unik
    new_name = f"{uuid.uuid4().hex}.png"
    save_path = os.path.join(save_dir, new_name)
    aug.save(save_path)

    return new_name, save_path

# --- Hitung target balancing ---
class_counts = distribution_train['labels'].value_counts()
min_count    = class_counts.min()
target = min(min_count * 5, 5000)

# Folder output
output_dir = "/content/balanced_dataset"
os.makedirs(output_dir, exist_ok=True)

# DataFrame baru untuk menyimpan path hasil oversampling+augmentasi
new_rows = []

for label, group in distribution_train.groupby('labels'):
    label_folder = os.path.join(output_dir, label)
    os.makedirs(label_folder, exist_ok=True)

    if len(group) > target:
        # Undersample: ambil random subset
        sampled = group.sample(n=target, random_state=42)
        for _, row in tqdm(sampled.iterrows(), total=len(sampled), desc=f"Copying {label}"):
            dst = os.path.join(label_folder, row['file_name'])
            shutil.copyfile(row['path'], dst)
            new_rows.append({'path': dst, 'file_name': row['file_name'], 'labels': label})
    else:
        # Oversample + augmentasi
        repeats = target // len(group)
        rem     = target % len(group)

        # Ulangi full group beberapa kali
        for _ in range(repeats):
            for _, row in tqdm(group.iterrows(), total=len(group), desc=f"Augmenting {label} (repeat)"):
                fn, saved = augment_and_save(row['path'], label_folder)
                new_rows.append({'path': saved, 'file_name': fn, 'labels': label})

        # Ambil sisanya secara acak dan augment
        extra = group.sample(n=rem, random_state=42)
        for _, row in tqdm(extra.iterrows(), total=len(extra), desc=f"Augmenting {label} (extra)"):
            fn, saved = augment_and_save(row['path'], label_folder)
            new_rows.append({'path': saved, 'file_name': fn, 'labels': label})

# Gabungkan semua metadata jadi DataFrame
balanced_df = pd.DataFrame(new_rows)

import matplotlib.pyplot as plt
import seaborn as sns

# Menghitung jumlah gambar per kelas setelah proses oversampling + undersampling
class_counts_after = balanced_df['labels'].value_counts()

# Membuat plot bar chart
plt.figure(figsize=(10, 6))
sns.barplot(x=class_counts_after.index, y=class_counts_after.values, palette='viridis')

# Menambahkan label dan judul
plt.title("Distribusi Jumlah Gambar per Kelas Setelah Augmentasi & Undersampling", fontsize=14)
plt.xlabel("Kelas", fontsize=12)
plt.ylabel("Jumlah Gambar", fontsize=12)
plt.xticks(rotation=45)  # Rotasi label kelas jika terlalu panjang

# Menampilkan grafik
plt.tight_layout()
plt.show()

# --- Cek jumlah di folder ---
print("\nJumlah gambar per kelas di folder:")
for label in sorted(os.listdir(output_dir)):
    cnt = len(os.listdir(os.path.join(output_dir, label)))
    print(f"  {label}: {cnt} gambar")

"""### Split Dataset"""

# Splitting dataset (Train, Val, Test) dengan proporsi 80:10:10
dataset_path = '/content/balanced_dataset'
base_output = 'split_dataset'

split_ratio = {
    'train': 0.8,
    'val': 0.1,
    'test': 0.1
}

# Buat direktori output
for split in ['train', 'val', 'test']:
    for class_name in os.listdir(dataset_path):
        class_split_path = os.path.join(base_output, split, class_name)
        os.makedirs(class_split_path, exist_ok=True)

# Proses untuk setiap kelas
for class_name in os.listdir(dataset_path):
    class_path = os.path.join(dataset_path, class_name)
    if os.path.isdir(class_path):
        all_images = os.listdir(class_path)
        random.shuffle(all_images)

        total = len(all_images)
        train_end = int(total * split_ratio['train'])
        val_end = train_end + int(total * split_ratio['val'])

        train_imgs = all_images[:train_end]
        val_imgs = all_images[train_end:val_end]
        test_imgs = all_images[val_end:]

        # Copy ke folder tujuan
        for img_list, split in zip([train_imgs, val_imgs, test_imgs], ['train', 'val', 'test']):
            for img in img_list:
                src = os.path.join(class_path, img)
                dst = os.path.join(base_output, split, class_name, img)
                shutil.copyfile(src, dst)

for split in ['train', 'val', 'test']:
    total = 0
    print(f"\nJumlah gambar di {split}:")
    split_path = os.path.join(base_output, split)
    for class_name in os.listdir(split_path):
        class_dir = os.path.join(split_path, class_name)
        num_images = len(os.listdir(class_dir))
        total += num_images
        print(f"  {class_name}: {num_images} gambar")
    print(f"Total {split}: {total} gambar")

# Detail komposisi Splitting Data
base_dir = 'split_dataset'
img_size = (150, 150)
batch_size = 32

#Training set
train_ds = tf.keras.utils.image_dataset_from_directory(
    os.path.join(base_dir, 'train'),
    image_size=img_size,
    batch_size=batch_size,
    label_mode='categorical'
)

# Validation set
val_ds = tf.keras.utils.image_dataset_from_directory(
    os.path.join(base_dir, 'val'),
    image_size=img_size,
    batch_size=batch_size,
    label_mode='categorical'
)

#Test set
test_ds = tf.keras.utils.image_dataset_from_directory(
    os.path.join(base_dir, 'test'),
    image_size=img_size,
    batch_size=batch_size,
    label_mode='categorical'
)

# Visualisasi sample foto pada masing masing split
class_names = train_ds.class_names

def show_images(dataset, title="Split Preview"):
    plt.figure(figsize=(12, 8))
    for images, labels in dataset.take(1):
        for i in range(8):
            ax = plt.subplot(2, 4, i + 1)
            plt.imshow(images[i].numpy().astype("uint8"))
            label_index = tf.argmax(labels[i]).numpy()
            plt.title(class_names[label_index])
            plt.axis("off")
    plt.suptitle(title)
    plt.tight_layout()
    plt.show()

show_images(train_ds, title="Training Set")
show_images(val_ds, title="Validation Set")
show_images(test_ds, title="Test Set")

"""## Modelling

### Augmentasi dan Load Dataset (Train, Validation, Test)
"""

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, BatchNormalization, MaxPooling2D, Dropout, GlobalAveragePooling2D, Dense
from tensorflow.keras.optimizers import Adam

# Gunakan mixed precision untuk menghemat RAM
tf.keras.mixed_precision.set_global_policy('mixed_float16')

# Buat model
model = Sequential([
    Conv2D(64, (3, 3), activation='relu', padding='same', input_shape=(150, 150, 3)),
    BatchNormalization(),
    MaxPooling2D(2, 2),
    Dropout(0.2),  # Dropout sedikit lebih kecil

    Conv2D(128, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(2, 2),
    Dropout(0.2),

    Conv2D(256, (3, 3), activation='relu', padding='same'),
    BatchNormalization(),
    MaxPooling2D(2, 2),
    Dropout(0.2),

    GlobalAveragePooling2D(),

    Dense(128, activation='relu'),
    Dropout(0.2),
    Dense(64, activation='relu'),
    Dropout(0.2),
    Dense(10, activation='softmax')  # 10 kelas
])

# Compile model dengan optimasi RAM
model.compile(
    optimizer=Adam(learning_rate=0.0005),
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Gunakan learning rate decay untuk menghemat resource training
reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, verbose=1)

# Tampilkan arsitektur
model.summary()

# Callback
checkpoint = ModelCheckpoint("saved_model.keras", save_best_only=True, monitor="val_accuracy", mode="max")
early_stop = EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True)

callbacks_list = [checkpoint, early_stop]

history = model.fit(
    train_ds,
    validation_data=val_ds,
    epochs=50,
    callbacks=callbacks_list
)

"""### Membangun dan Melatih Model"""

# Plot akurasi
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Training Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.title('Akurasi Model')
plt.xlabel('Epoch')
plt.ylabel('Akurasi')
plt.legend()
plt.grid(True)

# Plot loss
plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Loss Model')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()

train_loss, train_acc = model.evaluate(train_ds)
print(f"Akurasi di train set: {train_acc:.2%}")

val_loss, val_acc = model.evaluate(val_ds)
print(f"Akurasi di val set: {val_acc:.2%}")

test_loss, test_acc = model.evaluate(test_ds)
print(f"Akurasi di test set: {test_acc:.2%}")

# Konversi model ke Saved_model
model.export('saved_model')

# Install TensorFlow.js converter
!pip install tensorflowjs

# Import library tensorflowjs
import tensorflowjs as tfjs

# Buat direktori untuk menyimpan model TFJS
!mkdir -p tfjs_model

# Simpan model ke format TFJS
tfjs.converters.save_keras_model(model2, 'tfjs_model')

from google.colab import files

# Zip semua model yang disimpan
!zip -r model_artifacts.zip saved_model tfjs_model tflite
# Download hasil zip
files.download("model_artifacts.zip")

# Load model dari folder SavedModel
model = tf.saved_model.load("saved_model")

# Upload file gambar (misal .jpg)
from google.colab import files

uploaded = files.upload()
img_path = list(uploaded.keys())[0]

# # Load gambar
img = image.load_img(img_path, target_size=(150, 150))
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0)  # Menambahkan batch dimension

# Prediksi
predictions = model2.predict(img_array)

# Melihat probabilitas untuk setiap kelas
print(predictions)

# Menentukan label untuk setiap kelas
class_labels = ['battery', 'cardboard', 'metal', 'gelas', 'biological', 'clothes', 'paper', 'plastic', 'shoes', 'trash']  # Ganti dengan label kelas yang sesuai

# Mengambil kelas dengan probabilitas tertinggi
predicted_class = np.argmax(predictions, axis=1)
predicted_label = class_labels[predicted_class[0]]

# Menampilkan gambar
plt.imshow(img)
plt.axis('off')  # Menyembunyikan axis
plt.title(f"Prediksi: {predicted_label}\nProbabilitas: {predictions[0][predicted_class[0]]:.4f}")
plt.show()

"""## Menyimpan Model"""



"""## Inference"""

