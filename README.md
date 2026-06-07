# NeuroSort 

NeuroSort is a real-time automated file organizer bot that watches directories and intelligently sorts files using customizable rules.

It monitors folders continuously and organizes files automatically into categories such as Documents, Images, Videos, Archives, Code, Audio, and more.

---

##  Features

- Real-time folder monitoring using `watchdog`
- Rule-based file organization using YAML
- Dry-run mode (preview moves safely)
- Undo support for restoring previous moves
- Collision-safe renaming
- Time-based organization (Year/Month folders)
- Rich terminal UI with colored output
- Graceful shutdown with statistics
- Modular architecture

---

## 📁 Project Structure

```text
NeuroSort/
├── main.py
├── rules.yaml
├── .gitignore
├── src/
│   ├── watcher.py
│   ├── config.py
│   ├── display.py
│   ├── history.py
│   └── logger.py
```

## ⚙️ Installation

Clone repository:

```bash
git clone https://github.com/VaishnaviPatil-gif/NeuroSort.git
```

Move into project:

```bash
cd NeuroSort
```

Create virtual environment:

```bash
python -m venv venv
```

Activate:

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Usage

Watch Downloads:

```bash
python main.py --watch ~/Downloads
```

Dry run:

```bash
python main.py --watch ~/Downloads --dry-run
```

Undo:

```bash
python main.py --undo
```

Custom config:

```bash
python main.py --watch ~/Desktop --config rules.yaml
```

---

##  Example Rules

```yaml
rules:
  - folder: Documents
    extensions: [pdf, docx]

  - folder: Images
    extensions: [jpg, png]

  - folder: Code
    extensions: [py, cpp]
```

---

##  Future Improvements

- AI-powered smart categorization
- Web dashboard
- Advanced filtering rules
- Analytics and usage reports
- Plugin system

---



