import torch
from transformers import pipeline, AutoProcessor, AutoModelForSpeechSeq2Seq
import librosa
from tqdm import tqdm
import time
import warnings
import langid
from langdetect import detect

warnings.filterwarnings("ignore", category=FutureWarning)

def get_language_name(detected_language):
    language_mapping = {
        'af': 'Африкаанс',
        'afrikaans': 'Африкаанс',
        'am': 'Амхарська',
        'amharic': 'Амхарська',
        'ar': 'Арабська',
        'arabic': 'Арабська',
        'az': 'Азербайджанська',
        'azerbaijani': 'Азербайджанська',
        'be': 'Білоруська',
        'belarusian': 'Білоруська',
        'bg': 'Болгарська',
        'bulgarian': 'Болгарська',
        'bn': 'Бенгальська',
        'bengali': 'Бенгальська',
        'bs': 'Боснійська',
        'bosnian': 'Боснійська',
        'ca': 'Каталонська',
        'catalan': 'Каталонська',
        'ceb': 'Себуанська',
        'cebuano': 'Себуанська',
        'co': 'Корсиканська',
        'corsican': 'Корсиканська',
        'cs': 'Чеська',
        'czech': 'Чеська',
        'cy': 'Валлійська',
        'welsh': 'Валлійська',
        'da': 'Данська',
        'danish': 'Данська',
        'de': 'Німецька',
        'german': 'Німецька',
        'el': 'Грецька',
        'greek': 'Грецька',
        'en': 'Англійська',
        'english': 'Англійська',
        'eo': 'Есперанто',
        'esperanto': 'Есперанто',
        'es': 'Іспанська',
        'spanish': 'Іспанська',
        'et': 'Естонська',
        'estonian': 'Естонська',
        'eu': 'Баскська',
        'basque': 'Баскська',
        'fa': 'Перська',
        'persian': 'Перська',
        'fi': 'Фінська',
        'finnish': 'Фінська',
        'fr': 'Французька',
        'french': 'Французька',
        'fy': 'Фризька',
        'frisian': 'Фризька',
        'ga': 'Ірландська',
        'irish': 'Ірландська',
        'gd': 'Шотландська гельська',
        'scots gaelic': 'Шотландська гельська',
        'gl': 'Галісійська',
        'galician': 'Галісійська',
        'gu': 'Гуджараті',
        'gujarati': 'Гуджараті',
        'ha': 'Хауса',
        'hausa': 'Хауса',
        'haw': 'Гавайська',
        'hawaiian': 'Гавайська',
        'he': 'Іврит',
        'hebrew': 'Іврит',
        'hi': 'Гінді',
        'hindi': 'Гінді',
        'hmn': 'Хмонг',
        'hmong': 'Хмонг',
        'hr': 'Хорватська',
        'croatian': 'Хорватська',
        'ht': 'Гаїтянська креольська',
        'haitian creole': 'Гаїтянська креольська',
        'hu': 'Угорська',
        'hungarian': 'Угорська',
        'hy': 'Вірменська',
        'armenian': 'Вірменська',
        'id': 'Індонезійська',
        'indonesian': 'Індонезійська',
        'ig': 'Ігбо',
        'igbo': 'Ігбо',
        'is': 'Ісландська',
        'icelandic': 'Ісландська',
        'it': 'Італійська',
        'italian': 'Італійська',
        'ja': 'Японська',
        'japanese': 'Японська',
        'jw': 'Яванська',
        'javanese': 'Яванська',
        'ka': 'Грузинська',
        'georgian': 'Грузинська',
        'kk': 'Казахська',
        'kazakh': 'Казахська',
        'km': 'Кхмерська',
        'khmer': 'Кхмерська',
        'kn': 'Каннада',
        'kannada': 'Каннада',
        'ko': 'Корейська',
        'korean': 'Корейська',
        'ku': 'Курдська',
        'kurdish': 'Курдська',
        'ky': 'Киргизька',
        'kyrgyz': 'Киргизька',
        'la': 'Латинська',
        'latin': 'Латинська',
        'lb': 'Люксембурзька',
        'luxembourgish': 'Люксембурзька',
        'lo': 'Лаоська',
        'lao': 'Лаоська',
        'lt': 'Литовська',
        'lithuanian': 'Литовська',
        'lv': 'Латвійська',
        'latvian': 'Латвійська',
        'mg': 'Малагасійська',
        'malagasy': 'Малагасійська',
        'mi': 'Маорі',
        'maori': 'Маорі',
        'mk': 'Македонська',
        'macedonian': 'Македонська',
        'ml': 'Малаялам',
        'malayalam': 'Малаялам',
        'mn': 'Монгольська',
        'mongolian': 'Монгольська',
        'mr': 'Маратхі',
        'marathi': 'Маратхі',
        'ms': 'Малайська',
        'malay': 'Малайська',
        'mt': 'Мальтійська',
        'maltese': 'Мальтійська',
        'my': 'Бірманська',
        'myanmar (burmese)': 'Бірманська',
        'ne': 'Непальська',
        'nepali': 'Непальська',
        'nl': 'Нідерландська',
        'dutch': 'Нідерландська',
        'no': 'Норвезька',
        'norwegian': 'Норвезька',
        'ny': 'Чичева',
        'chichewa': 'Чичева',
        'pa': 'Панджабі',
        'punjabi': 'Панджабі',
        'pl': 'Польська',
        'polish': 'Польська',
        'ps': 'Пушту',
        'pashto': 'Пушту',
        'pt': 'Португальська',
        'portuguese': 'Португальська',
        'ro': 'Румунська',
        'romanian': 'Румунська',
        'ru': 'Російська',
        'russian': 'Російська',
        'sd': 'Сіндхі',
        'sindhi': 'Сіндхі',
        'si': 'Сингальська',
        'sinhala': 'Сингальська',
        'sk': 'Словацька',
        'slovak': 'Словацька',
        'sl': 'Словенська',
        'slovenian': 'Словенська',
        'sm': 'Самоанська',
        'samoan': 'Самоанська',
        'sn': 'Шона',
        'shona': 'Шона',
        'so': 'Сомалійська',
        'somali': 'Сомалійська',
        'sq': 'Албанська',
        'albanian': 'Албанська',
        'sr': 'Сербська',
        'serbian': 'Сербська',
        'st': 'Сесото',
        'sesotho': 'Сесото',
        'su': 'Сунданська',
        'sundanese': 'Сунданська',
        'sv': 'Шведська',
        'swedish': 'Шведська',
        'sw': 'Свахілі',
        'swahili': 'Свахілі',
        'ta': 'Тамільська',
        'tamil': 'Тамільська',
        'te': 'Телугу',
        'telugu': 'Телугу',
        'tg': 'Таджицька',
        'tajik': 'Таджицька',
        'th': 'Тайська',
        'thai': 'Тайська',
        'tl': 'Тагальська',
        'filipino': 'Тагальська',
        'tr': 'Турецька',
        'turkish': 'Турецька',
        'uk': 'Українська',
        'ukrainian': 'Українська',
        'ur': 'Урду',
        'urdu': 'Урду',
        'uz': 'Узбецька',
        'uzbek': 'Узбецька',
        'vi': 'Вʼєтнамська',
        'vietnamese': 'Вʼєтнамська',
        'xh': 'Кхоса',
        'xhosa': 'Кхоса',
        'yi': 'Їдиш',
        'yiddish': 'Їдиш',
        'yo': 'Йоруба',
        'yoruba': 'Йоруба',
        'zh': 'Китайська',
        'zh-cn': 'Китайська (спрощена)',
        'zh-tw': 'Китайська (традиційна)',
        'chinese': 'Китайська',
        'zu': 'Зулу',
        'zulu': 'Зулу',
        'unknown': 'Невідома мова',
    }
    return language_mapping.get(detected_language.lower(), 'Невідома мова')


def test_whisper(audio_file_paths):
    import transformers
    print(f"Transformers version: {transformers.__version__}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Використовується пристрій: {device}")

    model_name = "openai/whisper-large"

    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForSpeechSeq2Seq.from_pretrained(model_name)

    tokenizer = processor.tokenizer
    feature_extractor = processor.feature_extractor

    if tokenizer.pad_token_id is None or tokenizer.pad_token_id == tokenizer.eos_token_id:
        tokenizer.pad_token_id = tokenizer.eos_token_id + 1

    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=tokenizer,
        feature_extractor=feature_extractor,
        device=device,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        return_language=True,
    )

    for audio_file_path in audio_file_paths:
        print(f"\nТестування Whisper Large для файлу: {audio_file_path}")

        try:
            print("Завантаження аудіо...")
            audio_input, sampling_rate = librosa.load(audio_file_path, sr=16000)
            audio_duration = len(audio_input) / sampling_rate
            print(f"Аудіо завантажено. Тривалість: {audio_duration:.2f} секунд")

            chunk_duration = 30
            chunk_samples = int(chunk_duration * sampling_rate)
            chunks = [audio_input[i:i + chunk_samples] for i in range(0, len(audio_input), chunk_samples)]

            print("Виконання транскрипції та визначення мови...")
            full_transcription = []
            whisper_language = None
            langid_language = None
            langdetect_language = None

            for i, chunk in enumerate(tqdm(chunks, desc="Обробка частин аудіо")):
                chunk_start_time = time.time()

                result = pipe(
                    chunk,
                    return_timestamps=True,
                    generate_kwargs={
                        "task": "transcribe",
                        "language": None,
                    },
                )

                text = result.get('text', '')
                full_transcription.append(text)

                if i == 0:
                    if 'chunks' in result and len(result['chunks']) > 0:
                        chunk_language_code = result['chunks'][0].get('language', None)
                        whisper_language = get_language_name(chunk_language_code) if chunk_language_code else 'Невідома мова'
                    else:
                        whisper_language = 'Невідома мова'

                    langid.set_languages(None)
                    langid_predictions = langid.rank(text)
                    if langid_predictions:
                        langid_language_code, langid_probability = langid_predictions[0]
                        langid_language = get_language_name(langid_language_code)
                        print(f"\nВиявлена мова (langid): {langid_language} (ймовірність: {langid_probability:.2f})")
                    else:
                        langid_language = 'Невідома мова'
                        langid_probability = 0
                        print(f"\nВиявлена мова (langid): {langid_language}")

                    try:
                        langdetect_language_code = detect(text)
                        langdetect_language = get_language_name(langdetect_language_code)
                    except Exception as e:
                        langdetect_language = 'Невідома мова'

                    print(f"Виявлена мова (langdetect): {langdetect_language}")
                    print(f"Виявлена мова (Whisper): {whisper_language}")

                chunk_end_time = time.time()
                chunk_process_time = chunk_end_time - chunk_start_time

                print(f"\nЧастина {i + 1}/{len(chunks)} оброблена за {chunk_process_time:.2f} секунд")
                print(f"Довжина тексту транскрипції: {len(text)}")
                print(f"Частковий текст: {text[:100]}...")

            final_transcription = ' '.join(full_transcription)

            print("\nФінальні результати:")
            print(f"Файл: {audio_file_path}")
            print(f"Виявлена мова (Whisper): {whisper_language}")
            print(f"Виявлена мова (langid): {langid_language}")
            print(f"Виявлена мова (langdetect): {langdetect_language}")
            print(f"Загальна транскрипція: {final_transcription}")

        except Exception as e:
            print(f"Виникла помилка при обробці аудіо: {str(e)}")

if __name__ == "__main__":
    audio_file_paths = [
        "C:/python_projects/Pr0j3ct/audio_files/test_1.wav",
    ]
    test_whisper(audio_file_paths)
