import threading
import pygame
import time

class AudioController:
    def __init__(self, logger):
        self.start_time = None
        self.logger = logger
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        self.audio_files = []
        self.current_audio_index = 0
        self.is_playing = False
        self.current_position = 0
        self.update_thread = None


    def add_audio_file(self, file_path):
        try:
            sound = pygame.mixer.Sound(file_path)
            self.audio_files.append({
                'path': file_path,
                'sound': sound,
                'length': sound.get_length(),
                'position': 0
            })
            self.logger.info(f"Аудіофайл додано: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Помилка додавання аудіофайлу: {str(e)}")
            return False

    def remove_audio_file(self, index):
        if 0 <= index < len(self.audio_files):
            removed = self.audio_files.pop(index)
            self.logger.info(f"Аудіофайл видалено: {removed['path']}")
            if self.current_audio_index >= len(self.audio_files):
                self.current_audio_index = max(0, len(self.audio_files) - 1)

    def clear_audio_files(self):
        self.audio_files.clear()
        self.current_audio_index = 0
        self.logger.info("Всі аудіофайли видалено")

    def play_audio(self, index=None):
        if index is not None:
            if isinstance(index, int):
                self.current_audio_index = index
            else:
                self.logger.error(f"Неправильний тип індексу: {type(index)}. Очікується int.")
                return

        if self.audio_files:
            if 0 <= self.current_audio_index < len(self.audio_files):
                audio = self.audio_files[self.current_audio_index]

                if audio['position'] >= audio['length']:
                    audio['position'] = 0

                pygame.mixer.music.load(audio['path'])
                pygame.mixer.music.play(start=audio['position'])

                self.start_time = time.time() - audio['position']
                self.is_playing = True
                self.start_update_thread()

                self.logger.info(f"Відтворення аудіо: {audio['path']} (позиція: {audio['position']:.2f} сек)")
            else:
                self.logger.error(f"Неправильний індекс аудіо: {self.current_audio_index}")
        else:
            self.logger.warning("Немає доступних аудіофайлів для відтворення")

    def pause_audio(self):
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.logger.info("Аудіо призупинено")

    def resume_audio(self):
        if not self.is_playing and self.audio_files:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.start_update_thread()
            self.logger.info("Відтворення аудіо відновлено")

    def stop_audio(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.start_time = 0  # Скидаємо таймер
        if self.audio_files:
            self.audio_files[self.current_audio_index]['position'] = 0  # Скидаємо позицію
        self.logger.info("Відтворення аудіо зупинено")

    def next_audio(self):
        if self.current_audio_index < len(self.audio_files) - 1:
            self.stop_audio()
            self.current_audio_index += 1
            self.play_audio()

    def previous_audio(self):
        if self.current_audio_index > 0:
            self.stop_audio()
            self.current_audio_index -= 1
            self.play_audio()

    def get_current_audio_info(self):
        if self.audio_files:
            return self.audio_files[self.current_audio_index]
        return None

    def start_update_thread(self):
        if self.update_thread is None or not self.update_thread.is_alive():
            self.update_thread = threading.Thread(target=self.update_position)
            self.update_thread.daemon = True
            self.update_thread.start()

    def update_position(self):
        while self.is_playing:
            if self.audio_files:
                audio = self.audio_files[self.current_audio_index]
                elapsed_time = time.time() - self.start_time
                audio['position'] = min(elapsed_time, audio['length'])

                # Якщо дійшло до кінця, зупиняємо і переходимо до наступного
                if audio['position'] >= audio['length']:
                    self.next_audio()
                    return

                # **Оновлюємо UI повзунок**
                self.update_ui_progress()

            time.sleep(0.1)

    def update_ui_progress(self):
        if hasattr(self, 'ui_update_callback') and self.ui_update_callback:
            self.ui_update_callback(self.get_audio_position(), self.get_audio_length())

    def seek_audio(self, position):
        if self.audio_files:
            audio = self.audio_files[self.current_audio_index]

            # Обмежуємо позицію в межах тривалості файлу
            position = max(0, min(position, audio['length']))

            self.start_time = time.time() - position  # Оновлюємо початковий час
            audio['position'] = position

            # Перезапускаємо аудіо з оновленої позиції
            if self.is_playing:
                pygame.mixer.music.stop()
                pygame.mixer.music.play()

    def resume_playback(self):
        if not self.is_playing and self.audio_files:
            audio = self.audio_files[self.current_audio_index]

            # **Перезапускаємо аудіо з оновленої позиції**
            self.start_time = time.time() - audio['position']
            pygame.mixer.music.play()

            self.is_playing = True
            self.start_update_thread()
            self.logger.info(f"Відтворення аудіо відновлено з позиції {audio['position']:.2f} сек")

    def get_audio_position(self):
        if self.audio_files:
            return self.audio_files[self.current_audio_index]['position']
        return 0

    def get_audio_length(self):
        if self.audio_files:
            return self.audio_files[self.current_audio_index]['length']
        return 0

    def __del__(self):
        pygame.mixer.quit()