import os
import cv2
import base64
import shutil
from ollama import chat, generate


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

def ask_for_questions(paths, model="llava"):
    image_base64_list = []
    for path in paths:
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        image_base64_list.append(image_base64)

    prompt = (
        "You will be asked to describe a set of images.\n"
        "Before doing that, what questions would help you better understand the context of what is happening?\n"
        "You will receive all the images now. Please list 3 to 5 relevant questions you would like to ask the user."
    )

    response = generate(
        model=model,
        prompt=prompt,
        images=image_base64_list
    )

    return response["response"].strip()


def re_describe_images_with_context(paths, user_context, model="llava", update_progress=None):
    descriptions = []
    total = len(paths)

    for i, path in enumerate(paths):
        try:
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = (
                f"You are describing an image with the following context provided by the user:\n"
                f"{user_context.strip()}\n\n"
                f"Please describe what is happening in this image in one clear sentence."
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


def describe_images(paths, update_progress=None, prompt="Describe the action you see in this image in one sentence."):
    descriptions = []
    total = len(paths)

    for i, path in enumerate(paths):
        try:
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            response = generate(
                model="llava",
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


def generate_instructions_ollama(descriptions, update_progress=None, model="mistral"):
    caption_list = [f"{i+1}. {d['description']}" for i, d in enumerate(descriptions)]
    joined_captions = "\n".join(caption_list)

    prompt = (
        "You are an assistant that writes clear work instructions for people with cognitive disabilities.\n"
        "Make sure every step is simple and written as a clear command.\n\n"
        "Here are the observations extracted from a video:\n"
        f"{joined_captions}\n\n"
        "Now generate a numbered list of simple instructions:"
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

    print("Extracting frames...")
    frame_paths = extract_frames(video_path, output_folder, fps)

    print("Letting the AI ask for clarification...")
    questions = ask_for_questions(frame_paths)
    print("\nThe AI has some questions for you:\n")
    print(questions)

    print("\nPlease type your answers to help the AI better understand the video.\n")
    user_answers = input("Your answers: ")

    print("\nDescribing images with additional context...")
    final_descriptions = re_describe_images_with_context(
        frame_paths,
        user_context=user_answers,
        update_progress=lambda x: print(f"Progress: {x*100:.2f}%")
    )

    print("Generating final work instructions...")
    instructions = generate_instructions_ollama(final_descriptions, lambda x: print(f"Progress: {x*100:.2f}%"))

    print("\nGenerated Work Instructions:\n")
    print(instructions)


