# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller: шляхи відносно кореня репозиторію. Для великого офлайн-бандла задайте HF_BUNDLE_CACHE."""
import os
import importlib.util

block_cipher = None

ROOT = os.path.dirname(os.path.abspath(SPEC))


def _vosk_pkg_dir():
    spec = importlib.util.find_spec("vosk")
    if not spec or not spec.origin:
        raise RuntimeError("Пакет vosk не знайдено. Активуйте venv і виконайте: pip install vosk")
    return os.path.dirname(os.path.abspath(spec.origin))


VOSK_DIR = _vosk_pkg_dir()

datas = [
    ("icons", "icons"),
    (VOSK_DIR, "vosk"),
]

for folder in ("models", "logs", "Audio"):
    path = os.path.join(ROOT, folder)
    if os.path.isdir(path):
        datas.append((path, folder))

hf_bundle = os.environ.get("HF_BUNDLE_CACHE", "").strip()
if hf_bundle and os.path.isdir(hf_bundle):
    datas.append((hf_bundle, "transformers_cache"))

a = Analysis(
    [os.path.join(ROOT, "src", "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "vosk",
        "transformers",
        "torch",
        "customtkinter",
        "tkinter",
        "pydub",
        "numpy",
        "librosa",
        "langdetect",
        "langid",
        "deep-translator",
        "googletrans",
        "pygame",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["pandas", "pytz"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

for dll_name in (
    "libvosk.dll",
    "libgcc_s_seh-1.dll",
    "libstdc++-6.dll",
    "libwinpthread-1.dll",
):
    dll_path = os.path.join(VOSK_DIR, dll_name)
    if os.path.isfile(dll_path):
        a.binaries.append((dll_name, dll_path, "BINARY"))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AudioTranslator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon=os.path.join(ROOT, "icons", "img.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AudioTranslator",
)
