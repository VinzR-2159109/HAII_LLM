import os
import json
import shutil

from django.shortcuts import render, redirect
from django.conf import settings

from .forms import UploadForm
from .utils import handle_video, describe_images, generate_instructions

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

    context = request.session.get("context", "")
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
        "instructions": instructions
    })

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
