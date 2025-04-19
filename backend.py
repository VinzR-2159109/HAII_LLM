import os
import cv2
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration
from ollama import chat

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def extract_frames(video_path, output_folder="frames", fps=1):
    os.makedirs(output_folder, exist_ok=True)
    video = cv2.VideoCapture(video_path)
    video_fps = video.get(cv2.CAP_PROP_FPS)
    interval = int(video_fps // fps)
    count = saved = 0
    paths = []

    while True:
        ret, frame = video.read()
        if not ret:
            break
        if count % interval == 0:
            path = os.path.join(output_folder, f"frame_{saved:04d}.jpg")
            cv2.imwrite(path, frame)
            paths.append(path)
            saved += 1
        count += 1

    video.release()
    return paths

def describe_images(paths, update_progress):
    descriptions = []
    total = len(paths)
    for i, path in enumerate(paths):
        image = Image.open(path).convert("RGB")
        inputs = processor(image, return_tensors="pt").to(device)
        out = model.generate(**inputs)
        caption = processor.decode(out[0], skip_special_tokens=True)
        descriptions.append(caption)
        update_progress((i + 1) / total)
    return descriptions

def generate_instructions_ollama(descriptions, update_progress=None, model="mistral"):
    caption_list = [f"{i+1}. {desc}" for i, desc in enumerate(descriptions)]
    joined_captions = "\n".join(caption_list)

    prompt = (
        "Je bent een assistent die duidelijke werkinstructies schrijft voor mensen met een cognitieve beperking.\n"
        "Zorg dat elke stap eenvoudig is en in opdrachtvorm geschreven.\n\n"
        "Hier zijn de observaties uit een video:\n"
        f"{joined_captions}\n\n"
        "Genereer een genummerde lijst met eenvoudige instructies:"
    )

    if update_progress:
        update_progress(0.1)
    response = chat(model=model, messages=[{"role": "user", "content": prompt}])
    if update_progress:
        update_progress(1.0)
    return response['message']['content']
