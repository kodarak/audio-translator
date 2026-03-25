import json
import logging
import sys
import os

import numpy as np
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer, SetLogLevel

from language_codes import get_language_name, get_language_family
from whisper_recognition import WhisperRecognizer


class SpeechRecognition:
    def __init__(self, korean_model_path):
        self.word_confidences = None
        self.logger = logging.getLogger("AudioTranslator")
        SetLogLevel(-1)

        # Визначаємо базовий шлях для моделі
        if getattr(sys, 'frozen', False):
            # Виконується з PyInstaller
            base_path = sys._MEIPASS
        else:
            # Виконується з джерельного коду
            base_path = os.path.dirname(os.path.abspath(__file__))

        absolute_model_path = os.path.join(base_path, korean_model_path)
        self.korean_model = self.load_model(absolute_model_path, "Korean")
        self.whisper_recognizer = WhisperRecognizer()
        self.target_sample_rate = 16000
        self.chunk_size = 4000

    @staticmethod
    def load_model(model_path, model_name):
        try:
            model = Model(model_path)
            logging.info(f"{model_name} модель успішно завантажена")
            return model
        except Exception as e:
            logging.error(f"Помилка при завантаженні {model_name} моделі: {str(e)}")
            raise

    def preprocess_audio(self, audio_file):
        logging.info(f"Preprocessing audio file: {audio_file}")
        try:
            audio = AudioSegment.from_file(audio_file)
            logging.info(f"Original format: channels={audio.channels}, frame_rate={audio.frame_rate}")
            audio = audio.set_channels(1).set_frame_rate(self.target_sample_rate)
            samples = np.array(audio.get_array_of_samples()).astype(np.int16)  # Змінено на int16
            return samples.tobytes()  # Повертаємо bytes для Vosk
        except Exception as e:
            logging.error(f"Error during audio preprocessing: {str(e)}")
            raise

    def detect_language(self, file_path, method='whisper'):
        self.logger.info(f"Starting language detection for file: {file_path}, method: {method}")

        try:
            whisper_result = self.whisper_recognizer.detect_language(file_path)
            if isinstance(whisper_result, tuple):
                whisper_lang, detected_text, result_dict = whisper_result
                confidence = result_dict['confidence']
            elif isinstance(whisper_result, dict):
                whisper_lang = whisper_result.get('final_code', 'unknown')
                detected_text = whisper_result.get('text', '')
                confidence = whisper_result.get('confidence', 0.5)
            else:
                whisper_lang = "unknown"
                confidence = 0.5

            # Використовуємо Vosk ТІЛЬКИ для корейської, якщо метод = 'vosk' і Whisper визначив корейську
            if method == 'vosk' and whisper_lang.lower() == 'ko':
                language, conf = self.detect_language_vosk(file_path)
                if language == 'unknown':
                    self.logger.warning(f"Vosk failed to detect Korean. Falling back to Whisper for {file_path}")
                    return whisper_result
                return {
                    'final': get_language_name(language),
                    'final_code': language,
                    'confidence': conf,
                    'whisper': 'unknown',
                    'langid': ('unknown', 0.0),
                    'langdetect': 'unknown',
                    'text': '',
                    'language_family': get_language_family(language)
                }
            else:
                self.logger.info(f"Using Whisper for language {whisper_lang} in file {file_path}")
                self.logger.debug(f"Whisper result details: {whisper_result}")
                return whisper_result

        except Exception as e:
            self.logger.error(f"Error detecting language for {file_path}: {str(e)}")
            return {
                'final': 'Unknown',
                'final_code': 'unknown',
                'confidence': 0.5,
                'whisper': 'unknown',
                'langid': ('unknown', 0.0),
                'langdetect': 'unknown',
                'text': '',
                'language_family': 'Unknown'
            }

    def detect_language_whisper(self, audio_file):
        print(f"Detecting language for: {audio_file}")
        try:
            detected_languages = self.whisper_recognizer.detect_language(audio_file)

            if isinstance(detected_languages, dict) and audio_file in detected_languages:
                result = detected_languages[audio_file]
                return result['final'], 1.0
            else:
                logging.error(f"Unexpected result format from whisper_recognizer.detect_language: {detected_languages}")
                return "unknown", 0.0
        except Exception as e:
            logging.error(f"Помилка у визначенні мови Whisper: {str(e)}")
            return "unknown", 0.0

    def detect_language_vosk(self, audio_file):
        try:
            korean_score = self.calculate_language_score(audio_file, self.korean_model)
            self.logger.info(f"Vosk Korean score for {audio_file}: {korean_score}")

            # Отримати транскрипцію для перевірки корейських символів
            _, transcription = self.vosk_recognition(audio_file)
            has_korean = any('\uAC00' <= char <= '\uD7AF' for char in transcription)
            word_count = len([word for word in transcription.split() if word.strip()])
            unique_korean_words = len(
                [word for word in transcription.split() if any('\uAC00' <= c <= '\uD7AF' for c in word)])
            korean_char_ratio = sum(1 for char in transcription if '\uAC00' <= char <= '\uD7AF') / len(
                transcription) if transcription else 0.0
            korean_word_ratio = unique_korean_words / word_count if word_count > 0 else 0.0
            korean_confidence_ratio = self.calculate_korean_confidence_ratio(transcription)  # Нова функція

            self.logger.info(
                f"Transcription contains Korean (Hangul): {has_korean}, Word count: {word_count}, Unique Korean words: {unique_korean_words}, Korean char ratio: {korean_char_ratio:.2f}, Korean word ratio: {korean_word_ratio:.2f}, Korean confidence ratio: {korean_confidence_ratio:.2f}, Text: {transcription[:200]}...")

            # Екстремально суворі умови: надзвичайно високий score, наявність Hangul, достатня кількість унікальних корейських слів, висока частка корейських символів і слів, висока впевненість
            if (korean_score > 0.9 and has_korean and unique_korean_words > 5 and
                    korean_char_ratio > 0.9 and korean_word_ratio > 0.95 and korean_confidence_ratio > 0.95):
                return 'ko', korean_score
            else:
                self.logger.warning(
                    f"Vosk could not confirm Korean language (score: {korean_score}, Hangul: {has_korean}, Unique Korean words: {unique_korean_words}, Korean char ratio: {korean_char_ratio:.2f}, Korean word ratio: {korean_word_ratio:.2f}, Korean confidence ratio: {korean_confidence_ratio:.2f}). Returning 'unknown'.")
                return "unknown", 0.0
        except Exception as e:
            logging.error(f"Error detecting language with Vosk for {audio_file}: {str(e)}")
            return "unknown", 0.0

    def calculate_korean_confidence_ratio(self, transcription):
        """Обчислює середню впевненість корейських слів у транскрипції."""
        words = transcription.split()
        total_conf = 0
        korean_word_count = 0

        for word in words:
            if any('\uAC00' <= c <= '\uD7AF' for c in word):
                # Припускаємо, що впевненість зберігається в `self.word_confidences` (додайте її в `vosk_recognition`)
                conf = self.word_confidences.get(word, 0.0)  # Додайте збереження впевненостей у `vosk_recognition`
                total_conf += conf
                korean_word_count += 1

        return total_conf / korean_word_count if korean_word_count > 0 else 0.0

    def calculate_language_score(self, audio_file, model):
        processed_audio = self.preprocess_audio(audio_file)
        if not processed_audio:
            return 0.0

        rec = KaldiRecognizer(model, self.target_sample_rate)
        rec.SetWords(True)

        total_conf = 0
        count = 0
        word_confidences = {}  # Зберігаємо впевненості для кожного слова

        for i in range(0, len(processed_audio), self.chunk_size):
            chunk = processed_audio[i:i + self.chunk_size]
            # self.logger.debug(f"Processing chunk {i} to {i + self.chunk_size} for scoring, chunk length: {len(chunk)}")
            if rec.AcceptWaveform(chunk):
                result = json.loads(rec.Result())
                if 'result' in result:
                    for word_info in result['result']:
                        conf = word_info.get('conf', 0)
                        word_text = word_info.get('word', '').strip()
                        if conf > 0.9999 and any('\uAC00' <= c <= '\uD7AF' for c in
                                                 word_text):  # Враховуємо лише слова з впевненістю > 0.9999 і Hangul
                            self.logger.debug(f"Word: {word_text}, Confidence: {conf}, File: {audio_file}")
                            total_conf += conf
                            count += 1
                            word_confidences[word_text] = conf  # Зберігаємо впевненість
                else:
                    self.logger.warning(f"No results in chunk {i} to {i + self.chunk_size} for {audio_file}")
            else:
                # self.logger.debug(f"Chunk {i} to {i + self.chunk_size} not accepted by Vosk for {audio_file}, skipping")
                continue

        self.word_confidences = word_confidences  # Зберігаємо для використання в `calculate_korean_confidence_ratio`
        score = total_conf / count if count > 0 else 0.0
        self.logger.info(
            f"Calculated Vosk score for Korean: {score} with {count} ultra-high-confidence Korean words processed for {audio_file}")
        return score

    def transcribe_audio(self, file_path, method='whisper'):
        logging.info(f"Початок транскрипції аудіо: {file_path}, метод: {method}")

        if method == 'whisper':
            try:
                transcription = self.whisper_recognizer.transcribe(file_path)
                detected_language = self.whisper_recognizer.detect_language(file_path)
                return detected_language, transcription
            except Exception as e:
                logging.error(f"Помилка при розпізнаванні Whisper: {str(e)}")
                return 'unknown', ""
        elif method == 'vosk':
            return self.vosk_recognition(file_path)
        else:
            raise ValueError(f"Непідтримуваний метод транскрипції: {method}")

    def vosk_recognition(self, file_path):
        self.logger.info(f"Starting Vosk recognition for {file_path} with Korean model")
        try:
            processed_audio = self.preprocess_audio(file_path)
            self.logger.info(f"Audio processed, length: {len(processed_audio)} bytes")
            rec = KaldiRecognizer(self.korean_model, self.target_sample_rate)
            rec.SetWords(True)

            results = []
            processed_chunks = 0
            word_confidences = {}  # Зберігаємо впевненості для кожного слова

            for i in range(0, len(processed_audio), self.chunk_size):
                chunk = processed_audio[i:i + self.chunk_size]
                self.logger.debug(f"Processing chunk {i} to {i + self.chunk_size}")
                if rec.AcceptWaveform(chunk):
                    part_result = json.loads(rec.Result())
                    part_text = part_result.get('text', '')
                    self.logger.info(f"Chunk transcription: {part_text}")
                    results.append(part_text)
                    if 'result' in part_result:
                        for word_info in part_result['result']:
                            word = word_info.get('word', '').strip()
                            conf = word_info.get('conf', 0)
                            if word and conf > 0.9999:
                                word_confidences[word] = conf
                processed_chunks += 1
            self.logger.info(f"Processed {processed_chunks} chunks")

            final_result = json.loads(rec.FinalResult())
            final_text = final_result.get('text', '')
            self.logger.info(f"Final transcription: {final_text}")
            results.append(final_text)

            transcription = ' '.join(results)
            self.logger.info(f"Final cleaned transcription: {transcription[:200]}...")

            # Перевірка на корейські символи (Hangul)
            if any('\uAC00' <= char <= '\uD7AF' for char in transcription):
                detected_language = 'ko'
            else:
                detected_language = 'unknown'

            self.word_confidences = word_confidences  # Зберігаємо для `calculate_korean_confidence_ratio`
            return detected_language, self.post_process_text(transcription)
        except Exception as e:
            logging.error(f"Error during Vosk transcription for Korean: {str(e)}")
            return 'unknown', ""

    @staticmethod
    def post_process_text(text):
        text = ' '.join(text.split())

        sentences = text.split('. ')
        sentences = [s.capitalize() for s in sentences]
        text = '. '.join(sentences)

        if text and text[-1] not in '.!?':
            text += '.'

        words = text.split()
        for i in range(len(words) - 1):
            if words[i][-1] not in ',.!?":;' and words[i + 1][0].isupper():
                words[i] += ','

        text = ' '.join(words)

        return text

    def cleanup(self):
        pass