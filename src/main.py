import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
import os
import sys
import platform
from pathlib import Path

from ui import AudioTranslatorApp
from audio import AudioController
from recognition import SpeechRecognition
from translation import Translation
from whisper_recognition import WhisperRecognizer


def setup_logging():
    """Налаштування логування з підтримкою ротації файлів і виведення в консоль."""
    # Визначаємо шлях до папки logs
    if getattr(sys, 'frozen', False):
        # Якщо програма запущена як .exe, logs буде поруч з .exe
        log_dir = os.path.join(os.path.dirname(sys.executable), 'logs')
    else:
        # Якщо запущена як скрипт, logs буде в папці проекту
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'audio_translator.log')

    logger = logging.getLogger('AudioTranslator')
    logger.setLevel(logging.INFO)

    file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def check_required_files(logger, base_path):
    """Перевірка наявності критичних файлів для роботи програми."""
    required_files = [
        os.path.join(base_path, 'models', 'vosk_model_small_ko'),  # Приклад шляху до моделі
        os.path.join(base_path, 'logs', 'audio_translator.log'),  # Перевірка доступу до логів
        # Додайте інші файли, якщо потрібно (наприклад, іконки)
    ]
    for file_path in required_files:
        if not os.path.exists(file_path):
            logger.error(f"Required file not found: {file_path}")
        else:
            logger.info(f"Found required file: {file_path}")


def main():
    """Основна функція запуску програми Audio Translator."""
    try:
        load_dotenv()
    except Exception as e:
        print(f"Попередження: Не вдалося завантажити файл .env. {str(e)}")

    logger = setup_logging()
    logger.info("Запуск програми Audio Translator")

    # Визначаємо базовий шлях для ресурсів
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Базовий шлях до ресурсів: {base_path}")

    # Додаємо інформацію про середовище для дебагінгу
    logger.info(f"Версія Python: {sys.version}")
    logger.info(f"Операційна система: {platform.system()} {platform.release()}")
    logger.info(f"Шлях до виконуваного файлу: {sys.executable}")
    logger.info(f"Поточна робоча директорія: {os.getcwd()}")

    # Перевіряємо наявність критичних файлів
    check_required_files(logger, base_path)

    try:
        print("Ініціалізація AudioController...")
        audio_controller = AudioController(logger)
    except Exception as e:
        logger.exception(f"Фатальна помилка при ініціалізації AudioController: {str(e)}")
        print(f"Фатальна помилка: {str(e)}")
        raise

    try:
        # Піднімаємося на один рівень вище від src до кореня проєкту
        project_root = Path(base_path).parent if not getattr(sys, 'frozen', False) else Path(base_path)
        korean_model_path = os.getenv('KOREAN_MODEL_PATH')

        if not korean_model_path:
            raise ValueError("KOREAN_MODEL_PATH не вказано у файлі .env")

        absolute_korean_model_path = project_root / korean_model_path
        logger.info(f"Пошук моделі Vosk для корейської мови за шляхом: {absolute_korean_model_path}")

        if not os.path.exists(absolute_korean_model_path):
            logger.error(f"Модель не знайдено за шляхом: {absolute_korean_model_path}")
            raise FileNotFoundError(
                f"Модель Vosk для корейської мови не знайдено за шляхом: {absolute_korean_model_path}")
    except Exception as e:
        logger.exception(f"Фатальна помилка з шляхом до моделі: {str(e)}")
        print(f"Фатальна помилка: {str(e)}")
        raise

    try:
        print("Ініціалізація SpeechRecognition...")
        speech_recognition = SpeechRecognition(str(absolute_korean_model_path))
    except Exception as e:
        logger.exception(f"Фатальна помилка при ініціалізації SpeechRecognition: {str(e)}")
        print(f"Фатальна помилка: {str(e)}")
        raise

    try:
        print("Ініціалізація WhisperRecognizer...")
        whisper_recognizer = WhisperRecognizer()
    except Exception as e:
        logger.exception(f"Фатальна помилка при ініціалізації WhisperRecognizer: {str(e)}")
        print(f"Фатальна помилка: {str(e)}")
        raise

    try:
        print("Ініціалізація Translation...")
        translation = Translation(logger)
    except Exception as e:
        logger.exception(f"Фатальна помилка при ініціалізації Translation: {str(e)}")
        print(f"Фатальна помилка: {str(e)}")
        raise

    try:
        print("Ініціалізація AudioTranslatorApp...")
        app = AudioTranslatorApp(audio_controller, speech_recognition, whisper_recognizer, translation, logger)
        logger.info("Програма ініціалізована, запуск основного циклу")
        app.mainloop()
    except Exception as e:
        logger.exception(f"Фатальна помилка при ініціалізації GUI або в основному циклі: {str(e)}")
        print(f"Фатальна помилка: {str(e)}")
        raise
    finally:
        logger.info("Завершення роботи програми")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


if __name__ == "__main__":
    main()