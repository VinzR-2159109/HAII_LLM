import os
import json
import shutil

from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse

from .forms import UploadForm
from .utils import handle_video, describe_images, generate_instructions, refine_instructions, add_instruction

def upload_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            frames_dir = os.path.join(settings.MEDIA_ROOT, "frames")
            if os.path.exists(frames_dir):
                shutil.rmtree(frames_dir)
            os.makedirs(frames_dir, exist_ok=True)

            video = request.FILES["video"]
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            video_path = os.path.join(settings.MEDIA_ROOT, video.name)

            with open(video_path, 'wb+') as dest:
                for chunk in video.chunks():
                    dest.write(chunk)

            request.session["video_path"] = video_path
            request.session["context"] = request.POST.get("context", "").strip()

            return redirect("describe")
    else:
        form = UploadForm()

    return render(request, "upload.html", {"form": form})

def describe_view(request):
    video_path = request.session.get("video_path")
    if not video_path:
        return redirect("upload")

    frame_data = handle_video(video_path)

    context = request.session.get("context")
    print("Context loaded:", context)

    descriptions = describe_images(frame_data, context)

    descriptions_path = os.path.join(settings.MEDIA_ROOT, "descriptions.json")
    with open(descriptions_path, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, indent=2)

    return render(request, "describe.html", {
        "descriptions": descriptions,
        "media_url": "/media/"
    })

def generate_view(request):
    descriptions = []
    total = int(request.POST.get("total", 0))

    video_path = request.session.get("video_path")
    video_filename = os.path.basename(video_path) if video_path else ""

    request.session["video_path"]

    for i in range(total):
        if request.POST.get(f"deleted_{i}") == "true":
            continue

        path = request.POST.get(f"path_{i}")
        description = request.POST.get(f"description_{i}")
        descriptions.append({"path": path, "description": description})

    descriptions_path = os.path.join("media", "descriptions.json")
    with open(descriptions_path, "w", encoding="utf-8") as f:
        json.dump(descriptions, f, indent=2)

    instructions = generate_instructions(descriptions)

    return render(request, "generate.html", {
        "instructions": instructions,
        "video_filename": video_filename
    })

def add_instruction_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        instructions = data.get("instructions", [])

        current_texts = [instr["text"].strip() for instr in instructions]

        insert_index = data.get("insert_index", len(current_texts))
        insert_index = max(0, min(insert_index, len(current_texts))) 

        descriptions_path = os.path.join(settings.MEDIA_ROOT, "descriptions.json")
        with open(descriptions_path, "r", encoding="utf-8") as f:
            descriptions_data = json.load(f)

        descriptions = [item["description"] for item in descriptions_data]

        new_instruction = add_instruction(current_texts, insert_index, descriptions)

        return JsonResponse({
            "new_instruction": new_instruction
        })

    except Exception as e:
        print(f"Error in add_instruction_view: {e}")
        return JsonResponse({"error": str(e)}, status=500)



def refine_instructions_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        data = json.loads(request.body)
        refine_context = data.get("refine_context", "")
        instructions = data.get("instructions", [])

        unlocked_texts = []
        unlocked_mapping = []

        for instr in instructions:
            if not instr["locked"]:
                text = instr["text"].strip()
                if text != '':
                    unlocked_mapping.append(True)
                    unlocked_texts.append(text)
                else:
                    unlocked_mapping.append(False)

        print(f"refine context: {refine_context}")
        refined_texts = refine_instructions(unlocked_texts, refine_context)

        result = []
        unlocked_index = 0

        for instr in instructions:
            if instr["locked"]:
                result.append(instr["text"])
            else:
                if unlocked_mapping[unlocked_index]:
                    result.append(refined_texts[unlocked_index])
                    unlocked_index += 1
                else:
                    result.append('')

        return JsonResponse({"refined_instructions": result})

    except Exception as e:
        print(f"Error in refine_instructions_view: {e}")
        return JsonResponse({"error": str(e)}, status=500)

def save_instructions_view(request):
    if request.method != "POST":
        return redirect("generate")

    total = int(request.POST.get("total", 0))
    final = []

    for i in range(total):
        text = request.POST.get(f"text_{i}", "").strip()
        final.append({
            "text": text
        })

    with open("media/descriptions.json", "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2)
    
    with open("media/final_instructions.md", "w", encoding="utf-8") as f:
            f.write("# Final Instructions\n\n")
            for i, item in enumerate(final, start=1):
                f.write(f"{i}. {item['text']}\n")

    return render(request, "done.html", {"instructions": final})