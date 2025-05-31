import os
import cv2
import base64

from django.conf import settings
from ollama import generate

from typing import List
from pydantic import BaseModel
from langchain.output_parsers import PydanticOutputParser

def handle_video(video_path, fps=1):
    frame_dir = os.path.join(settings.MEDIA_ROOT, "frames")
    os.makedirs(frame_dir, exist_ok=True)

    for f in os.listdir(frame_dir):
        os.remove(os.path.join(frame_dir, f))

    video = cv2.VideoCapture(video_path)
    video_fps = video.get(cv2.CAP_PROP_FPS)
    interval = int(video_fps // fps)
    count = saved = 0
    frames = []

    while True:
        ret, frame = video.read()
        if not ret:
            break
        if count % interval == 0:
            filename = f"frame_{saved:04d}.jpg"
            full_path = os.path.join(frame_dir, filename)
            cv2.imwrite(full_path, frame)
            frames.append({
                "path": full_path,
                "url": f"frames/{filename}"
            })
            saved += 1
        count += 1

    video.release()
    return frames


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

def describe_images(frame_data, context, model="llava", update_progress=None):
    descriptions = []
    total = len(frame_data)

    for i, item in enumerate(frame_data):
        try:
            with open(item["path"], "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            previous_steps = "\n".join(
                [f"{j+1}. {desc['description']}" for j, desc in enumerate(descriptions)]
            )

            prompt = f"You are helping create work instructions for people with cognitive disabilities.\n\n"
            prompt += f"Context provided by the user:\n{context.strip()}\n\n"
            if i > 0:
                prompt += f"These are the previous {i} steps:\n{previous_steps}\n\n"
            prompt += f"Now describe image #{i+1}."
            prompt += "\nDescribe the action in one clear, simple sentence.\nAvoid repeating earlier steps."

            response = generate(model=model, prompt=prompt, images=[image_base64])
            description = response["response"].strip()

            descriptions.append({
                "path": item["path"],
                "url": item["url"],
                "description": description
            })

            if update_progress:
                update_progress((i + 1) / total)

        except Exception as e:
            print(f"Error describing {item['path']}: {e}")
            descriptions.append({
                "path": item["path"],
                "url": item["url"],
                "description": "Error generating description."
            })

    return descriptions


class InstructionSet(BaseModel):
    instructions: List[str]

def generate_instructions(descriptions, model="llava"):
    images = []
    image_instructions = []

    for item in descriptions:
        path = item["path"]
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        images.append(image_base64)
        image_instructions.append(item['description'])

    parser = PydanticOutputParser(pydantic_object=InstructionSet)

    prompt = (
        "You are a careful assistant that generates one short, clear instruction per image description, "
        "suitable for people with cognitive disabilities.\n"
        "Instructions must be simple, actionable, and easy to follow.\n"
        "Do not reference images or numbers.\n"
        "Write only one instruction per description.\n\n"
        "Descriptions:\n"
    )

    prompt += "\n".join(f"- {desc}" for desc in image_instructions)

    prompt += (
        "\n\nNow respond in this exact JSON format:\n\n"
        "{\n"
        '  "instructions": [\n'
        '    "Instruction for first description.",\n'
        '    "Instruction for second description.",\n'
        '    "..."\n'
        "  ]\n"
        "}\n\n"
        "Respond with JSON only. Do not include explanations. Do not include a JSON schema. Do not include markdown (no ```json)."
    )

    response = generate(model=model, prompt=prompt, images=images)
    raw = response["response"]
    print("Raw response:", raw)

    try:
        parsed_obj = parser.parse(raw)
        return parsed_obj.instructions
    except Exception as e:
        print(f"LangChain parsing failed: {e}")
        return []

def refine_instructions(instructions, user_context, model="llava"):
    parser = PydanticOutputParser(pydantic_object=InstructionSet)

    prompt = (
        "You are refining existing work instructions for people with cognitive disabilities.\n\n"
        "Context provided by the user:\n"
        f"{user_context.strip()}\n\n"
        "Here are the current instructions:\n"
    )

    prompt += "\n".join(f"- {instr}" for instr in instructions)

    prompt += (
        "\n\nPlease rewrite each instruction to be clearer, simpler, and more actionable for the target audience.\n"
        "Do not reference numbering or images.\n"
        "Do not merge instructions.\n"
        "Preserve the original step order.\n\n"
        "Respond in this exact JSON format:\n\n"
        "{\n"
        '  "instructions": [\n'
        '    "Refined instruction 1.",\n'
        '    "Refined instruction 2.",\n'
        '    "..."\n'
        "  ]\n"
        "}\n\n"
        "Respond with JSON only. Do not include explanations. Do not include a JSON schema. Do not include markdown."
    )

    response = generate(model=model, prompt=prompt)
    raw = response["response"]
    print("Raw response:", raw)

    try:
        parsed_obj = parser.parse(raw)
        return parsed_obj.instructions
    except Exception as e:
        print(f"LangChain parsing failed: {e}")
        return []
