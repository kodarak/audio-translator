import logging
import os
import re
import sys
import warnings
from typing import Tuple

import langdetect
import langid
import librosa
from librosa.effects import preemphasis
import torch
from langdetect import detect, LangDetectException
from transformers import WhisperProcessor, WhisperForConditionalGeneration, WhisperTokenizer

from app_paths import hf_hub_cache_dir
from language_codes import (
    get_language_name,
    get_language_family,
    LANGUAGE_CODES
)

warnings.filterwarnings("ignore", category=FutureWarning)


def create_language_groups_from_families():
    language_groups = {}

    for code, info in LANGUAGE_CODES.items():
        if code == 'unknown':
            continue

        family = info['family']
        if family not in language_groups:
            language_groups[family] = set()

        language_groups[family].add(info['name'].lower())
        language_groups[family].add(code.lower())

        for extra_code in info['codes']:
            language_groups[family].add(extra_code.lower())

    return {k: sorted(list(v)) for k, v in language_groups.items()}


def get_language_code_mapping():
    code_mapping = {}

    for code, info in LANGUAGE_CODES.items():
        main_code = code.lower()
        code_mapping[main_code] = main_code
        code_mapping[info['name'].lower()] = main_code
        code_mapping[info['uk_name'].lower()] = main_code

        for variant in info['codes']:
            code_mapping[variant.lower()] = main_code

    return code_mapping


def normalize_whisper_language_code(code: str) -> str:
    code = code.lower()

    for lang_code, lang_info in LANGUAGE_CODES.items():
        if code == lang_code or code in lang_info['codes']:
            return lang_info['name'].lower()

    return LANGUAGE_CODES['unknown']['name'].lower()  # Повертаємо "Unknown"


class WhisperRecognizer:
    def __init__(self):
        self.logger = logging.getLogger("AudioTranslator")
        self.logger.info("Initializing WhisperRecognizer...")
        print("WhisperRecognizer initialized")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model_cache = hf_hub_cache_dir()
        model_id = "openai/whisper-large-v3"
        self.logger.info(f"Loading model: {model_id}")

        try:
            self.processor = WhisperProcessor.from_pretrained(model_id, cache_dir=model_cache)
            self.model = WhisperForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=False,
                use_safetensors=True,
                cache_dir=model_cache,
            ).to(self.device)
            self.tokenizer = WhisperTokenizer.from_pretrained(model_id, cache_dir=model_cache)
            self.feature_extractor = self.processor.feature_extractor

            self.max_target_positions = 2048  # Збільшуємо максимальну довжину для кращого розпізнавання
            self.logger.info("WhisperRecognizer initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing WhisperRecognizer: {str(e)}")
            raise

        self.language_groups = create_language_groups_from_families()
        self.code_mapping = get_language_code_mapping()

        self.supported_languages = {'english', 'chinese', 'german', 'spanish', 'russian', 'korean', 'french',
                                    'japanese', 'portuguese', 'turkish', 'polish', 'catalan', 'dutch', 'arabic',
                                    'swedish', 'italian', 'indonesian', 'hindi', 'finnish', 'vietnamese', 'hebrew',
                                    'ukrainian', 'greek', 'malay', 'czech', 'romanian', 'danish', 'hungarian', 'tamil',
                                    'norwegian', 'thai', 'urdu', 'croatian', 'bulgarian', 'lithuanian', 'latin',
                                    'maori', 'malayalam', 'welsh', 'slovak', 'telugu', 'persian', 'latvian', 'bengali',
                                    'serbian', 'azerbaijani', 'slovenian', 'kannada', 'estonian', 'macedonian',
                                    'breton', 'basque', 'icelandic', 'armenian', 'nepali', 'mongolian', 'bosnian',
                                    'kazakh', 'albanian', 'swahili', 'galician', 'marathi', 'punjabi', 'sinhala',
                                    'khmer', 'shona', 'yoruba', 'somali', 'afrikaans', 'occitan', 'georgian',
                                    'belarusian', 'tajik', 'sindhi', 'gujarati', 'amharic', 'yiddish', 'lao', 'uzbek',
                                    'faroese', 'haitian creole', 'pashto', 'turkmen', 'nynorsk', 'maltese', 'sanskrit',
                                    'luxembourgish', 'myanmar', 'tibetan', 'tagalog', 'malagasy', 'assamese', 'tatar',
                                    'hawaiian', 'lingala', 'hausa', 'bashkir', 'javanese', 'sundanese', 'cantonese'}

    def detect_language_with_whisper(self, audio_input, sampling_rate) -> Tuple[str, str, dict]:
        audio_input = preemphasis(audio_input, coef=0.97)
        try:
            self.logger.info(f"Обробка аудіо довжиною: {len(audio_input)} семплів за допомогою Whisper")

            input_features = self.feature_extractor(
                audio_input,
                sampling_rate=sampling_rate,
                return_tensors="pt"
            ).input_features.to(self.device)

            attention_mask = torch.ones_like(input_features)

            outputs = self.model.generate(
                input_features,
                attention_mask=attention_mask,
                task="transcribe",
                return_timestamps=False,
                max_length=self.max_target_positions,
                num_beams=5,
                no_repeat_ngram_size=2,
                temperature=0.5
            )

            self.logger.debug(
                f"Outputs type: {type(outputs)}, shape: {outputs.size() if isinstance(outputs, torch.Tensor) else 'Not a tensor'}")

            if outputs is None or not isinstance(outputs, torch.Tensor) or outputs.size(0) == 0:
                self.logger.warning("Whisper повернув порожній або некоректний результат")
                return "unknown", "", {'confidence': 0.5, 'has_arabic': False}

            detected_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True,
                                                  clean_up_tokenization_spaces=True)
            self.logger.info(f"Whisper виявив текст: {detected_text[:500]}...")

            self.logger.debug(f"Detected text type: {type(detected_text)}, content: {detected_text[:200]}...")

            if not isinstance(detected_text, str):
                self.logger.error(f"Detected text is not a string: {type(detected_text)}")
                return "unknown", "", {'confidence': 0.5, 'has_arabic': False}

            if not detected_text.strip():
                self.logger.warning(f"Некоректний текст (порожній або лише пробіли): {detected_text}")
                return "unknown", "", {'confidence': 0.5, 'has_arabic': False}

            if len(detected_text.strip()) < 10 or not any(c.isalpha() for c in detected_text) or all(
                    ord(c) > 0xFFFF for c in detected_text):
                self.logger.warning("Detected artifact or short text, returning unknown")
                return "unknown", detected_text, {'confidence': 0.5, 'has_arabic': False}

            # Визначення символів
            has_arabic = (any('\u0600' <= char <= '\u06FF' for char in detected_text) and
                          sum(1 for char in detected_text if '\u0600' <= char <= '\u06FF') / len(detected_text) > 0.5)
            has_korean = any('\uAC00' <= char <= '\uD7AF' for char in detected_text)
            has_chinese = any('\u4E00' <= char <= '\u9FFF' for char in detected_text)
            has_azerbaijani = any(char in 'əöü' for char in detected_text) or self._check_azerbaijani_features(
                detected_text)
            has_kyrgyz = any(char in 'ҮүӨө' for char in detected_text)
            has_turkish = any(char in 'ğışçöü' for char in detected_text)

            # Попереднє визначення мови за символами
            if has_korean:
                self.logger.info("Whisper detected Korean (Hangul characters)")
                return 'ko', detected_text, {'confidence': 0.95, 'has_arabic': False}
            elif has_chinese:
                self.logger.info("Whisper detected Chinese (Han characters)")
                return 'zh', detected_text, {'confidence': 0.95, 'has_arabic': False}
            elif has_arabic:
                self.logger.info("Whisper detected Arabic (Arabic characters)")
                return 'ar', detected_text, {'confidence': 0.95, 'has_arabic': True}
            elif has_azerbaijani:
                self.logger.info("Whisper detected Azerbaijani (specific characters or features: ə, ö, ü)")
                return 'az', detected_text, {'confidence': 0.95, 'has_arabic': False}
            elif has_kyrgyz:
                self.logger.info("Whisper detected Kyrgyz (specific characters: Ү, ү, Ө, ө)")
                kyrgyz_score = self._calculate_language_likelihood(detected_text, 'ky')
                ru_score = self._calculate_language_likelihood(detected_text, 'ru')
                kk_score = self._calculate_language_likelihood(detected_text, 'kk')
                if kyrgyz_score > max(ru_score, kk_score) * 0.8 or sum(
                        1 for char in detected_text if char in 'ҮүӨө') > 2:
                    self.logger.info("Confirming Kyrgyz based on score and characters")
                    return 'ky', detected_text, {
                        'confidence': min(0.98, kyrgyz_score / (kyrgyz_score + max(ru_score, kk_score))),
                        'has_arabic': False}
            elif has_turkish:
                self.logger.info("Whisper detected Turkish (specific characters: ğ, ı, ş, ç, ö, ü)")
                return 'tr', detected_text, {'confidence': 0.9, 'has_arabic': False}

            # Додаткове визначення за langid і langdetect
            langid_lang = 'unknown'
            try:
                langid_result = langid.classify(detected_text)
                langid_lang, langid_confidence = langid_result
                self.logger.info(f"Langid detected: {langid_lang} (confidence: {langid_confidence:.2f})")
            except langid.LangIdError as e:
                self.logger.warning(f"Langid error for text '{detected_text[:200]}...': {str(e)}")

            detected_lang = 'unknown'
            try:
                detected_lang = detect(detected_text)
                self.logger.info(f"Langdetect detected: {detected_lang}")
            except LangDetectException as e:
                self.logger.warning(f"Langdetect error for text '{detected_text[:200]}...': {str(e)}")

            # Логіка для азербайджанської та турецької
            if detected_lang in ['tr', 'az'] and langid_lang in ['tr', 'az']:
                az_score = self._calculate_language_likelihood(detected_text, 'az')
                tr_score = self._calculate_language_likelihood(detected_text, 'tr')
                char_count = detected_text.lower().count('ə')
                if has_azerbaijani and (az_score > tr_score * 0.7 or char_count > 2):  # Зменшено поріг до 0.7
                    self.logger.info("Choosing Azerbaijani based on strong evidence")
                    return 'az', detected_text, {'confidence': min(0.98, az_score / (az_score + tr_score)),
                                                 'has_arabic': False}
                elif has_turkish and tr_score > az_score * 0.8:
                    self.logger.info("Confirming Turkish based on score and characters")
                    return 'tr', detected_text, {'confidence': min(0.9, tr_score / (az_score + tr_score)),
                                                 'has_arabic': False}

            # Перевизначення лише за наявності арабських символів з високою впевненістю
            if has_arabic and (langid_lang == 'ar' or detected_lang == 'ar'):
                self.logger.info("Confirming Arabic due to script and language detection")
                return 'ar', detected_text, {'confidence': 0.95, 'has_arabic': True}

            # Остаточне рішення
            final_lang = detected_lang if detected_lang != 'unknown' else langid_lang
            final_confidence = min(0.85, abs(langid_confidence) / 1000 if langid_confidence else 0.5)
            return final_lang, detected_text, {'confidence': final_confidence, 'has_arabic': has_arabic}

        except Exception as e:
            self.logger.error(f"Помилка обробки Whisper: {str(e)}")
            return "unknown", "", {'confidence': 0.5, 'has_arabic': False}

    def _check_azerbaijani_features(self, text):
        az_words = ['və', 'bu', 'bir', 'üçün', 'çox', 'ilə', 'da', 'də', 'mən', 'oldu', 'var', 'sən', 'məhz']
        az_endings = ['lər', 'lar', 'dir', 'dır', 'dik', 'miş', 'mış']
        words = text.lower().split()
        word_matches = sum(1 for word in words if word in az_words)
        ending_matches = sum(1 for word in words if any(word.endswith(ending) for ending in az_endings))
        char_count = text.lower().count('ə')
        return word_matches > 1 or ending_matches > 1 or char_count > 2  # Збільшено поріг char_count

    def _has_strong_azerbaijani_indicators(self, text):
        """Перевірка сильних індикаторів азербайджанської (комбінація символів і слів)"""
        return any(char in 'əöü' for char in text) and any(
            word in ['və', 'mən', 'nə', 'var'] for word in text.lower().split())

    def _calculate_language_likelihood(self, text, lang_code):
        """Calculate likelihood score that text belongs to a specific language"""
        if lang_code == 'tr':
            # Turkish specific features
            features = {
                'words': ['ve', 'bu', 'bir', 'için', 'çok', 'ile', 'daha', 'ben', 'da', 'de'],
                'endings': ['ler', 'lar', 'dir', 'dır', 'dik', 'miş', 'mış'],
                'chars': ['ğ', 'ı', 'ş', 'ç', 'ö', 'ü']
            }
        elif lang_code == 'az':
            # Azerbaijani specific features
            features = {
                'words': ['və', 'bu', 'bir', 'üçün', 'çox', 'ilə', 'da', 'də', 'mən'],
                'endings': ['lər', 'lar', 'dir', 'dır', 'dik', 'miş', 'mış'],
                'chars': ['ə', 'ğ', 'ı', 'ş', 'ç', 'ö', 'ü']
            }
        else:
            return 0  # Unsupported language

        words = text.lower().split()
        score = 0

        # Check for words
        word_matches = sum(1 for word in words if word in features['words'])
        score += word_matches * 2

        # Check for endings
        ending_matches = sum(1 for word in words if any(word.endswith(ending) for ending in features['endings']))
        score += ending_matches * 1.5

        # Check for characteristic letters
        char_count = sum(text.lower().count(char) for char in features['chars'])
        score += char_count * 0.5

        return score

    @staticmethod
    def _detect_cyrillic_language(text: str) -> Tuple[str, str, float]:
        try:
            detected_lang, confidence = langid.classify(text)
            return detected_lang, text, abs(float(confidence))
        except:
            return 'ru', text, 0.5

    @staticmethod
    def _evaluate_transcription_quality(text: str, language: str, family: str) -> float:
        if not text:
            return 0.0

        score = 0.0

        words = text.split()
        score += len(words) * 2

        # Специфічні перевірки для різних систем письма
        script_scores = {
            'Sino-Tibetan': (u'\u4e00', u'\u9fff', 50),  # Chinese
            'Japonic': (u'\u3040', u'\u309F', 50),  # Hiragana
            'Koreanic': (u'\uAC00', u'\uD7AF', 50),  # Hangul
            'Slavic': (u'\u0400', u'\u04FF', 50),  # Cyrillic
            'Semitic': (u'\u0600', u'\u06FF', 50),  # Arabic
            'Indo-Iranian': (u'\u0900', u'\u097F', 50),  # Devanagari
        }

        if family in script_scores:
            start, end, bonus = script_scores[family]
            if any(start <= char <= end for char in text):
                score += bonus

        if len(words) > 3:
            score += min(len(words) / 5, 10)

            unique_words = len(set(words))
            word_variety = unique_words / len(words)
            score += word_variety * 20

        return min(100.0, score)

    def _detect_language_internal(self, audio_file_path):
        global langdetect_result
        SIMILAR_LANGUAGES = {
            # Тюркські мови
            'turkic': {
                'languages': ['tr', 'az', 'uz', 'kk', 'ky', 'ug', 'tk'],
                'features': {
                    'phonetic': ['ə', 'ü', 'ö', 'ı', 'ğ'],
                    'common_words': {
                        'tr': ['ve', 'bu', 'bir', 'için', 'çok', 'ben'],
                        'az': ['və', 'bu', 'bir', 'var', 'nə', 'mən'],
                        'uz': ['va', 'bu', 'bir', 'bor', 'men'],
                        'kk': ['және', 'бұл', 'бір', 'мен'],
                        'ky': ['жана', 'бул', 'бир', 'мен']
                    }
                }
            },
            # Слов’янські мови
            'slavic': {
                'languages': ['ru', 'uk', 'be', 'bg', 'sr', 'hr', 'sl', 'cs', 'pl', 'sk'],
                'features': {
                    'specific_chars': {
                        'uk': ['ї', 'є', 'і', 'ґ'],
                        'be': ['ў', 'і', 'ь'],
                        'bg': ['ъ', 'щ', 'ю', 'я'],
                        'pl': ['ą', 'ę', 'ł', 'ń', 'ó', 'ś', 'ź', 'ż']
                    }
                }
            },
            # Китайські діалекти
            'chinese': {
                'languages': ['zh', 'yue', 'wuu', 'hsn', 'hak'],
                'features': {
                    'script': ['[\u4e00-\u9fff]'],
                    'frequency': {
                        'zh': ['的', '是', '不', '了', '在'],
                        'yue': ['嘅', '咗', '喺', '唔', '佢']
                    }
                }
            }
        }

        LANGUAGE_FEATURES = {
            'ar': {'script': ['[\u0600-\u06FF]'], 'vowel_patterns': ['ا', 'و', 'ي'],
                   'common_patterns': ['ал', 'фи', 'мен']},
            'ja': {'scripts': ['[\u3040-\u309F]', '[\u30A0-\u30FF]', '[\u4e00-\u9fff]'],
                   'particles': ['は', 'が', 'の', 'ни', 'о']},
            'ko': {'script': ['[\uAC00-\uD7AF]'], 'particles': ['은', '는', 'и', 'га', '을', '를']},
            'ky': {'script': ['[\u0400-\u04FF]'], 'specific_chars': ['Ү', 'ү', 'Ө', 'ө']},
            'tr': {'script': ['[\u0061-\u007A]'], 'specific_chars': ['ğ', 'ı', 'ş']}
        }

        def analyze_audio_segment(audio_data, sample_rate):
            try:
                mfcc = librosa.feature.mfcc(y=audio_data, sr=sample_rate, n_mfcc=13)
                spectral_centroid = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)
                zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
                pitches, magnitudes = librosa.piptrack(y=audio_data, sr=sample_rate)
                return {
                    'mfcc': mfcc,
                    'spectral_centroid': spectral_centroid,
                    'zero_crossing_rate': zero_crossing_rate,
                    'pitches': pitches,
                    'magnitudes': magnitudes
                }
            except Exception as e:
                self.logger.warning(f"Помилка при аналізі аудіо: {str(e)}")
                return None

        def calculate_language_probability(text, audio_features, lang):
            score = 0.0
            if not text or not isinstance(text, str):
                return score

            if lang in LANGUAGE_FEATURES:
                for script_pattern in LANGUAGE_FEATURES[lang].get('scripts', []):
                    if re.search(script_pattern, text):
                        score += 1.0
                for char_pattern in LANGUAGE_FEATURES[lang].get('specific_chars', []):
                    if any(char in text for char in char_pattern):
                        score += 1.0

            for group in SIMILAR_LANGUAGES.values():
                if lang in group['languages']:
                    if 'phonetic' in group['features']:
                        for phonetic in group['features']['phonetic']:
                            if phonetic in text:
                                score += 0.5
                    if 'common_words' in group['features'] and lang in group['features']['common_words']:
                        for word in group['features']['common_words'][lang]:
                            if word in text.lower():
                                score += 0.3

            if audio_features:
                pass  # Тут можна додати аналіз аудіо-ознак, якщо потрібно

            return score

        try:
            audio_input, sampling_rate = librosa.load(audio_file_path, sr=16000, duration=30)
            detected_lang, detected_text, result_dict = self.detect_language_with_whisper(audio_input, sampling_rate)
            initial_confidence = result_dict['confidence']
            has_arabic = result_dict.get('has_arabic', False)  # Безпечний доступ

            if not detected_text or not detected_text.strip():
                return {
                    'final': get_language_name("unknown"),
                    'final_code': 'unknown',
                    'confidence': 0.0,
                    'whisper': 'unknown',
                    'langid': ('unknown', 0.0),
                    'langdetect': 'unknown',
                    'text': "",
                    'language_family': get_language_family("unknown")
                }

            audio_features = analyze_audio_segment(audio_input, sampling_rate)

            language_scores = {}
            for lang in [lang for group in SIMILAR_LANGUAGES.values() for lang in group['languages']]:
                score = calculate_language_probability(detected_text, audio_features, lang)
                language_scores[lang] = score

            langid_result = None
            langid_lang = 'unknown'  # Початкове значення
            try:
                langid_result = langid.classify(detected_text)
                langid_lang, langid_confidence = langid_result
                language_scores[langid_lang] = language_scores.get(langid_lang, 0) + 0.5
                self.logger.info(f"Langid detected: {langid_lang} (confidence: {langid_confidence:.2f})")
            except langid.LangIdError as e:
                self.logger.warning(f"Langid error for text '{detected_text[:200]}...': {str(e)}")

            try:
                langdetect_result = detect(detected_text)
                language_scores[langdetect_result] = language_scores.get(langdetect_result, 0) + 0.5
                self.logger.info(f"Langdetect detected: {langdetect_result}")
            except langdetect.LangDetectException as e:
                self.logger.warning(f"Langdetect error for text '{detected_text[:200]}...': {str(e)}")

            if has_arabic and detected_lang != 'ar' and (langid_result and langid_lang != 'ar'):
                if sum(1 for char in detected_text if '\u0600' <= char <= '\u06FF') / len(detected_text) > 0.7:
                    self.logger.info("Overriding with Arabic due to dominant script evidence")
                    final_lang = 'ar'
                    final_confidence = 0.98
                else:
                    self.logger.warning("Arabic script detected but not dominant, keeping original detection")

            if language_scores:
                final_lang = max(language_scores.items(), key=lambda x: x[1])[0]
                final_confidence = language_scores[final_lang] / sum(
                    language_scores.values()) if language_scores.values() else initial_confidence
            else:
                final_lang = detected_lang
                final_confidence = initial_confidence

            return {
                'final': get_language_name(final_lang),
                'final_code': final_lang,
                'confidence': final_confidence,
                'whisper': detected_lang,
                'langid': (
                langid_result[0] if langid_result else 'unknown', langid_result[1] if langid_result else 0.0),
                'langdetect': langdetect_result if langdetect_result else 'unknown',
                'text': detected_text,
                'language_family': get_language_family(final_lang)
            }

        except Exception as e:
            self.logger.error(f"Помилка визначення мови: {str(e)}")
            return {
                'final': get_language_name("unknown"),
                'final_code': 'unknown',
                'confidence': 0.0,
                'whisper': 'unknown',
                'langid': ('unknown', 0.0),
                'langdetect': 'unknown',
                'text': "",
                'language_family': get_language_family("unknown")
            }

    def detect_language(self, audio_file_path):
        return self._detect_language_internal(audio_file_path)

    def transcribe(self, audio_file_path):
        try:
            result = self.detect_language(audio_file_path)
            language = result['final_code']

            audio_input, sampling_rate = librosa.load(audio_file_path, sr=16000)

            max_chunk_size = 10 * 16000  # Зменшуємо до 10 секунд
            if len(audio_input) > max_chunk_size:
                chunks = [audio_input[i:i + max_chunk_size]
                          for i in range(0, len(audio_input), max_chunk_size)]
                transcription_parts = []

                for chunk in chunks:
                    input_features = self.feature_extractor(
                        chunk,
                        sampling_rate=sampling_rate,
                        return_tensors="pt"
                    ).input_features.to(self.device)

                    with torch.no_grad():
                        outputs = self.model.generate(
                            input_features,
                            task="transcribe",
                            language=language,
                            return_timestamps=True,
                            max_length=self.max_target_positions,
                            num_beams=5,  # Збільшуємо для кращої якості
                            no_repeat_ngram_size=2,
                            length_penalty=2.0,
                            temperature=0.5
                        )

                    chunk_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True,
                                                       clean_up_tokenization_spaces=True)
                    transcription_parts.append(chunk_text)

                transcription = ' '.join(transcription_parts)
            else:
                input_features = self.feature_extractor(
                    audio_input,
                    sampling_rate=sampling_rate,
                    return_tensors="pt"
                ).input_features.to(self.device)

                with torch.no_grad():
                    outputs = self.model.generate(
                        input_features,
                        task="transcribe",
                        language=language,
                        return_timestamps=True,
                        max_length=self.max_target_positions,
                        num_beams=5,
                        no_repeat_ngram_size=2,
                        length_penalty=2.0,
                        temperature=0.5
                    )

                transcription = self.tokenizer.decode(outputs[0], skip_special_tokens=True,
                                                      clean_up_tokenization_spaces=True)

            return language, transcription

        except Exception as e:
            logging.error(f"Error during transcription: {str(e)}")
            raise