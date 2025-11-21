import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import torch
import timm
import numpy as np
import torchvision.transforms as T
import threading
import os

# ----------------- SETTINGS -----------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_FOLDER = "models"
MODEL_FILES = {
    "convnext_large_in22ft1k": os.path.join(MODEL_FOLDER, "convnext_large_in22ft1k.pth"),
    "swin_base_patch4_window7_224": os.path.join(MODEL_FOLDER, "swin_base_patch4_window7_224.pth"),
    "tf_efficientnet_b4_ns": os.path.join(MODEL_FOLDER, "tf_efficientnet_b4_ns.pth"),
}
DEFAULT_TEST_IMAGE = "/mnt/data/c14ae7ce-d62c-4a9d-9e6b-103d1a6100fa.png"  # example you uploaded; optional

IMG_SIZE = 224
transform = T.Compose([
    T.Resize((IMG_SIZE, IMG_SIZE)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225])
])

# ----------------- Load class names -----------------
def load_class_names(path="class_names.txt"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"class names file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        names = [line.strip() for line in f.readlines() if line.strip()]
    return names

# ----------------- Model loading -----------------
def create_and_load(model_name, path, num_classes):
    model = timm.create_model(model_name, pretrained=False, num_classes=num_classes)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Model file not found: {path}")
    # Load to CPU first then move to DEVICE
    state = torch.load(path, map_location="cpu")
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model

# ----------------- GUI App -----------------
class DogBreedApp:
    def __init__(self, root):
        self.root = root
        root.title("Dog Breed Predictor — Ensemble")
        root.geometry("800x600")

        # Top frame for buttons
        top = tk.Frame(root)
        top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        self.open_btn = tk.Button(top, text="Open Image", command=self.open_image)
        self.open_btn.pack(side=tk.LEFT, padx=4)

        self.predict_btn = tk.Button(top, text="Predict", command=self.predict_image, state=tk.DISABLED)
        self.predict_btn.pack(side=tk.LEFT, padx=4)

        self.status_label = tk.Label(top, text="Load models first...", fg="blue")
        self.status_label.pack(side=tk.LEFT, padx=12)

        # Canvas for image
        self.canvas = tk.Canvas(root, width=640, height=420, bg="gray")
        self.canvas.pack(padx=8, pady=8)

        # Bottom frame for results
        bottom = tk.Frame(root)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=8)

        self.result_label = tk.Label(bottom, text="Breed: N/A", font=("Helvetica", 14))
        self.result_label.pack(side=tk.LEFT, padx=8)

        self.conf_label = tk.Label(bottom, text="Confidence: N/A", font=("Helvetica", 14))
        self.conf_label.pack(side=tk.LEFT, padx=12)

        # Load classes and models in background
        self.class_names = []
        self.models = {}
        threading.Thread(target=self._load_resources, daemon=True).start()

        self.current_image_path = None
        self.current_tkimage = None

    def _load_resources(self):
        try:
            self.class_names = load_class_names("class_names.txt")
        except Exception as e:
            self._update_status(f"Missing class_names.txt - create it (one breed per line).", error=True)
            return

        # sanity: class count
        n = len(self.class_names)
        self._update_status(f"Loaded {n} class names. Loading models...")

        # load models
        for mn, p in MODEL_FILES.items():
            try:
                self.models[mn] = create_and_load(mn, p, num_classes=n)
                self._update_status(f"Loaded {mn}")
            except Exception as e:
                self._update_status(f"Failed loading {mn}: {e}", error=True)
                return

        self._update_status("Models loaded — ready")
        self.predict_btn.config(state=tk.NORMAL)

        # Optionally show default image
        if os.path.exists(DEFAULT_TEST_IMAGE):
            self._display_image(DEFAULT_TEST_IMAGE)
            self.current_image_path = DEFAULT_TEST_IMAGE
            # do not auto-predict; let user press Predict

    def _update_status(self, text, error=False):
        def upd():
            self.status_label.config(text=text, fg="red" if error else "green")
        self.root.after(0, upd)

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")])
        if not path:
            return
        self.current_image_path = path
        self._display_image(path)
        self.result_label.config(text="Breed: N/A")
        self.conf_label.config(text="Confidence: N/A")

    def _display_image(self, path):
        pil = Image.open(path).convert("RGB")
        # fit into canvas
        w, h = pil.size
        max_w, max_h = 640, 420
        scale = min(max_w / w, max_h / h, 1.0)
        new_w, new_h = int(w * scale), int(h * scale)
        pil_resized = pil.resize((new_w, new_h), Image.LANCZOS)
        self.current_tkimage = ImageTk.PhotoImage(pil_resized)
        self.canvas.delete("all")
        self.canvas.create_image(max_w // 2, max_h // 2, image=self.current_tkimage)
        self.canvas.config(width=max_w, height=max_h)

    def predict_image(self):
        if not self.current_image_path:
            messagebox.showinfo("Info", "Open an image first.")
            return
        # run prediction in background so GUI stays responsive
        threading.Thread(target=self._predict_background, daemon=True).start()

    def _predict_background(self):
        self._update_status("Predicting...", error=False)
        try:
            img = Image.open(self.current_image_path).convert("RGB")
            x = transform(img).unsqueeze(0).to(DEVICE)

            probs_total = None
            for mn, model in self.models.items():
                with torch.no_grad():
                    out = model(x)
                    probs = torch.softmax(out, dim=1).cpu().numpy()[0]
                probs_total = probs if probs_total is None else probs_total + probs

            probs_total /= len(self.models)
            idx = int(np.argmax(probs_total))
            breed = self.class_names[idx]
            conf = float(probs_total[idx]) * 100.0

            # update UI
            self.root.after(0, lambda: self.result_label.config(text=f"Breed: {breed}"))
            self.root.after(0, lambda: self.conf_label.config(text=f"Confidence: {conf:.2f}%"))
            self._update_status("Prediction done", error=False)
        except Exception as e:
            self._update_status(f"Prediction error: {e}", error=True)

# ----------------- Start the app -----------------
if __name__ == "__main__":
    root = tk.Tk()
    app = DogBreedApp(root)
    root.mainloop()
