import cv2
import os
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import torch
from ollama import chat

def extract_frames(video_path, output_folder, fps=1):
    os.makedirs(output_folder, exist_ok=True)
    video = cv2.VideoCapture(video_path)

    video_fps = video.get(cv2.CAP_PROP_FPS)
    frame_interval = int(video_fps // fps)

    count, saved = 0, 0
    while True:
        success, frame = video.read()
        if not success:
            break
        if count % frame_interval == 0:
            frame_path = os.path.join(output_folder, f"frame_{saved:04d}.jpg")
            cv2.imwrite(frame_path, frame)
            saved += 1
        count += 1

    video.release()
    print(f"✅ {saved} frames saved to: {output_folder}")

def describe_images(frame_folder):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)

    descriptions = {}
    for filename in sorted(os.listdir(frame_folder)):
        if filename.endswith(".jpg"):
            image_path = os.path.join(frame_folder, filename)
            raw_image = Image.open(image_path).convert('RGB')

            inputs = processor(raw_image, return_tensors="pt").to(device)
            output = model.generate(**inputs)
            caption = processor.decode(output[0], skip_special_tokens=True)

            descriptions[filename] = caption
            print(f"{filename}: {caption}")
    return descriptions

def generate_instructions_ollama(descriptions, model="mistral"):
    caption_list = [f"{i+1}. {desc}" for i, desc in enumerate(descriptions.values())]
    joined_captions = "\n".join(caption_list)

    prompt = (
        "Je bent een assistent die duidelijke werkinstructies schrijft voor mensen met een cognitieve beperking.\n"
        "Zorg dat elke stap eenvoudig is en in opdrachtvorm geschreven.\n\n"
        "Hier zijn de observaties uit een video:\n"
        f"{joined_captions}\n\n"
        "Genereer een genummerde lijst met eenvoudige instructies:"
    )

    response = chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response['message']['content']

if __name__ == "__main__":
    video_path = "test_video.mp4"
    output_folder = "frames"

    extract_frames(video_path, output_folder, fps=1)
    descriptions = describe_images(output_folder)
    instructions = generate_instructions_ollama(descriptions)

    print("\n📋 gegenereerde werkinstructies:\n")
    print(instructions)

    with open("instructions.txt", "w") as f:
        f.write(instructions)
