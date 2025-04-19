from tkinter import *
from tkinter import filedialog
from PIL import Image, ImageTk
from backend import extract_frames, describe_images, generate_instructions_ollama

frames = []
descriptions = []
image_objs = []

def refresh_frame_view(container):
    for widget in container.winfo_children():
        widget.destroy()

    for i, path in enumerate(frames):
        img = Image.open(path).resize((160, 90))
        img_tk = ImageTk.PhotoImage(img)
        image_objs.append(img_tk)

        frame = Frame(container, bd=1, relief="solid", padx=4, pady=4)
        frame.grid(row=i // 2, column=i % 2, padx=10, pady=10)

        lbl = Label(frame, image=img_tk)
        lbl.image = img_tk
        lbl.pack()

        entry = Entry(frame, width=40, justify="center")
        entry.insert(0, descriptions[i])
        entry.pack(pady=4)
        entry.bind("<KeyRelease>", lambda e, idx=i: update_description(idx, e.widget.get()))

        btn = Button(frame, text="Delete", command=lambda idx=i: delete_frame(idx, container))
        btn.pack(pady=2)

def update_description(index, new_text):
    descriptions[index] = new_text

def delete_frame(index, container):
    del frames[index]
    del descriptions[index]
    refresh_frame_view(container)

def process_video(video_path, frame_container, loading_label):
    global frames, descriptions
    frame_area_container.pack_forget()
    loading_label.config(text="⏳ Beschrijvingen worden gegenereerd...")
    root.update_idletasks()

    frames = extract_frames(video_path)

    def update(p): pass
    descriptions = describe_images(frames, update)

    refresh_frame_view(frame_container)
    loading_label.config(text="✅ Klaar met beschrijven")
    frame_area_container.pack()

def generate_instructions(loading_label, output_label):
    frame_area_container.pack_forget()
    loading_label.config(text="⏳ Werkinstructies worden gegenereerd...")
    root.update_idletasks()

    def update(p): pass
    instructions = generate_instructions_ollama(descriptions, update)

    loading_label.config(text="✅ Klaar met instructies genereren")
    output_label.config(text=instructions)

# --- Tkinter Setup ---
root = Tk()
root.title("Thinker - Werkinstructie Generator")
root.geometry("800x800")

btn_frame = Frame(root)
btn_frame.pack(pady=10)

upload_btn = Button(btn_frame, text="Upload Video", width=25, command=lambda: upload_video())
upload_btn.grid(row=0, column=0, padx=10)

generate_btn = Button(btn_frame, text="Genereer Werkinstructies", width=25, command=lambda: generate_instructions(loading_label, output_label))
generate_btn.grid(row=0, column=1, padx=10)

# Loading label
loading_label = Label(root, text="", font=("Arial", 11), fg="blue")
loading_label.pack(pady=10)

# Frame viewer area (hidden during loading)
frame_area_container = Frame(root)
frame_area = Canvas(frame_area_container, width=750, height=400)
scrollbar = Scrollbar(frame_area_container, orient="vertical", command=frame_area.yview)
scroll_frame = Frame(frame_area)

scroll_frame.bind("<Configure>", lambda e: frame_area.configure(scrollregion=frame_area.bbox("all")))
frame_area.create_window((0, 0), window=scroll_frame, anchor="nw")
frame_area.configure(yscrollcommand=scrollbar.set)

frame_area.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

frame_area_container.pack()

# Output label (final instructions)
output_label = Label(root, text="", wraplength=700, justify="center", font=("Arial", 11))
output_label.pack(pady=10)

def upload_video():
    path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mov *.avi")])
    if path:
        process_video(path, scroll_frame, loading_label)

root.mainloop()
