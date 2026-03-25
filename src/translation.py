import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ssl import SSLError
from typing import List, Any, Optional

from deep_translator import GoogleTranslator as DeepGoogleTranslator
from dotenv import load_dotenv
from googletrans import Translator as GoogleTranslator
from transformers import MarianMTModel, MarianTokenizer
from translate import Translator

from app_paths import hf_hub_cache_dir

load_dotenv()


class Translation:
    CHUNK_SIZE = 500
    API_DELAY = 2
    MAX_RETRIES = 5

    def __init__(self, logger):
        self.logger = logger
        self.google_translator = GoogleTranslator()
        self.deepl_api_key = os.getenv('DEEPL_API_KEY')
        # self.mymemory_email = os.getenv('MYMEMORY_EMAIL', 'your@email.com')

        # Define Helsinki-NLP models (для корейської та китайської)
        self.models = {
            "ko-en": ("Helsinki-NLP/opus-mt-ko-en", MarianMTModel, MarianTokenizer),
            "zh-en": ("Helsinki-NLP/opus-mt-zh-en", MarianMTModel, MarianTokenizer),  # Додаємо модель для китайської
        }
        self.loaded_models = {}

        self.cache_dir = hf_hub_cache_dir()
        self.logger.info(f"Using cache directory for models: {self.cache_dir}")

    def load_model(self, model_key) -> tuple[Optional[MarianTokenizer], Optional[MarianMTModel]]:
        """
        Завантаження моделі MarianMT із вказаного кешу.
        """
        if model_key not in self.loaded_models:
            model_name, model_cls, tokenizer_cls = self.models.get(model_key, (None, None, None))
            if not model_name:
                raise ValueError(f"Модель для {model_key} не підтримується MarianMT")

            try:
                self.logger.info(f"Attempting to load model {model_name} from cache: {self.cache_dir}")
                tokenizer = tokenizer_cls.from_pretrained(model_name, cache_dir=self.cache_dir, force_download=False)
                model = model_cls.from_pretrained(model_name, cache_dir=self.cache_dir, force_download=False)
                self.loaded_models[model_key] = (tokenizer, model)
                self.logger.info(f"Successfully loaded model: {model_name}")
            except Exception as e:
                self.logger.error(f"Failed to load model {model_name} from {self.cache_dir}: {str(e)}")
                raise
        return self.loaded_models[model_key]

    def translate_text(self, text: str, source_lang: str, dest_lang: str, service: str = 'Translate') -> str:
        self.logger.info(f"Translating text from {source_lang} to {dest_lang} using service: {service}")
        source_lang = self._normalize_lang_code(source_lang)
        dest_lang = self._normalize_lang_code(dest_lang)

        if source_lang == dest_lang:
            return text

        if source_lang == "unknown":
            self.logger.warning("Source language is 'unknown'. Attempting to use default Google Translate.")
            return self.google_translate(text, "auto", dest_lang)

        if service == 'MarianMT':
            if source_lang == "ko":
                if dest_lang in ["uk", "ru"]:
                    try:
                        en_text = self._translate_single(text, "ko-en", max_length=512)
                        if not en_text or en_text.startswith("Translation error"):
                            self.logger.warning(f"MarianMT failed for ko-en. Falling back to Google Translate.")
                            return self.google_translate(text, source_lang, dest_lang)
                        return self.google_translate(en_text, "en", dest_lang)
                    except Exception as e:
                        self.logger.error(f"MarianMT error for ko-en: {str(e)}")
                        return self.google_translate(text, source_lang, dest_lang)
                return self._translate_single(text, "ko-en", max_length=512)
            elif source_lang == "zh":
                if dest_lang in ["uk", "ru"]:
                    try:
                        en_text = self._translate_single(text, "zh-en", max_length=512)
                        if not en_text or en_text.startswith("Translation error"):
                            self.logger.warning(f"MarianMT failed for zh-en. Falling back to Google Translate.")
                            return self.google_translate(text, source_lang, dest_lang)
                        return self.google_translate(en_text, "en", dest_lang)
                    except Exception as e:
                        self.logger.error(f"MarianMT error for zh-en: {str(e)}")
                        return self.google_translate(text, source_lang, dest_lang)
                return self._translate_single(text, "zh-en", max_length=512)
            else:
                self.logger.warning(
                    f"MarianMT not supported for source language {source_lang}. Using Google Translate.")
                return self.google_translate(text, source_lang, dest_lang)
        else:
            translation_methods: dict[str, callable] = {
                "Translate": self.translate_translate,
                "Google": self.google_translate,
                "DeepGoogle": self.deep_google_translate,
                "Ensemble": self.ensemble_translate
            }
            translate_method = translation_methods.get(service, self.google_translate)
            try:
                return translate_method(text, source_lang, dest_lang)
            except Exception as e:
                self.logger.error(f"Translation error for {service} from {source_lang} to {dest_lang}: {str(e)}")
                return f"Translation error: {str(e)}"

    def _translate_single(self, text: str, model_key: str, max_length=512) -> str:  # Зменшено з 1024 до 512
        self.logger.info(f"Translating with MarianMT, model: {model_key}, input: {text[:200]}...")
        try:
            tokenizer, model = self.load_model(model_key)
            # Розбиваємо текст на менші частини з урахуванням max_length
            chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
            translated_chunks = []

            for chunk in chunks:
                inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
                self.logger.info(f"Input tokens shape for chunk: {inputs.input_ids.shape}")
                if inputs.input_ids.shape[1] > max_length:
                    self.logger.warning(f"Chunk exceeds max_length ({max_length}), truncating...")
                translated = model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=5,
                    no_repeat_ngram_size=2,
                    length_penalty=2.0,
                    temperature=0.5
                )
                chunk_text = tokenizer.decode(translated[0], skip_special_tokens=True,
                                              clean_up_tokenization_spaces=True)
                translated_chunks.append(chunk_text)
                self.logger.info(f"Output for chunk: {chunk_text[:200]}...")

            translated_text = ' '.join(translated_chunks)
            return translated_text
        except Exception as e:
            self.logger.error(f"Translation error with {model_key}: {str(e)}")
            self.logger.debug(f"Input text causing error: {text[:500]}...")  # Додаємо деталі для дебагінгу
            return f"Translation error: {str(e)}"

    @staticmethod
    def _normalize_lang_code(lang_code: str) -> str:
        lang_mapping = {
            'Українська': 'uk', 'Русский': 'ru', 'Російська': 'ru',
            'Ukrainian': 'uk', 'Russian': 'ru', 'ukr': 'uk', 'rus': 'ru',
            'ukrainian': 'uk', 'russian': 'ru', 'ko': 'ko', 'Korean': 'ko', 'korean': 'ko',
            'Chinese': 'zh', 'китайська': 'zh', 'zh': 'zh'  # Додаємо підтримку китайської
        }
        return lang_mapping.get(lang_code, lang_code[:2].lower() if len(lang_code) > 2 else lang_code.lower())

    def translate_translate(self, text: str, source_lang: str, dest_lang: str) -> str:
        self.logger.info("Starting translation with Translate")
        translator = Translator(to_lang=dest_lang, from_lang=source_lang)
        return self._translate_in_chunks(translator.translate, text)

    def google_translate(self, text: str, source_lang: str, dest_lang: str) -> str:
        self.logger.info("Starting translation with Google Translate")
        try:
            return self._translate_in_chunks(
                lambda chunk: self.google_translator.translate(chunk, dest=dest_lang, src=source_lang).text, text)
        except Exception as e:
            self.logger.error(f"Google Translate error: {str(e)}")
            return f"Translation error: {str(e)}"

    def deep_google_translate(self, text: str, source_lang: str, dest_lang: str) -> str:
        self.logger.info("Starting translation with Deep Google Translate")
        try:
            translator = DeepGoogleTranslator(source=source_lang, target=dest_lang)
            return self._translate_in_chunks(translator.translate, text)
        except Exception as e:
            self.logger.error(f"Deep Google Translate error: {str(e)}")
            return f"Translation error: {str(e)}"

    # def deepl_translate(self, text: str, source_lang: str, dest_lang: str) -> str:
    #     if not self.deepl_api_key:
    #         return "Перекладач DeepL недоступний (відсутній API ключ)"
    #     self.logger.info("Початок перекладу за допомогою DeepL")
    #     translator = DeeplTranslator(api_key=self.deepl_api_key, source=source_lang, target=dest_lang)
    #     return self._translate_in_chunks(translator.translate, text)

    # def mymemory_translate(self, text: str, source_lang: str, dest_lang: str) -> str:
    #     self.logger.info("Початок перекладу за допомогою MyMemory")
    #     translator = MyMemoryTranslator(source=source_lang, target=dest_lang)
    #     return self._translate_in_chunks(translator.translate, text)

    def _translate_in_chunks(self, translate_func, text: str) -> str:
        chunks = [text[i:i + self.CHUNK_SIZE] for i in range(0, len(text), self.CHUNK_SIZE)]
        translated_chunks = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_chunk = {executor.submit(self._translate_chunk_with_retry, translate_func, chunk): chunk for chunk in chunks}
            for i, future in enumerate(as_completed(future_to_chunk)):
                translated_chunks.append(future.result())
                self.logger.info(f"Translated chunk {i + 1}/{len(chunks)}")
        return ' '.join(translated_chunks)

    def _translate_chunk_with_retry(self, translate_func, chunk: str) -> str | None | Any:
        for attempt in range(self.MAX_RETRIES):
            try:
                result = translate_func(chunk)
                if isinstance(result, str):
                    return result
                elif isinstance(result, dict) and 'translatedText' in result:
                    return result['translatedText']
                return str(result)
            except (ConnectionError, SSLError) as e:
                self.logger.error(f"SSL error detected, retrying (attempt {attempt + 1}/{self.MAX_RETRIES}): {str(e)}")
                if attempt == self.MAX_RETRIES - 1:
                    return f"Translation failed due to SSL: {str(e)}"
                time.sleep(self.API_DELAY * (attempt + 1))  # Експоненційна затримка
            except Exception as e:
                self.logger.error(f"Chunk translation error (attempt {attempt + 1}/{self.MAX_RETRIES}): {str(e)}")
                if attempt == self.MAX_RETRIES - 1:
                    return chunk
                time.sleep(self.API_DELAY)

    def ensemble_translate(self, text: str, source_lang: str, dest_lang: str) -> str:
        self.logger.info("Starting ensemble translation")
        methods = [self.translate_translate, self.google_translate, self.deep_google_translate]
        with ThreadPoolExecutor(max_workers=len(methods)) as executor:
            future_to_method = {executor.submit(method, text, source_lang, dest_lang): method.__name__ for method in methods}
            translations = []
            for future in as_completed(future_to_method):
                method_name = future_to_method[future]
                try:
                    result = future.result()
                    translations.append(result)
                    self.logger.info(f"Successful translation by {method_name}")
                except Exception as e:
                    self.logger.error(f"Ensemble translation error by {method_name}: {str(e)}")
        return max(translations, key=len) if translations else "Ensemble translation failed"

    @staticmethod
    def get_available_translators() -> List[str]:
        return ["Translate", "Google", "DeepGoogle", "MarianMT", "Ensemble"]

    def translate_to_multiple_languages(self, text: str, source_lang: str, target_langs: List[str], service: str = 'Translate') -> dict:
        translations = {}
        for lang in target_langs:
            translations[lang] = self.translate_text(text, source_lang, lang, service)
        return translations