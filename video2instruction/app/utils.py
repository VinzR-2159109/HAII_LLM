import os
import cv2
import base64
import shutil
from ollama import chat, generate

def handle_video(video_path, fps=1):
    os.makedirs("media/frames", exist_ok=True)
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
            path = os.path.join("media/frames", f"frame_{saved:04d}.jpg")
            cv2.imwrite(path, frame)
            paths.append(path)
            saved += 1
        count += 1

    video.release()
    return paths

def ask_questions(paths, context, model="llava"):
    image_base64_list = []
    for path in paths:
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        image_base64_list.append(image_base64)

    prompt = (
        f"The user provided the following context:\n{context.strip()}\n\n"
        "You will now see several images extracted from a video.\n"
        "Your task is to help create clear, step-by-step work instructions.\n\n"
        "Before doing so, ask one clear and relevant clarifying question to better understand the task shown.\n"
        "- Only ask a question if the answer is essential to describe the task correctly.\n"
        "- Ask only one question.\n"
        "- Use a single sentence.\n"
        "- Do not include numbering or bullet points.\n"
    )

    response = generate(
        model=model,
        prompt=prompt,
        images=image_base64_list
    )

    return response["response"].strip()

def describe_images(paths, context, model="llava", update_progress=None):
    descriptions = []
    total = len(paths)

    for i, path in enumerate(paths):
        try:
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            previous_steps = "\n".join(
                [f"{j+1}. {desc['description']}" for j, desc in enumerate(descriptions)]
            )

            prompt = (
                f"You are helping create work instructions for people with cognitive disabilities.\n\n"
                f"Context provided by the user:\n{context.strip()}\n\n"
            )

            if i > 0:
                prompt += (
                    f"These are the previous {i} steps:\n{previous_steps}\n\n"
                    f"Now describe image #{i+1}."
                )
            else:
                prompt += "Now describe the first image."

            prompt += (
                "\nDescribe the action in one clear, simple sentence."
                "\nFocus on what the person is doing or manipulating."
                "\nAvoid repeating earlier steps."
            )

            response = generate(
                model=model,
                prompt=prompt,
                images=[image_base64]
            )

            description = response["response"].strip()
            descriptions.append({"path": path, "description": description})

            if update_progress:
                update_progress((i + 1) / total)

            print(description)

        except Exception as e:
            print(f"Error describing {path}: {e}")
            descriptions.append({"path": path, "description": "Error generating description."})

    return descriptions

def generate_instructions(descriptions, model="llava"):
    prompt = (
        "You are an assistant that writes clear, step-by-step work instructions for people with cognitive disabilities.\n"
        "Each instruction is based on a visual frame and its description.\n"
        "Use the image and its caption to create one numbered instruction per frame.\n"
        "Make each instruction short, direct, and actionable.\n"
    )

    images = []
    image_instructions = []

    for i, item in enumerate(descriptions):
        path = item["path"]
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        images.append(image_base64)
        image_instructions.append(f"{i+1}. {item['description']}")

    prompt += "\nHere are the images and their descriptions:\n" + "\n".join(image_instructions)
    prompt += "\n\nNow generate a list of clear, easy-to-follow instructions."

    response = generate(model=model, prompt=prompt, images=images)
    instructions = response["response"].strip()

    return instructions

