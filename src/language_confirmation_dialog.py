import customtkinter as ctk
import os


class LanguageConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent, audio_files, available_translators):
        super().__init__(parent)
        self.title("Підтвердження мови аудіо та вибір перекладача")
        self.geometry("700x500")
        self.audio_files = audio_files
        self.available_translators = available_translators

        self.create_widgets()

    def create_widgets(self):
        frame = ctk.CTkScrollableFrame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        headers = ["Файл", "Виявлена мова", "Перекладати", "Перекладач"]
        for i, header in enumerate(headers):
            ctk.CTkLabel(frame, text=header, font=("Arial", 12, "bold")).grid(
                row=0, column=i, padx=5, pady=5, sticky="w"
            )

        for i, audio_file in enumerate(self.audio_files, start=1):
            ctk.CTkLabel(frame, text=os.path.basename(audio_file.path)).grid(
                row=i, column=0, padx=5, pady=2, sticky="w"
            )
            ctk.CTkLabel(frame, text=audio_file.detected_language).grid(
                row=i, column=1, padx=5, pady=2, sticky="w"
            )

            translate_checkbox = ctk.CTkCheckBox(
                frame, text="", variable=audio_file.is_selected_for_translation
            )
            translate_checkbox.grid(row=i, column=2, padx=5, pady=2)

            if not audio_file.translator_choice.get():
                audio_file.translator_choice.set("Translate")
            translator_menu = ctk.CTkOptionMenu(
                frame,
                variable=audio_file.translator_choice,
                values=self.available_translators
            )
            translator_menu.grid(row=i, column=3, padx=5, pady=2)

        ctk.CTkButton(self, text="Підтвердити", command=self.on_confirm).pack(pady=10)

    def on_confirm(self):
        self.destroy()