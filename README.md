# 🎥 Center Stage Camera

**Apple-quality Center Stage for Windows** - AI-powered face tracking that keeps you centered in video calls.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/bajishaikh18/CenterStage?style=social)](https://github.com/bajishaikh18/CenterStage/stargazers)
[![GitHub last commit](https://img.shields.io/github/last-commit/bajishaikh18/CenterStage)](https://github.com/bajishaikh18/CenterStage/commits)
[![GitHub code size](https://img.shields.io/github/languages/code-size/bajishaikh18/CenterStage)](https://github.com/bajishaikh18/CenterStage)

<p align="center">
  <img src="https://img.shields.io/badge/Works%20With-Teams-6264A7?logo=microsoft-teams" alt="Microsoft Teams"/>
  <img src="https://img.shields.io/badge/Works%20With-Zoom-2D8CFF?logo=zoom" alt="Zoom"/>
  <img src="https://img.shields.io/badge/Works%20With-Google%20Meet-00897B?logo=google-meet" alt="Google Meet"/>
</p>

<!-- 
## 🎬 Demo
![Center Stage Demo](demo.gif)
Add a demo GIF here to show the tracking in action!
-->

## ✨ Features

- 🎯 **Automatic Face Tracking** - Keeps your face centered, even as you move
- 🍎 **Apple-Quality Motion** - Buttery smooth transitions with easing
- 📹 **Virtual Camera Output** - Works with Teams, Zoom, Meet, and more
- 🔥 **Three Versions** - Choose based on your needs

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** - [Download](https://www.python.org/downloads/)
2. **UnityCapture** (Virtual Camera Driver)
   - [Download from GitHub](https://github.com/schellingb/UnityCapture/releases)
   - Extract and run `Install.bat` as Administrator
   - Restart your computer

### Installation

```bash
git clone https://github.com/yourusername/CenterStage.git
cd CenterStage
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
pip install -r requirements.txt
```

---

## 📦 Three Versions

| Version | Resolution | CPU Usage | Best For |
|---------|------------|-----------|----------|
| **ultralight.py** | 720p | 🟢 Minimal | Long calls, older PCs |
| **lite.py** | 1080p | 🟡 Medium | Best quality |
| **main.py** | Configurable | 🟠 Higher | Full UI & controls |

---

### 🪶 Ultra Light (Recommended)

Minimal CPU, no heating, smooth tracking.

```bash
source venv/Scripts/activate && python ultralight.py
```

---

### ⚡ Lite Version

1080p quality, Apple-style smooth tracking.

```bash
source venv/Scripts/activate && python lite.py
```

---

### 🖥️ Full Version

Complete GUI with preview, settings, and controls.

```bash
source venv/Scripts/activate && python main.py
```

---

## 🧪 Test Preview

Test locally before your call (no virtual camera):

```bash
python test_preview.py
```

Press **Q** to quit.

---

## ⚙️ Using with Video Apps

1. Run your preferred version (ultralight/lite)
2. In **Teams/Zoom/Meet**: Go to Settings → Camera
3. Select **"Unity Video Capture"**
4. Done! 🎉

---

## 📁 Project Structure

```
CenterStage/
├── ultralight.py     # 🪶 Minimal CPU (recommended)
├── lite.py           # ⚡ 1080p quality
├── test_preview.py   # 🧪 Local test
├── main.py           # 🖥️ Full UI version
├── requirements.txt
├── src/              # Full version source
└── tests/            # Unit tests
```

---

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - feel free to use in your projects!

This project includes [UnityCapture](https://github.com/schellingb/UnityCapture) which is released under the Unlicense (public domain).

---

## 🙏 Acknowledgments

- **OpenCV** - Face detection
- **pyvirtualcam** - Virtual camera support
- **UnityCapture** - Windows virtual camera driver (Unlicense)
- **PySide6** - GUI framework (Full version)

---

**Made with ❤️ for better video calls**
