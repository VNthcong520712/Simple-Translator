import customtkinter as ctk
from tkinter import messagebox
import tensorflow as tf
import pickle
from tensorflow.keras.preprocessing.sequence import pad_sequences
from PIL import Image

# ==============================
# CẤU HÌNH
# ==============================
MAXLEN = 60
MODEL_PATH = "model1/transformer_saved_model"
SRC_TOKENIZER_PATH = "model1/tokenizer_src.pkl"
TGT_TOKENIZER_PATH = "model1/tokenizer_tgt.pkl"

# ==============================
# LOAD MODEL + TOKENIZER
# ==============================
try:
    with open(SRC_TOKENIZER_PATH, "rb") as f:
        tokenizer_src = pickle.load(f)
    with open(TGT_TOKENIZER_PATH, "rb") as f:
        tokenizer_tgt = pickle.load(f)
    model = tf.saved_model.load(MODEL_PATH)
    serving_fn = model.signatures["serving_default"]
    print("✅ Loaded model & tokenizers successfully!")
except Exception as e:
    print("❌ Error loading model:", e)
    raise SystemExit()

# ==============================
# MASKS
# ==============================
def create_padding_mask(seq):
    seq = tf.cast(tf.math.equal(seq, 0), tf.float32)
    return seq[:, tf.newaxis, tf.newaxis, :]

def create_look_ahead_mask(size):
    mask = 1 - tf.linalg.band_part(tf.ones((size, size)), -1, 0)
    return mask

def create_masks(inputs, targets):
    enc_padding_mask = create_padding_mask(inputs)
    dec_padding_mask = create_padding_mask(inputs)
    look_ahead_mask = create_look_ahead_mask(tf.shape(targets)[1])
    dec_target_padding_mask = create_padding_mask(targets)
    combined_mask = tf.maximum(dec_target_padding_mask, look_ahead_mask)
    return enc_padding_mask, combined_mask, dec_padding_mask

# ==============================
# TRANSLATE FUNCTION
# ==============================
def translate_sentence(sentence: str):
    sentence = "sos " + sentence.strip() + " eos."
    sequence = tokenizer_src.texts_to_sequences([sentence])
    input_tensor = pad_sequences(sequence, maxlen=MAXLEN, padding='post', truncating='post')
    input_tensor = tf.convert_to_tensor(input_tensor, dtype=tf.int64)

    decoder_input = tokenizer_tgt.texts_to_sequences(['sos'])
    decoder_input = tf.convert_to_tensor(decoder_input, dtype=tf.int64)

    for _ in range(MAXLEN):
        enc_padding_mask, combined_mask, dec_padding_mask = create_masks(input_tensor, decoder_input)
        outputs = serving_fn(
            args_0=input_tensor,
            args_1=decoder_input,
            args_3=enc_padding_mask,
            args_4=combined_mask,
            args_5=dec_padding_mask
        )
        predictions = outputs['output_1']
        predictions = predictions[:, -1:, :]
        predicted_id = tf.cast(tf.argmax(predictions, axis=-1), tf.int64)

        if predicted_id == tokenizer_tgt.word_index.get('eos'):
            break
        decoder_input = tf.concat([decoder_input, predicted_id], axis=1)

    result = tokenizer_tgt.sequences_to_texts(decoder_input.numpy())[0]
    result = result.replace("sos ", "").replace(" eos", "").strip()
    return result

# ==============================
# GIAO DIỆN HIỆN ĐẠI
# ==============================
ctk.set_appearance_mode("System")  # "Dark" hoặc "Light"
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("🌍 AI Translator - English ↔ Vietnamese")
app.geometry("720x520")
app.resizable(False, False)

# === ICON (tuỳ chọn) ===
try:
    app.iconbitmap("translator.ico")
except:
    pass

# === TIÊU ĐỀ ===
title_label = ctk.CTkLabel(app, text="🌍 AI Translator (Anh ↔ Việt)", 
                           font=ctk.CTkFont(size=24, weight="bold"))
title_label.pack(pady=(20,10))

# === FRAME CHÍNH ===
main_frame = ctk.CTkFrame(app, corner_radius=15)
main_frame.pack(pady=20, padx=20, fill="both", expand=True)

# === INPUT TEXT ===
input_label = ctk.CTkLabel(main_frame, text="Nhập câu cần dịch:", font=ctk.CTkFont(size=14))
input_label.pack(anchor="w", padx=15, pady=(15,5))

input_box = ctk.CTkTextbox(main_frame, width=640, height=120, corner_radius=12)
input_box.pack(padx=15)

# === BUTTON ===
def on_translate():
    src_text = input_box.get("1.0", "end").strip()
    if not src_text:
        messagebox.showwarning("Cảnh báo", "Vui lòng nhập câu cần dịch!")
        return
    result_label.configure(text="⏳ Đang dịch...", text_color="#999")
    app.update()
    try:
        translated = translate_sentence(src_text)
        result_label.configure(text=translated, text_color="#000")
    except Exception as e:
        result_label.configure(text="❌ Lỗi khi dịch!", text_color="red")
        print(e)

translate_btn = ctk.CTkButton(main_frame, text="Dịch ngay 🚀", width=200, height=40,
                              font=ctk.CTkFont(size=15, weight="bold"),
                              command=on_translate)
translate_btn.pack(pady=15)

# === OUTPUT BOX ===
output_label = ctk.CTkLabel(main_frame, text="Bản dịch:", font=ctk.CTkFont(size=14))
output_label.pack(anchor="w", padx=15, pady=(5,5))

result_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=16),
                            width=640, height=120, justify="left", wraplength=600,
                            corner_radius=12, fg_color="#f1f1f1", text_color="#000")
result_label.pack(padx=15, pady=(0,15))

footer = ctk.CTkLabel(app, text="✨ Powered by Transformer & TensorFlow ✨", font=ctk.CTkFont(size=12))
footer.pack(pady=(0,15))

app.mainloop()
