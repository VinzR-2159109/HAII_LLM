# Video to Work Instructions Generator
## 🛠 Installation

### 1. Clone the repo
```bash
git clone https://github.com/your-username/thinker.git
cd thinker
```

### 2. Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Install ffmpeg (for frame extraction)

#### Ubuntu/Debian
```bash
sudo apt install ffmpeg
```

#### macOS (with Homebrew)
```bash
brew install ffmpeg
```

---

## 🤖 Run Ollama (for local LLMs)

Make sure you have [Ollama](https://ollama.com) installed and running:

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Run a local model (e.g. mistral)
ollama run mistral
```

---

## 🚀 Running the App

```bash
python app_frontend.py
```

---

## 📂 Project Structure

```
thinker/
├── app_frontend.py        # Tkinter GUI
├── backend.py             # Frame extraction, BLIP, and instruction generation
├── requirements.txt
├── README.md
└── frames/                # Generated frame images (temporary)
```

---

## 📦 Requirements

```
torch
transformers
Pillow
opencv-python
timm
ollama
```

These are listed in `requirements.txt`.

---

