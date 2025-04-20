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


def ask_for_questions(paths, user_context, model="llava"):
    image_base64_list = []
    for path in paths:
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        image_base64_list.append(image_base64)

    prompt = (
        f"The user has provided the following context about the video:\n"
        f"{user_context.strip()}\n\n"
        "You will now be shown several images extracted from this video.\n"
        "Before generating descriptions, please list 1 or 2 clarifying questions you would like to ask the user "
        "to better understand the actions taking place in the video."
    )

    response = generate(
        model=model,
        prompt=prompt,
        images=image_base64_list
    )

    return response["response"].strip()


def describe_images(paths, full_context, model="llava", update_progress=None):
    descriptions = []
    total = len(paths)

    for i, path in enumerate(paths):
        try:
            with open(path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = (
                f"The user has provided this context:\n{full_context.strip()}\n\n"
                f"Based on that, describe what is happening in this image in one clear sentence."
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


def generate_instructions(descriptions, update_progress=None, model="mistral"):
    caption_list = [f"{i+1}. {d['description']}" for i, d in enumerate(descriptions)]
    joined_captions = "\n".join(caption_list)

    prompt = (
        "You are an assistant that writes clear work instructions for people with cognitive disabilities.\n"
        "Make sure every step is simple and written as a direct command.\n\n"
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

    print("=== STEP 0: Provide Context ===")
    user_context = input("Briefly describe what's happening in the video (e.g. 'person assembling a chair'): ")

    print("\n=== STEP 1: Extracting Frames ===")
    frame_paths = extract_frames(video_path, output_folder, fps)

    print("\n=== STEP 2: AI Will Ask Clarifying Questions ===")
    questions = ask_for_questions(frame_paths, user_context)
    print("\nThe AI has the following questions for you:\n")
    print(questions)

    print("\n=== STEP 3: Your Answers ===")
    user_answers = input("Please answer the AI's questions in a single paragraph:\n")

    full_context = f"{user_context.strip()}\n\nUser's answers to clarifying questions:\n{user_answers.strip()}"

    print("\n=== STEP 4: Describing Images With Full Context ===")
    descriptions = describe_images(
        frame_paths,
        full_context,
        update_progress=lambda x: print(f"Progress: {x*100:.2f}%")
    )

    print("\n=== STEP 5: Generating Final Instructions ===")
    instructions = generate_instructions(descriptions, lambda x: print(f"Progress: {x*100:.2f}%"))

    print("\n=== Final Work Instructions ===\n")
    print(instructions)
