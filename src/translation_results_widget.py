import customtkinter as ctk
from typing import Dict, Optional

class TranslationResultsWidget(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.file_selector_frame = ctk.CTkFrame(self)
        self.file_selector_frame.pack(fill="x", padx=10, pady=(5,0))

        self.file_label = ctk.CTkLabel(self.file_selector_frame, text="Обраний файл:")
        self.file_label.pack(side="left", padx=5)

        self.file_selector = ctk.CTkOptionMenu(
            self.file_selector_frame,
            values=["Немає файлів"],
            command=self.on_file_selected
        )
        self.file_selector.pack(side="left", padx=5, fill="x", expand=True)

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=5)

        self.tabs = {
            "Оригінал": self.tab_view.add("Оригінал"),
            "Українська": self.tab_view.add("Українська")
            #"Російська": self.tab_view.add("Російська")
        }

        self.text_widgets = {}
        for name, tab in self.tabs.items():
            text_widget = ctk.CTkTextbox(tab, wrap="word")
            text_widget.pack(fill="both", expand=True, padx=5, pady=5)
            self.text_widgets[name] = text_widget

        self.translation_results: Dict[str, Dict[str, str]] = {}
        self.current_file: Optional[str] = None

    def add_translation_result(self, file_name: str, results: Dict[str, str]):
        self.translation_results[file_name] = results
        self.update_file_selector()

    def update_file_selector(self):
        files = list(self.translation_results.keys())
        if not files:
            files = ["Немає файлів"]
        self.file_selector.configure(values=files)
        if files[0] != "Немає файлів":
            self.file_selector.set(files[0])
            self.show_translation(files[0])

    def show_translation(self, file_name: str):
        if file_name in self.translation_results:
            results = self.translation_results[file_name]
            for lang, text in results.items():
                if lang in self.text_widgets:
                    self.text_widgets[lang].delete("1.0", ctk.END)
                    self.text_widgets[lang].insert("1.0", text)

    def on_file_selected(self, file_name: str):
        if file_name != "Немає файлів":
            self.current_file = file_name
            self.show_translation(file_name)

    def clear(self):
        self.translation_results.clear()
        for text_widget in self.text_widgets.values():
            text_widget.delete("1.0", ctk.END)
        self.file_selector.configure(values=["Немає файлів"])
        self.file_selector.set("Немає файлів")