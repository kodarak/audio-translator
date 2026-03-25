# AudioTranslator

Настільний застосунок (Python / CustomTkinter) для відтворення аудіо, розпізнавання мови (Vosk, Whisper) і перекладу тексту кількома бекендами.

## Вимоги

- **ОС:** наразі орієнтовано на **Windows** (у залежностях є `pywin32`).
- **Python:** рекомендовано **3.12** (узгоджено з типовою збіркою PyInstaller у `main.spec`).
- **GPU:** опційно, для прискорення Whisper через CUDA.

## Швидкий старт

```powershell
git clone https://github.com/<ваш-акаунт>/<назва-репозиторію>.git
cd <назва-репозиторію>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Відредагуйте .env: KOREAN_MODEL_PATH, за потреби HF / DeepL
cd src
python main.py
```

### Змінні середовища (`.env`)

| Змінна | Опис |
|--------|------|
| `KOREAN_MODEL_PATH` | Шлях до каталогу моделі Vosk (корейська), **від кореня репозиторію**, напр. `models/vosk-model-small-ko-0.22`. |
| `DEEPL_API_KEY` | Опційно, якщо ввімкнете бекенд DeepL у коді. |
| `HUGGINGFACE_HUB_CACHE` | Опційно: каталог кешу Hub (за замовчуванням `~/.cache/huggingface/hub` на Windows через `HF_HOME`). |
| `HF_HOME` | Базовий каталог Hugging Face; підкаталог `hub` використовується для завантажень, якщо не задано `HUGGINGFACE_HUB_CACHE`. |

Моделі **Whisper** (`openai/whisper-large-v3`) та **MarianMT** завантажуються з Hugging Face при першому запуску, якщо їх ще немає в кеші.

## Збірка виконуваного файлу (PyInstaller)

1. Активуйте віртуальне середовище з усіма залежностями.
2. За потреби включіть локальний знімок кешу Hub у бандл (великий обсяг):

   ```powershell
   $env:HF_BUNDLE_CACHE = "C:\path\to\hub"
   pyinstaller main.spec
   ```

3. Якщо змінну не задавати, збірка все одно проходить; тоді на цільовій машіні потрібен Інтернет (або власний спосіб доставити кеш у `transformers_cache` поруч з програмою — за логікою `app_paths` / frozen).

Секрети **не вшивайте** в `datas`: тримайте `.env` лише локально (файл у `.gitignore`).

## Ліцензія

Див. [LICENSE](LICENSE). Залежності проєкту мають власні ліцензії. Окремі перекладачі та API (Google, DeepL тощо) регулюються їхніми умовами використання.
