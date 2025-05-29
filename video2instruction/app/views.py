import os
import json

from django.shortcuts import render, redirect
from django.conf import settings

from .forms import UploadForm
from .utils import handle_video, describe_images, generate_instructions

def upload_view(request):
    if request.method == "POST":
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            video = request.FILES["video"]

            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            video_path = os.path.join(settings.MEDIA_ROOT, video.name)

            with open(video_path, 'wb+') as dest:
                for chunk in video.chunks():
                    dest.write(chunk)

            request.session["video_path"] = video_path
            return redirect("describe")
    else:
        form = UploadForm()

    return render(request, "upload.html", {"form": form})


def describe_view(request):
    video_path = request.session.get("video_path")
    if not video_path:
        return redirect("upload")

    frame_paths = request.session.get("frames")
    if not frame_paths:
        frame_paths = handle_video(video_path)
        request.session["frames"] = frame_paths

    context = request.POST.get("context", "").strip()
    request.session["context"] = context

    descriptions = describe_images(frame_paths, context)
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

