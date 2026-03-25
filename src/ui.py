import logging
import os
import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pyperclip
from PIL import Image

from language_codes import get_language_name, get_language_family
from language_confirmation_dialog import LanguageConfirmationDialog
from translation_results_widget import TranslationResultsWidget


class LogWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Перегляд логів")
        self.geometry("600x450")
        self.resizable(False, False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.log_display = ctk.CTkTextbox(self, height=400, width=580)
        self.log_display.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="nsew")

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=1, column=0, pady=10)

        self.clear_button = ctk.CTkButton(self.button_frame, text="Очистити логи", command=self.clear_logs)
        self.clear_button.grid(row=0, column=0, padx=5)

        self.copy_button = ctk.CTkButton(self.button_frame, text="Копіювати все", command=self.copy_logs)
        self.copy_button.grid(row=0, column=1, padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def clear_logs(self):
        self.log_display.delete("1.0", ctk.END)

    def copy_logs(self):
        log_text = self.log_display.get("1.0", ctk.END)
        pyperclip.copy(log_text)
        messagebox.showinfo("Інформація", "Логи скопійовано до буфера обміну")

    def on_closing(self):
        self.withdraw()


class TextHandler(logging.Handler):
    def __init__(self):
        logging.Handler.__init__(self)
        self.log_queue = queue.Queue()
        self.log_window = None
        self.is_closing = False

    def emit(self, record):
        if not self.is_closing:
            msg = self.format(record)
            self.log_queue.put(msg)
            if self.log_window and hasattr(self.log_window, 'winfo_exists'):
                try:
                    if self.log_window.winfo_exists():
                        self.log_window.after(0, self.process_log_queue)
                except tk.TclError:
                    pass

    def set_log_window(self, log_window):
        self.log_window = log_window
        self.process_log_queue()

    def process_log_queue(self):
        if self.is_closing:
            return
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get()
                if self.log_window and hasattr(self.log_window, 'winfo_exists'):
                    if self.log_window.winfo_exists():
                        self.log_window.log_display.insert(tk.END, msg + '\n')
                        self.log_window.log_display.see(tk.END)
        except tk.TclError:
            pass


class CustomProgressBar(ctk.CTkFrame):
    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.height = 16
        self.thumb_radius = 8
        self.configure(height=self.height)
        self.canvas = ctk.CTkCanvas(self, height=self.height, bg="#2d2d2d", highlightthickness=0)
        self.canvas.pack(fill="x", expand=True)
        self.progress = 0
        self.command = command
        self.is_hovered = False
        self.state = "normal"

        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)

    def configure(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs.pop("state")
            self.update_state()
        super().configure(**kwargs)

    def update_state(self):
        if self.state == "disabled":
            self.canvas.unbind("<Enter>")
            self.canvas.unbind("<Leave>")
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
        else:
            self.canvas.bind("<Enter>", self.on_enter)
            self.canvas.bind("<Leave>", self.on_leave)
            self.canvas.bind("<ButtonPress-1>", self.on_press)
            self.canvas.bind("<B1-Motion>", self.on_drag)
        self.draw_progress()

    def on_enter(self, event=None):
        self.is_hovered = True
        self.draw_progress()

    def on_leave(self, event=None):
        self.is_hovered = False
        self.draw_progress()

    def draw_progress(self):
        self.canvas.delete("all")
        width = self.canvas.winfo_width()
        height = self.height

        bg_color = "#555555"
        fg_color = "#1DB954" if self.is_hovered else "white"

        self.draw_pill(0, 0, width, height, bg_color, "background")

        if self.progress > 0:
            progress_width = max(height, width * self.progress)
            self.draw_pill(0, 0, progress_width, height, fg_color, "progress")

        if self.is_hovered:
            thumb_x = max(self.thumb_radius, min(width * self.progress, width - self.thumb_radius))
            self.canvas.create_oval(thumb_x - self.thumb_radius, (height - self.thumb_radius * 2) // 2,
                                    thumb_x + self.thumb_radius, (height + self.thumb_radius * 2) // 2,
                                    fill="white", outline="", tags="thumb")

    def draw_pill(self, x, y, width, height, color, tag):
        radius = height // 2
        self.canvas.create_oval(x, y, x + height, y + height, fill=color, outline="", tags=tag)
        self.canvas.create_oval(x + width - height, y, x + width, y + height, fill=color, outline="", tags=tag)
        self.canvas.create_rectangle(x + radius, y, x + width - radius, y + height, fill=color, outline="", tags=tag)

    def set(self, value):
        self.progress = value
        self.draw_progress()

    def on_press(self, event):
        if self.state == "normal":
            self.update_progress(event.x)

    def on_drag(self, event):
        if self.state == "normal":
            self.update_progress(event.x)

    def update_progress(self, x):
        width = self.canvas.winfo_width()
        self.progress = max(0, min(1, x / width))
        self.draw_progress()
        if self.command:
            self.command(self.progress)


def open_settings():
    messagebox.showinfo("Налаштування", "Функція налаштувань ще не реалізована.")


class InstructionWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Інструкція користувача")
        self.geometry("600x400")
        self.resizable(True, True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.text_widget = ctk.CTkTextbox(self, wrap="word")
        self.text_widget.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.load_instructions()

    def load_instructions(self):
        instructions = """
        Інструкція з використання Професійного Аудіо Перекладача
        """
        self.text_widget.insert("1.0", instructions)
        self.text_widget.configure(state="disabled")

class LanguageSelectionDialog(ctk.CTkToplevel):
    def __init__(self, parent, audio_files):
        super().__init__(parent)
        self.title("Вибір файлів для визначення мови")
        self.geometry("500x400")
        self.audio_files = audio_files
        self.confirmed = False

        self.create_widgets()

    def create_widgets(self):
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        for audio_file in self.audio_files:
            file_frame = ctk.CTkFrame(frame)
            file_frame.pack(fill="x", pady=5)

            ctk.CTkLabel(file_frame, text=f"Файл: {os.path.basename(audio_file.path)}").pack(side="left")

            var = ctk.BooleanVar(value=True)
            ctk.CTkCheckBox(file_frame, text="Визначити мову", variable=var).pack(side="right")
            audio_file.is_selected_for_identification = var

        ctk.CTkButton(self, text="Почати визначення мови", command=self.on_confirm).pack(pady=10)

    def on_confirm(self):
        self.confirmed = True
        self.destroy()

class AudioFile:
    def __init__(self, path):
        self.path = path
        self.detected_language = None
        self.language_details = None
        self.transcription = None
        self.translations = {}
        self.is_selected_for_translation = ctk.BooleanVar(value=True)
        self.checkbox_var = ctk.BooleanVar(value=True)
        self.listbox_frame = None
        self.translator_choice = ctk.StringVar(value="Translate")

class AudioTranslatorApp(ctk.CTk):
    def __init__(self, audio_controller, speech_recognition, whisper_recognizer, translation, logger):
        super().__init__()
        self.audio_checkboxes = None
        self.detect_language_button = None
        self.play_selected_button = None
        self.clear_files_button = None
        self.remove_file_button = None
        self.add_file_button = None
        self.file_listbox = None
        self.menu = None
        self.result_texts = None
        self.result_notebook = None
        self.status_label = None
        self.status_var = None
        self.translate_button = None
        self.speech_recognition_choice = None
        self.translator_choice = None
        self.time_label = None
        self.progress_bar = None
        self.stop_button = None
        self.play_pause_button = None
        self.file_status_label = None
        self.file_entry = None
        self.after_ids = []

        self.audio_controller = audio_controller
        self.speech_recognition = speech_recognition
        self.whisper_recognizer = whisper_recognizer
        self.text_widgets = {}
        self.translation = translation
        self.logger = logger

        # Add language mapping
        # self.language_mapping = {
        #     "Українська": "uk",
        #     "Російська": "ru"
        # }
        self.language_mapping = {
            "Українська": "uk"
        }
        
        #self.target_languages = ["Українська", "Російська"]
        self.target_languages = ["Українська"]
        self.language_vars = []

        self.audio_files = []
        self.current_audio_index = 0

        self.is_playing = False
        self.audio_length = 0
        self.current_time = 0
        self.file_path = ""
        self.detected_language = None

        self.setup_window()
        self.create_widgets()
        self.create_menu()

        self.log_window = None
        self.text_handler = TextHandler()
        logger.addHandler(self.text_handler)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.is_closing = False

    def setup_window(self):
        self.title("Аудіо Перекладач")
        self.geometry("1100x800")
        self.resizable(False, False)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Визначаємо базовий шлях для .exe або скрипта
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).resolve().parent.parent  # До кореня проєкту

        icon_path = base_path / 'icons' / 'img.ico'

        try:
            icon_path_str = str(icon_path)
            self.logger.info(f"Loading icon from: {icon_path_str}")
            self.iconbitmap(icon_path_str)  # Використовуємо .ico безпосередньо
        except FileNotFoundError as e:
            self.logger.error(f"Помилка: Не знайдено файл іконки {icon_path_str}. Використовуємо стандартну іконку.")
            # Якщо іконка не знайдена, програма використовує стандартну іконку Windows
        except Exception as e:
            self.logger.error(f"Помилка обробки іконки: {str(e)}")

            # Логування для діагностики
        self.logger.info(f"Icon setup completed for window")

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self.create_file_section()
        self.create_player_section()
        self.create_translation_section()
        self.create_result_section()

    def create_file_section(self):
        file_frame = ctk.CTkFrame(self)
        file_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        file_frame.grid_columnconfigure(0, weight=1)

        self.file_listbox = ctk.CTkScrollableFrame(file_frame, fg_color="transparent", orientation="vertical")
        self.file_listbox.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        file_frame.grid_rowconfigure(0, weight=1)

        self.audio_checkboxes = []

        button_frame = ctk.CTkFrame(file_frame)
        button_frame.grid(row=1, column=0, sticky="ew", pady=(5, 0))
        button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.add_file_button = ctk.CTkButton(button_frame, text="Додати файли", command=self.add_files)
        self.add_file_button.grid(row=0, column=0, padx=5)

        self.remove_file_button = ctk.CTkButton(button_frame, text="Видалити файл", command=self.remove_file)
        self.remove_file_button.grid(row=0, column=1, padx=5)

        self.clear_files_button = ctk.CTkButton(button_frame, text="Очистити все", command=self.clear_files)
        self.clear_files_button.grid(row=0, column=2, padx=5)

        self.play_selected_button = ctk.CTkButton(button_frame, text="Відтворити вибране",
                                                  command=self.play_selected_audio)
        self.play_selected_button.grid(row=0, column=3, padx=5)

        self.file_status_label = ctk.CTkLabel(file_frame, text="")
        self.file_status_label.grid(row=2, column=0, columnspan=2, pady=(5, 0))

    def add_files(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Аудіо файли", "*.mp3 *.wav")])
        for file_path in file_paths:
            if file_path:
                if self.audio_controller.add_audio_file(file_path):
                    audio_file = AudioFile(file_path)
                    self.audio_files.append(audio_file)
                    self.add_audio_to_listbox(audio_file)
        if file_paths:
            self.stop_playback()
            self.load_audio(file_paths[-1])
        self.update_player_controls()

    def add_audio_to_listbox(self, audio_file):
        frame = ctk.CTkFrame(self.file_listbox, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=2)

        checkbox = ctk.CTkCheckBox(frame, text="", variable=audio_file.checkbox_var, width=20)
        checkbox.pack(side="left")

        label = ctk.CTkLabel(frame, text=os.path.basename(audio_file.path), anchor="w")
        label.pack(side="left", fill="x", expand=True)

        audio_file.listbox_frame = frame

        self.audio_checkboxes.append((checkbox, label, audio_file))

        frame.bind("<Button-1>", lambda e, af=audio_file: self.toggle_audio_selection(af))
        label.bind("<Button-1>", lambda e, af=audio_file: self.toggle_audio_selection(af))

    def toggle_audio_selection(self, audio_file):
        audio_file.checkbox_var.set(not audio_file.checkbox_var.get())
        self.update_audio_selection()

    def update_audio_selection(self):
        for _, label, af in self.audio_checkboxes:
            if af.checkbox_var.get():
                label.configure(fg_color="gray75" if ctk.get_appearance_mode() == "Light" else "gray25")
            else:
                label.configure(fg_color="transparent")

    def on_checkbox_change(self, audio_file):
        if audio_file.checkbox_var.get():
            self.select_audio_file(audio_file)
        else:
            audio_file.listbox_frame.configure(fg_color="transparent")

    def select_audio_file(self, audio_file):
        for checkbox, label, af in self.audio_checkboxes:
            if af == audio_file:
                label.configure(fg_color="gray75" if ctk.get_appearance_mode() == "Light" else "gray25")
                checkbox.select()
            else:
                label.configure(fg_color="transparent")
                checkbox.deselect()
        self.load_audio(audio_file.path)

    def remove_file(self):
        selected_audio = next((af for cb, _, af in self.audio_checkboxes if af.checkbox_var.get()), None)
        if selected_audio:
            self.stop_playback()
            index = self.audio_files.index(selected_audio)
            self.audio_controller.remove_audio_file(index)
            self.audio_files.remove(selected_audio)
            selected_audio.listbox_frame.destroy()
            self.audio_checkboxes = [(cb, lb, af) for cb, lb, af in self.audio_checkboxes if af != selected_audio]
            self.update_player_controls()
        else:
            messagebox.showwarning("Попередження", "Будь ласка, виберіть аудіо файл для видалення")

    def clear_files(self):
        self.stop_playback()
        for _, _, audio_file in self.audio_checkboxes:
            audio_file.listbox_frame.destroy()
        self.audio_checkboxes.clear()
        self.audio_files.clear()
        self.audio_controller.clear_audio_files()
        self.update_player_controls()

    def play_selected_audio(self):
        selected_audio = next((af for cb, _, af in self.audio_checkboxes if af.checkbox_var.get()), None)
        if selected_audio:
            index = self.audio_files.index(selected_audio)
            self.audio_controller.play_audio(index)
            self.is_playing = True
            self.update_player_controls()
            self.start_progress_update()
        else:
            messagebox.showwarning("Попередження", "Будь ласка, виберіть аудіо файл для відтворення")

    def create_player_section(self):
        player_frame = ctk.CTkFrame(self)
        player_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        player_frame.grid_columnconfigure(1, weight=1)

        self.play_pause_button = ctk.CTkButton(player_frame, text="▶", command=self.toggle_playback, width=40)
        self.play_pause_button.grid(row=0, column=0, padx=(0, 10))

        self.stop_button = ctk.CTkButton(player_frame, text="⏹", command=self.stop_playback, width=40)
        self.stop_button.grid(row=0, column=2, padx=(10, 0))

        self.progress_bar = CustomProgressBar(player_frame, command=self.seek_audio_position)
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=10)
        self.progress_bar.command = self.seek_audio_position

        self.time_label = ctk.CTkLabel(player_frame, text="0:00 / 0:00")
        self.time_label.grid(row=1, column=1, pady=(5, 0))

        self.update_player_controls()

    def update_audio_controls(self):
        if self.audio_files:
            self.remove_file_button.configure(state="normal")
            self.clear_files_button.configure(state="normal")
            self.play_selected_button.configure(state="normal")
            self.detect_language_button.configure(state="normal")
        else:
            self.remove_file_button.configure(state="disabled")
            self.clear_files_button.configure(state="disabled")
            self.play_selected_button.configure(state="disabled")
            self.detect_language_button.configure(state="disabled")

    def update_player_controls(self):
        if self.audio_controller.is_playing:
            self.play_pause_button.configure(text="⏸")
        else:
            self.play_pause_button.configure(text="▶")

        if self.audio_files:
            self.play_pause_button.configure(state="normal")
            self.stop_button.configure(state="normal")
            self.progress_bar.configure(state="normal")
            self.remove_file_button.configure(state="normal")
            self.clear_files_button.configure(state="normal")
            self.play_selected_button.configure(state="normal")
        else:
            self.play_pause_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.progress_bar.configure(state="disabled")
            self.remove_file_button.configure(state="disabled")
            self.clear_files_button.configure(state="disabled")
            self.play_selected_button.configure(state="disabled")

    def create_translation_section(self):
        translation_frame = ctk.CTkFrame(self)
        translation_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        translation_frame.grid_columnconfigure(0, weight=1)

        lang_frame = ctk.CTkFrame(translation_frame)
        lang_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        lang_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lang_frame, text="Цільові мови:").grid(row=0, column=0, sticky="w", padx=5)

        # for i, lang in enumerate(["Українська", "Російська"]):
        #     var = ctk.BooleanVar(value=True)
        #     self.language_vars.append(var)
        #     ctk.CTkCheckBox(lang_frame, text=lang, variable=var).grid(row=0, column=i + 1, padx=5)

        var = ctk.BooleanVar(value=True)
        self.language_vars.append(var)
        ctk.CTkCheckBox(lang_frame, text="Українська", variable=var).grid(row=0, column=1, padx=5)

        translator_frame = ctk.CTkFrame(translation_frame)
        translator_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        translator_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(translator_frame, text="Перекладач:").grid(row=0, column=0, sticky="w", padx=5)

        available_translators = self.translation.get_available_translators()
        self.translator_choice = ctk.StringVar(value="Translate")

        def on_translator_change(value):
            self.logger.info(f"Translator changed to: {value}")
            self.translator_choice.set(value)

        translator_options = ctk.CTkSegmentedButton(
            translator_frame,
            values=available_translators,
            variable=self.translator_choice,
            command=on_translator_change,  # Додаємо callback
            dynamic_resizing=False
        )
        translator_options.grid(row=0, column=1, sticky="ew", padx=5)

        recognition_frame = ctk.CTkFrame(translation_frame)
        recognition_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        recognition_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(recognition_frame, text="Розпізнавання:").grid(row=0, column=0, sticky="w", padx=5)

        self.speech_recognition_choice = ctk.StringVar(value="whisper")
        recognition_methods = ["whisper", "vosk"]
        recognition_options = ctk.CTkSegmentedButton(
            recognition_frame,
            values=recognition_methods,
            variable=self.speech_recognition_choice,
            dynamic_resizing=False
        )
        recognition_options.grid(row=0, column=1, sticky="ew", padx=5)

        button_frame = ctk.CTkFrame(translation_frame)
        button_frame.grid(row=4, column=0, sticky="ew", pady=(5, 0))
        button_frame.grid_columnconfigure((0, 1), weight=1)

        self.detect_language_button = ctk.CTkButton(
            button_frame,
            text="Визначити мову",
            command=self.detect_language
        )
        self.detect_language_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.translate_button = ctk.CTkButton(
            button_frame,
            text="Перекласти",
            command=self.start_translation
        )
        self.translate_button.grid(row=0, column=1, padx=(5, 0), sticky="ew")

        self.status_var = ctk.StringVar(value="Готово")
        self.status_label = ctk.CTkLabel(translation_frame, textvariable=self.status_var)
        self.status_label.grid(row=5, column=0, pady=(5, 0))

    def create_result_section(self):
        self.result_widget = TranslationResultsWidget(self)
        self.result_widget.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 20))

    def create_menu(self):
        self.menu = tk.Menu(self)
        self.config(menu=self.menu)

        file_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Експорт перекладу", command=self.export_translation)
        file_menu.add_separator()
        file_menu.add_command(label="Вихід", command=self.on_closing)

        edit_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Редагування", menu=edit_menu)
        edit_menu.add_command(label="Копіювати поточний переклад", command=self.copy_current_translation)

        tools_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Інструменти", menu=tools_menu)
        tools_menu.add_command(label="Налаштування", command=open_settings)
        tools_menu.add_command(label="Переглянути логи", command=self.open_log_window)

        help_menu = tk.Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Довідка", menu=help_menu)

        help_items = {
            "Інструкція": self.show_instructions,
            "Про програму": self.show_about
        }

        for label, command in help_items.items():
            help_menu.add_command(label=label, command=command)

    def export_translation(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as file:
                    for lang, text_widget in self.result_texts.items():
                        file.write(f"--- {lang} ---\n")
                        file.write(text_widget.get("1.0", ctk.END))
                        file.write("\n\n")
                messagebox.showinfo("Експорт", "Переклад успішно експортовано!")
            except Exception as e:
                self.logger.error(f"Помилка при експорті перекладу: {str(e)}")
                messagebox.showerror("Помилка", f"Не вдалося експортувати переклад: {str(e)}")

    def copy_current_translation(self):
        current_tab = self.result_notebook.get()
        if current_tab in self.result_texts:
            text = self.result_texts[current_tab].get("1.0", ctk.END)
            self.clipboard_clear()
            self.clipboard_append(text)
            messagebox.showinfo("Копіювання", f"Текст з вкладки '{current_tab}' скопійовано в буфер обміну.")
        else:
            messagebox.showwarning("Попередження", "Немає тексту для копіювання.")

    def show_instructions(self):
        instruction_window = InstructionWindow(self)
        instruction_window.focus_force()

    @staticmethod
    def show_about():
        about_text = """
        Професійний Аудіо Перекладач
        Версія: 1.0

        Розроблено для перекладу аудіо файлів на різні мови.

        © 2024 Моя Компанія. Всі права захищені.
        """
        messagebox.showinfo("Про програму", about_text)

    def open_log_window(self):
        if self.log_window is None or not self.log_window.winfo_exists():
            self.log_window = LogWindow(self)
            self.log_window.title("Перегляд логів")
            self.log_window.clear_button.configure(text="Очистити логи")
            self.text_handler.set_log_window(self.log_window)
        else:
            self.log_window.deiconify()
        self.log_window.focus()

    def on_closing(self):
        if not self.is_closing and messagebox.askokcancel("Вихід", "Ви впевнені, що хочете вийти?"):
            self.is_closing = True
            self.text_handler.is_closing = True
            self.logger.info("Починаємо закриття програми")
            self.stop_all_processes()
            self.speech_recognition.cleanup()
            self.logger.info("Всі процеси зупинено")
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
                handler.close()
            self.destroy()

    def stop_all_processes(self):
        if self.is_playing:
            self.stop_playback()

        for after_id in getattr(self, 'after_ids', []):
            self.after_cancel(after_id)

    def browse_file(self):
        self.logger.info("Вибір аудіо файлу")
        file_path = filedialog.askopenfilename(filetypes=[("Аудіо файли", "*.mp3 *.wav")])
        if file_path:
            self.logger.info(f"Обрано файл: {file_path}")
            self.file_path = file_path
            self.file_entry.configure(state="normal")
            self.file_entry.delete(0, ctk.END)
            self.file_entry.insert(0, os.path.basename(file_path))
            self.file_entry.configure(state="readonly")
            self.update_file_status(file_path)
            self.load_audio(file_path)

    def update_file_status(self, file_path=None):
        if file_path:
            status_text = f"Файл успішно завантажено: {file_path}"
            self.file_status_label.configure(text=status_text, text_color="green")
        else:
            self.file_status_label.configure(text="Файл не завантажено", text_color="red")

    def load_audio(self, file_path):
        self.logger.info(f"Завантаження аудіо файлу: {file_path}")
        try:
            index = next(i for i, af in enumerate(self.audio_files) if af.path == file_path)
            self.audio_controller.current_audio_index = index
            audio_info = self.audio_controller.get_current_audio_info()
            self.audio_length = audio_info['length']
            self.file_path = file_path
            self.update_time_label()
            self.logger.info(f"Аудіо успішно завантажено. Тривалість: {self.audio_length} секунд")
            self.update_file_status(file_path)
        except Exception as e:
            self.logger.exception(f"Виняток при завантаженні аудіо: {str(e)}")
            self.show_error(f"Помилка завантаження аудіо: {str(e)}")
            self.update_file_status()

    def toggle_playback(self):
        if self.is_playing:
            self.pause_playback()
        else:
            # Якщо немає завантаженого аудіо, шукаємо вибране і запускаємо
            if not self.audio_files or self.audio_controller.get_current_audio_info() is None:
                selected_audio = next((af for cb, _, af in self.audio_checkboxes if af.checkbox_var.get()), None)
                if selected_audio:
                    index = self.audio_files.index(selected_audio)
                    self.audio_controller.play_audio(index)  # Завантажуємо і граємо
                    self.is_playing = True
                    self.update_player_controls()
                    self.start_progress_update()
                else:
                    messagebox.showerror("Помилка", "Будь ласка, виберіть аудіофайл.")
            else:
                self.resume_playback()

    def start_playback(self):
        self.logger.info("Початок відтворення")
        try:
            self.audio_controller.play_audio()
            self.is_playing = True
            self.play_pause_button.configure(text="⏸")
            self.start_progress_update()
            self.logger.info("Відтворення успішно розпочато")
        except Exception as e:
            self.logger.exception(f"Помилка при початку відтворення: {str(e)}")
            self.show_error(f"Помилка при початку відтворення: {str(e)}")
        self.update_player_controls()

    def pause_playback(self):
        self.logger.info("Пауза відтворення")
        try:
            self.audio_controller.pause_audio()
            self.is_playing = False
            self.play_pause_button.configure(text="▶")
            self.logger.info("Відтворення успішно призупинено")
        except Exception as e:
            self.logger.exception(f"Помилка при призупиненні відтворення: {str(e)}")
            self.show_error(f"Помилка при призупиненні відтворення: {str(e)}")
        self.update_player_controls()

    def resume_playback(self):
        self.logger.info("Відновлення відтворення")
        try:
            self.audio_controller.resume_audio()
            self.is_playing = True
            self.play_pause_button.configure(text="⏸")
            self.start_progress_update()
            self.logger.info("Відтворення успішно відновлено")
        except Exception as e:
            self.logger.exception(f"Помилка при відновленні відтворення: {str(e)}")
            self.show_error(f"Помилка при відновленні відтворення: {str(e)}")
        self.update_player_controls()

    def stop_playback(self):
        self.logger.info("Зупинка відтворення")
        try:
            self.audio_controller.stop_audio()
            self.is_playing = False
            self.current_time = 0
            self.progress_bar.set(0)
            self.play_pause_button.configure(text="▶")
            self.update_time_label()
            self.logger.info("Відтворення успішно зупинено")
        except Exception as e:
            self.logger.exception(f"Помилка при зупинці відтворення: {str(e)}")
            self.show_error(f"Помилка при зупинці відтворення: {str(e)}")
        self.update_player_controls()

    def seek_audio_position(self, position):
        self.logger.info(f"Перехід до позиції: {position}")
        try:
            if self.audio_length > 0:
                seek_time = position * self.audio_length
                self.audio_controller.seek_audio(seek_time)
                self.current_time = seek_time
                self.update_time_label()
                self.logger.info(f"Перехід завершено до позиції: {seek_time}")
        except Exception as e:
            self.logger.exception(f"Помилка в seek_audio_position: {str(e)}")
            self.show_error(f"Помилка при переході до позиції аудіо: {str(e)}")

    def start_progress_update(self):
        self.update_progress_bar()

    def update_progress_bar(self):
        try:
            self.current_time = self.audio_controller.get_audio_position()
            progress = self.current_time / self.audio_length if self.audio_length > 0 else 0
            self.progress_bar.set(progress)
            self.update_time_label()
        except Exception as e:
            self.logger.exception(f"Помилка оновлення прогрес-бару: {str(e)}")
        finally:
            if self.is_playing:
                self.after_ids.append(self.after(100, self.update_progress_bar))

    def update_time_label(self):
        current_time_str = self.format_time(self.current_time)
        total_time_str = self.format_time(self.audio_length)
        self.time_label.configure(text=f"{current_time_str} / {total_time_str}")

    @staticmethod
    def format_time(seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def clean_transcription(self, text):
        if not text or not isinstance(text, str):
            return ""
        # Видаляємо зайві пробіли, повторення та нормалізуємо текст
        text = ' '.join(text.split())  # Видаляємо зайві пробіли
        # Видаляємо повторювані фрази (просте рішення)
        words = text.split()
        if len(words) > 10:  # Якщо текст довгий, перевіряємо на повторення
            cleaned_words = []
            prev_word = None
            for word in words:
                if word != prev_word or not cleaned_words:  # Уникаємо поспіль повторюваних слів
                    cleaned_words.append(word)
                prev_word = word
            text = ' '.join(cleaned_words)
        return text.strip()

    def show_error(self, message):
        self.logger.error(f"Помилка: {message}")
        messagebox.showerror("Помилка", message)

    def detect_language(self):
        selected_audios = [af for af in self.audio_files if af.checkbox_var.get()]
        if not selected_audios:
            messagebox.showerror("Помилка", "Будь ласка, виберіть хоча б один аудіо файл для визначення мови.")
            return

        self.detect_language_button.configure(state="disabled")
        self.status_var.set("Визначення мови...")

        def update_status(message, progress=None):
            self.status_var.set(message)
            if progress is not None and hasattr(self, 'progress_bar'):
                self.progress_bar.set(progress)

        def detection_task():
            try:
                total_files = len(selected_audios)
                for i, audio_file in enumerate(selected_audios, 1):
                    file_name = os.path.basename(audio_file.path)
                    self.logger.info(f"Початок обробки файлу {i}/{total_files}: {file_name}")

                    progress = i / total_files
                    estimated_time = 30 * (total_files - i + 1)
                    status_message = (
                        f"Визначення мови для файлу {i}/{total_files}: {file_name}\n"
                        f"Приблизний час до завершення: {estimated_time} сек"
                    )
                    self.after(0, lambda m=status_message, p=progress: update_status(m, p))

                    start_time = time.time()
                    method = self.speech_recognition_choice.get()
                    # Додаємо перевірку, чи мова підтримує Vosk
                    whisper_result = self.speech_recognition.whisper_recognizer.detect_language(audio_file.path)
                    whisper_lang = whisper_result['final_code'] if isinstance(whisper_result, dict) else 'unknown'

                    if method == 'vosk' and whisper_lang.lower() != 'ko':
                        self.logger.warning(f"Vosk cannot be used for {whisper_lang}. Using Whisper instead.")
                        method = 'whisper'

                    detected_language = self.speech_recognition.detect_language(audio_file.path, method=method)

                    # Перевірка, чи результат є словником або кортежем
                    if isinstance(detected_language, dict):
                        audio_file.detected_language = detected_language['final'] if detected_language['final'] != "Unknown" else "Невідома мова"
                        audio_file.language_details = detected_language
                    elif isinstance(detected_language, tuple):
                        lang, text, conf = detected_language
                        audio_file.detected_language = get_language_name(lang) if lang != "unknown" else "Невідома мова"
                        audio_file.language_details = {
                            'final': audio_file.detected_language,
                            'final_code': lang,
                            'confidence': conf,
                            'whisper': lang,
                            'langid': ('unknown', 0.0),  # Можна уточнити через langid, якщо потрібно
                            'langdetect': 'unknown',
                            'text': text,
                            'language_family': get_language_family(lang)
                        }
                    else:
                        audio_file.detected_language = "Невідома мова"
                        audio_file.language_details = {
                            'final': "Unknown",
                            'final_code': 'unknown',
                            'confidence': 0.5,
                            'whisper': 'unknown',
                            'langid': ('unknown', 0.0),
                            'langdetect': 'unknown',
                            'text': '',
                            'language_family': 'Unknown'
                        }

                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Файл: {audio_file.path} (оброблено за {elapsed_time:.1f} сек)")
                    self.logger.info(f"Фінальна виявлена мова: {audio_file.detected_language}")
                    self.logger.info(f"Whisper: {audio_file.language_details['whisper']}")
                    self.logger.info(
                        f"Langid: {audio_file.language_details['langid'][0]} "
                        f"(впевненість: {audio_file.language_details['langid'][1]:.2f})"
                    )
                    self.logger.info(f"Langdetect: {audio_file.language_details['langdetect']}")

                    self.after(0, lambda p=progress: self.progress_bar.set(p))

                self.after(0, lambda: self.status_var.set("Завершення визначення мови..."))
                self.after(0, lambda: self.show_language_confirmation(selected_audios))

            except Exception as e:
                self.logger.error(f"Помилка при визначенні мови: {str(e)}")
                self.after(0, lambda: self.status_var.set(f"Помилка: {str(e)}"))
                self.after(0, lambda: messagebox.showerror("Помилка",
                                                           f"Виникла помилка при визначенні мови:\n{str(e)}"))
            finally:
                self.after(0, lambda: self.detect_language_button.configure(state="normal"))
                self.after(0, lambda: update_status("Готово", 0))

        threading.Thread(target=detection_task, daemon=True).start()

    def show_language_confirmation(self, selected_audios):
        language_confirmation = LanguageConfirmationDialog(
            self, 
            selected_audios,
            self.translation.get_available_translators()
        )
        self.wait_window(language_confirmation)

        files_to_translate = [
            af for af in selected_audios 
            if af.is_selected_for_translation.get()
        ]
        
        if files_to_translate:
            self.result_widget.clear()
            self._start_translation_process()

        self.update_language_detection_display(selected_audios)

    def _start_translation_process(self):
        self.logger.info("Початок процесу перекладу")
        try:
            files_to_translate = [
                af for af in self.audio_files 
                if af.checkbox_var.get() and af.is_selected_for_translation.get()
            ]
            
            if not files_to_translate:
                messagebox.showwarning(
                    "Попередження",
                    "Будь ласка, виберіть хоча б один файл для перекладу"
                )
                return
                
            self.translate_button.configure(state="disabled")
            self.status_var.set("Початок транскрипції та перекладу...")

            threading.Thread(
                target=self.translation_task,
                args=(files_to_translate,),
                daemon=True
            ).start()

        except Exception as e:
            self.logger.error(f"Критична помилка в start_translation: {str(e)}")
            self.show_error(f"Критична помилка під час перекладу: {str(e)}")
            self.translate_button.configure(state="normal")

    def update_language_detection_display(self, selected_audios):
        if "Оригінал" in self.text_widgets:
            self.text_widgets["Оригінал"].delete("1.0", ctk.END)
            for audio_file in selected_audios:
                cleaned_transcription = self.clean_transcription(audio_file.transcription or "")
                self.text_widgets["Оригінал"].insert(ctk.END, f"Файл: {os.path.basename(audio_file.path)}\n")
                self.text_widgets["Оригінал"].insert(ctk.END,
                                                     f"Фінальна виявлена мова: {audio_file.detected_language}\n")
                self.text_widgets["Оригінал"].insert(ctk.END, f"Whisper: {audio_file.language_details['whisper']}\n")
                self.text_widgets["Оригінал"].insert(ctk.END,
                                                     f"Langid: {audio_file.language_details['langid'][0]} (впевненість: {audio_file.language_details['langid'][1]:.2f})\n")
                self.text_widgets["Оригінал"].insert(ctk.END,
                                                     f"Langdetect: {audio_file.language_details['langdetect']}\n\n")
                self.text_widgets["Оригінал"].insert(ctk.END, f"Транскрипція: {cleaned_transcription}\n\n")

    def start_translation(self):
        self._start_translation_process()

    def translation_task(self, files_to_translate):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        try:
            total_files = len(files_to_translate)
            total_steps = total_files * (1 + len(self.target_languages))
            current_step = 0

            for audio_file in files_to_translate:
                file_name = os.path.basename(audio_file.path)
                self.logger.info(f"Processing file {file_name} with source language: {audio_file.detected_language}")

                current_step += 1
                progress = current_step / total_steps
                self.update_progress(progress, f"Транскрибування аудіо: {file_name}", current_step, total_steps)

                method = self.speech_recognition_choice.get()
                self.logger.info(f"Using transcription method: {method} for {audio_file.path}")
                transcription_result = self.speech_recognition.transcribe_audio(audio_file.path, method=method)
                if isinstance(transcription_result, tuple):
                    detected_language, transcription_text = transcription_result
                else:
                    transcription_text = transcription_result
                    detected_language = audio_file.detected_language or "unknown"

                if isinstance(transcription_text, tuple):
                    transcription_text = transcription_text[1] if len(transcription_text) > 1 else str(
                        transcription_text[0])
                elif not isinstance(transcription_text, str):
                    transcription_text = str(transcription_text)

                transcription_text = self.clean_transcription(transcription_text)
                audio_file.transcription = transcription_text
                source_lang = detected_language['final_code'] if isinstance(detected_language,
                                                                            dict) else detected_language
                if source_lang == "unknown" and audio_file.language_details.get('whisper') != 'unknown':
                    source_lang = audio_file.language_details['whisper']  # Використовуємо мову Whisper, якщо доступна

                # Перевірка якості транскрипції
                if not transcription_text or len(transcription_text.strip()) < 5 or \
                        transcription_text.strip().lower() in ["музика", "music", "..."]:
                    self.logger.warning(
                        f"Transcription for {file_name} is empty or insignificant: {transcription_text}")
                    audio_file.translations["Українська"] = "Немає тексту для перекладу (можливо, лише музика)"
                    #audio_file.translations["Російська"] = "Нет текста для перевода (возможно, только музыка)"
                    self.after(0, self.update_result_display)
                    continue  # Пропускаємо переклад

                self.logger.info(f"Confirmed source language: {source_lang}")
                self.logger.info(f"Cleaned transcription for {file_name}: {transcription_text[:200]}...")

                def translate_to_language(target_lang_name):
                    target_lang_code = self.language_mapping.get(target_lang_name)
                    service = "MarianMT" if source_lang == "ko" else audio_file.translator_choice.get()
                    self.logger.info(f"Using service {service} for {source_lang} to {target_lang_code}")
                    try:
                        translated_text = self.translation.translate_text(
                            text=transcription_text,
                            source_lang=source_lang,
                            dest_lang=target_lang_code,
                            service=service
                        )
                        return target_lang_name, translated_text, service
                    except Exception as e:
                        error_msg = f"Помилка перекладу на {target_lang_name}: {str(e)}"
                        self.logger.error(error_msg)
                        return target_lang_name, error_msg, service

                selected_languages = [
                    lang for lang in self.target_languages
                    if self.language_vars[self.target_languages.index(lang)].get()
                ]

                self.logger.info(
                    f"Starting translation for {file_name} with translator: {audio_file.translator_choice.get()}")

                with ThreadPoolExecutor(max_workers=len(selected_languages)) as executor:
                    futures = {
                        executor.submit(translate_to_language, lang): lang
                        for lang in selected_languages
                    }
                    for future in as_completed(futures):
                        target_lang_name, translated_text, used_service = future.result()
                        audio_file.translations[target_lang_name] = translated_text
                        current_step += 1
                        progress = current_step / total_steps
                        self.update_progress(
                            progress,
                            f"Переклад на {target_lang_name}: {file_name}",
                            current_step,
                            total_steps
                        )
                        self.logger.info(
                            f"Translated to {target_lang_name} using {used_service}: {translated_text[:200]}...")

                self.after(0, self.update_result_display)
                self.after(0, lambda: self.status_var.set("Переклад завершено"))
                self.after(0, lambda: self.progress_bar.set(0))

        except Exception as e:
            self.logger.error(f"Translation task error: {str(e)}")
            error_message = f"Помилка: {str(e)}"
            self.after(0, lambda msg=error_message: self.status_var.set(msg))
        finally:
            self.after(0, lambda: self.translate_button.configure(state="normal"))

    def update_progress(self, progress, message, current_step, total_steps):
        estimated_time = 45 * (total_steps - current_step)
        status_message = f"{message} ({current_step}/{total_steps})\n" \
                        f"Приблизний час до завершення: {estimated_time} сек"
        self.status_var.set(status_message)
        self.progress_bar.set(progress)

    def update_result_display(self):
        for audio_file in self.audio_files:
            if audio_file.is_selected_for_translation.get():
                # results = {
                #     "Оригінал": f"Виявлена мова: {audio_file.detected_language}\n\n{audio_file.transcription}",
                #     "Українська": audio_file.translations.get("Українська", ""),
                #     "Російська": audio_file.translations.get("Російська", "")
                # }
                results = {
                    "Оригінал": f"Виявлена мова: {audio_file.detected_language}\n\n{audio_file.transcription}",
                    "Українська": audio_file.translations.get("Українська", "")
                }
                self.result_widget.add_translation_result(os.path.basename(audio_file.path), results)

    def update_status(self, message):
        self.status_var.set(message)
        self.logger.info(message)
