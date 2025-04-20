import os
import cv2
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from ollama import chat
from ollama import generate
import base64

processor = AutoProcessor.from_pretrained("microsoft/git-large")
model = AutoModelForCausalLM.from_pretrained("microsoft/git-large")
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



def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def describe_images(paths, update_progress):
    descriptions = []
    total = len(paths)

    for i, path in enumerate(paths):
        image_base64 = image_to_base64(path)

        prompt = "Describe what the person is doing in the image."

        response = generate(
            model="llava",
            prompt=prompt,
            images=[image_base64]
        )

        description = response["response"].strip()
        descriptions.append(description)
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


if __name__ == "__main__":
    video_path = "test_video.mp4"
    output_folder = "frames"
    fps = 1

    # Extract frames from the video
    frame_paths = extract_frames(video_path, output_folder, fps)

    # Describe images
    descriptions = describe_images(frame_paths, lambda x: print(f"Progress: {x*100:.2f}%"))

    # Generate instructions using Ollama
    instructions = generate_instructions_ollama(descriptions, lambda x: print(f"Progress: {x*100:.2f}%"))
    print(instructions)