import torch
from torchvision import transforms
from PIL import Image
import timm
import io

# Load class names
with open("class_names.txt", "r") as f:
    class_names = [c.strip() for c in f.readlines()]


def load_model():
    model_path = "models/swin_base_patch4_window7_224.pth"

    print(f"Loading model weights from: {model_path}")

    # 1️⃣ Create model architecture
    model = timm.create_model(
        "swin_base_patch4_window7_224",
        pretrained=False,
        num_classes=len(class_names)
    )

    # 2️⃣ Load weights (state_dict)
    state_dict = torch.load(model_path, map_location="cpu")

    # Sometimes training saves inside ['model'] key
    if isinstance(state_dict, dict) and "model" in state_dict:
        state_dict = state_dict["model"]

    model.load_state_dict(state_dict, strict=False)

    model.eval()
    return model


model = load_model()


def predict_breed(image_file):
    # Work with Streamlit uploaded file or path
    if not isinstance(image_file, str):
        image = Image.open(io.BytesIO(image_file.read())).convert("RGB")
    else:
        image = Image.open(image_file).convert("RGB")

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor()
    ])

    img = transform(image).unsqueeze(0)

    with torch.no_grad():
        preds = model(img)
        idx = preds.argmax().item()
        confidence = float(preds[0][idx])

    return class_names[idx], confidence
