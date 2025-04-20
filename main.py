import os
import cv2
import base64
import shutil
from ollama import chat, generate

# 🎞️ STEP 1: Frame Extraction
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

# 🧠 STEP 2: AI Questions Based on User Context
def ask_for_questions(paths, user_context, model="llava"):
    image_base64_list = []
    for path in paths:
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        image_base64_list.append(image_base64)

    prompt = (
        f"The user has provided this context:\n{user_context.strip()}\n\n"
        "You will now be shown several images from the video.\n"
        "Before describing them, list 2 clarifying questions you'd ask the user "
        "to better understand the task shown."
        "But only if you really need the answer to understand the images!"
    )

    response = generate(
        model=model,
        prompt=prompt,
        images=image_base64_list
    )

    return response["response"].strip()

# 🖼️ STEP 3: Describe Each Image (with memory of previous steps)
def re_describe_images_with_context(paths, full_context, model="llava", update_progress=None):
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
                f"Context provided by the user:\n{full_context.strip()}\n\n"
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

# 📝 STEP 4: Save and Edit Descriptions
def save_descriptions_to_file(descriptions, path="descriptions.txt"):
    with open(path, "w", encoding="utf-8") as f:
        for i, d in enumerate(descriptions):
            f.write(f"{i+1}. {d['description']}\n")

def load_descriptions_from_file(path="descriptions.txt"):
    descriptions = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                if "." in line:
                    idx, text = line.strip().split(".", 1)
                    descriptions.append({"index": int(idx), "description": text.strip()})
    return descriptions

# 🧠 STEP 5: Iterative Instruction Generation with Images + Feedback
def refine_instructions_loop(descriptions, model="llava"):
    feedback = None

    while True:
        prompt = (
            "You are an assistant that writes clear, step-by-step work instructions for people with cognitive disabilities.\n"
            "Each instruction is based on a visual frame and its description.\n"
            "Use the image and its caption to create one numbered instruction per frame.\n"
            "Make each instruction short, direct, and actionable.\n"
        )

        if feedback:
            prompt += f"\nUser feedback: {feedback.strip()}\n"

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

        print("\n=== 🛠️ GENERATED WORK INSTRUCTIONS ===\n")
        print(instructions)

        choice = input("\nAre these instructions acceptable? (y = yes / r = refine with feedback): ").strip().lower()

        if choice == "y":
            return instructions
        elif choice == "r":
            feedback = input("What should be improved?\n")
        else:
            print("Please type 'y' or 'r'.")

# 💾 STEP 6: Save Final Instructions
def save_instructions_to_file(instructions, path="instructions.txt"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(instructions)

# 🧼 Optional Cleanup
def cleanup_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)

# 🚀 MAIN WORKFLOW
if __name__ == "__main__":
    video_path = "test_video.mp4"
    output_folder = "frames"
    fps = 1

    print("===STEP 0: Describe Your Video ===")
    user_context = input("Briefly describe what's happening in the video (e.g. 'person assembling a shelf'): ")

    print("\n===STEP 1: Extracting Video Frames ===")
    frame_paths = extract_frames(video_path, output_folder, fps)

    print("\n===STEP 2: AI is Generating Questions ===")
    questions = ask_for_questions(frame_paths, user_context)
    print("\nThe AI would like you to answer the following questions:\n")
    print(questions)

    print("\n===STEP 3: Your Answers ===")
    user_answers = input("Please answer the AI's questions in one paragraph:\n")
    full_context = f"{user_context.strip()}\n\nUser's answers to clarifying questions:\n{user_answers.strip()}"

    print("\n=== STEP 4: Describing Images With Context ===")
    descriptions = re_describe_images_with_context(
        frame_paths,
        full_context,
        update_progress=lambda x: print(f"Progress: {x*100:.2f}%")
    )

    print("\n=== STEP 5: Review and Edit Descriptions ===")
    save_descriptions_to_file(descriptions, "descriptions.txt")
    print("Descriptions saved to 'descriptions.txt'.")
    input("Edit the file if needed, then press ENTER to continue...")
    user_descriptions = load_descriptions_from_file("descriptions.txt")

    # Merge paths back into loaded descriptions
    for i, d in enumerate(user_descriptions):
        d["path"] = frame_paths[i]

    print("\n=== STEP 6: Iterative Instruction Refinement ===")
    final_instructions = refine_instructions_loop(user_descriptions)

    print("\n=== STEP 7: Saving Final Instructions ===")
    save_instructions_to_file(final_instructions, "instructions.txt")
    print("Instructions saved to 'instructions.txt'.")

    # Optional: cleanup_folder(output_folder)
