import json
import sys
import minecraft_launcher_lib as mcl
import subprocess
from uuid import uuid1
from random_username.generate import generate_username
import threading
import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import os
import psutil
from functools import partial

# Настройка темы CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class MinecraftLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Minecraft Launcher")
        self.geometry("900x700")
        self.resizable(True, True)

        # Инициализация переменных
        self.minecraft_directory = ".minecraft"
        self.version_var = ctk.StringVar()
        self.username_var = ctk.StringVar()
        self.uuid_var = ctk.StringVar()
        self.token_var = ctk.StringVar()
        self.ram_var = ctk.IntVar(value=4)
        self.progress_var = ctk.DoubleVar()
        self.status_var = ctk.StringVar(value="Готов к работе")
        self.versions_data = []  # Все доступные версии (для установки)
        self.installed_versions = []  # Только установленные
        self.total_ram = psutil.virtual_memory().total // (1024 ** 3)
        self.ram_var.set(min(4, self.total_ram // 2))

        # Текущее окно: "play" или "settings"
        self.current_view = "splash"

        # Показываем splash screen
        self.show_splash_screen()

        # Проверка пакетов и загрузка данных
        self.check_required_packages()
        threading.Thread(target=self.load_data_async, daemon=True).start()

    def load_data_async(self):
        """Асинхронная загрузка списка версий и установленных версий"""
        self.update_status_splash("Загрузка списка версий...")
        try:
            all_versions = mcl.utils.get_version_list()
            versions_data = []
            for v in all_versions:
                version_type = v.get('type', 'unknown')
                versions_data.append({
                    'id': v['id'],
                    'type': version_type,
                    'display': f"{v['id']} ({version_type})"
                })

            # Добавляем Forge и Fabric
            self.add_forge_versions(versions_data)
            self.add_fabric_versions(versions_data)
            self.versions_data = versions_data

            # Получаем установленные версии
            self.installed_versions = self.get_installed_versions()

            # Переключаемся на главное окно
            self.after(0, self.show_play_screen)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {e}"))
            self.after(0, self.show_play_screen)

    def add_forge_versions(self, versions_data):
        try:
            forge_versions = mcl.forge.list_forge_versions()
            for version in forge_versions:
                if version in [v['id'] for v in versions_data]:
                    continue
                versions_data.append({
                    'id': version,
                    'type': 'forge',
                    'display': f"{version} (forge)"
                })
        except Exception as e:
            print(f"Ошибка Forge: {e}")

    def add_fabric_versions(self, versions_data):
        try:
            fabric_versions = mcl.fabric.get_all_minecraft_versions()
            for version in fabric_versions:
                ver_id = version['version']
                if any(v['id'] == ver_id for v in versions_data):
                    continue
                if version['stable']:
                    versions_data.append({
                        'id': ver_id,
                        'type': 'fabric',
                        'display': f"{ver_id} (fabric)"
                    })
        except Exception as e:
            print(f"Ошибка Fabric: {e}")

    def get_installed_versions(self):
        """Получаем список установленных версий из папки versions"""
        versions_path = os.path.join(self.minecraft_directory, "versions")
        if not os.path.exists(versions_path):
            return []
        installed = []
        for d in os.listdir(versions_path):
            json_path = os.path.join(versions_path, d, f"{d}.json")
            if os.path.exists(json_path):
                installed.append(d)
        return sorted(installed, reverse=True)  # Новые версии сверху

    # === ЭКРАНЫ ===

    def show_splash_screen(self):
        self.current_view = "splash"
        self.clear_window()

        splash_frame = ctk.CTkFrame(self)
        splash_frame.pack(fill="both", expand=True)

        logo = ctk.CTkLabel(splash_frame, text="🎮", font=("Arial", 60))
        logo.pack(pady=50)

        title = ctk.CTkLabel(splash_frame, text="Загрузка лаунчера...", font=("Arial", 24))
        title.pack(pady=10)

        self.splash_status = ctk.CTkLabel(splash_frame, text="Инициализация...", font=("Arial", 14))
        self.splash_status.pack(pady=5)

        self.splash_progress = ttk.Progressbar(splash_frame, mode="indeterminate", length=300)
        self.splash_progress.pack(pady=20)
        self.splash_progress.start()

    def update_status_splash(self, text):
        if self.current_view == "splash":
            self.splash_status.configure(text=text)

    def show_play_screen(self):
        if self.current_view == "splash":
            self.splash_progress.stop()
        self.current_view = "play"
        self.clear_window()

        # Заголовок
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)

        title_label = ctk.CTkLabel(header_frame, text="Играть", font=("Arial", 20, "bold"))
        title_label.pack(side="left")

        settings_btn = ctk.CTkButton(
            header_frame,
            text="⚙️ Настройки",
            width=120,
            command=self.show_settings_screen
        )
        settings_btn.pack(side="right")

        # Список установленных версий
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(list_frame, text="Выберите версию для запуска:", font=("Arial", 14)).pack(anchor="w", padx=10, pady=(10, 5))

        # Скролл-фрейм для версий
        canvas = ctk.CTkCanvas(list_frame, bg="#2b2b2b", highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=canvas.yview)
        scrollable_frame = ctk.CTkFrame(canvas, fg_color="transparent")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        if not self.installed_versions:
            ctk.CTkLabel(scrollable_frame, text="Нет установленных версий. Перейдите в Настройки для установки.", text_color="gray").pack(pady=20)
        else:
            for version in self.installed_versions:
                btn = ctk.CTkButton(
                    scrollable_frame,
                    text=version,
                    height=40,
                    font=("Arial", 14),
                    command=partial(self.launch_with_version, version)
                )
                btn.pack(fill="x", padx=20, pady=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Поля ввода
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(input_frame, text="Никнейм:").grid(row=0, column=0, padx=5, sticky="w")
        ctk.CTkEntry(input_frame, textvariable=self.username_var, width=200).grid(row=0, column=1, padx=5)

        ram_label = ctk.CTkLabel(input_frame, text=f"RAM: {self.ram_var.get()} ГБ")
        ram_label.grid(row=0, column=2, padx=20)

        ctk.CTkSlider(
            input_frame,
            from_=1,
            to=self.total_ram,
            variable=self.ram_var,
            width=150,
            command=lambda v: ram_label.configure(text=f"RAM: {int(float(v))} ГБ")
        ).grid(row=0, column=3, padx=5)

    def launch_with_version(self, version_id):
        username = self.username_var.get() or generate_username()[0]
        uuid = self.uuid_var.get() or str(uuid1())
        ram = self.ram_var.get()

        # Определяем тип версии (Forge/Fabric/обычная)
        version_type = "release"
        if "forge" in version_id:
            version_type = "forge"
        elif "fabric" in version_id:
            version_type = "fabric"

        options = {
            'username': username,
            'uuid': uuid,
            'token': self.token_var.get(),
            'jvmArguments': [f"-Xmx{ram}G", "-Xms128m"],
            'gameDirectory': self.minecraft_directory
        }

        try:
            command = mcl.command.get_minecraft_command(
                version=version_id,
                minecraft_directory=self.minecraft_directory,
                options=options
            )
            self.print_to_console(f"Запуск: {version_id}")
            threading.Thread(target=self.run_minecraft_process, args=(command,), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить: {e}")

    def show_settings_screen(self):
        self.current_view = "settings"
        self.clear_window()

        # Заголовок
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(header_frame, text="Настройки", font=("Arial", 20, "bold")).pack(side="left")

        back_btn = ctk.CTkButton(
            header_frame,
            text="⬅️ Назад",
            width=100,
            command=self.show_play_screen
        )
        back_btn.pack(side="right")

        # Основной фрейм
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Настройки установки
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(settings_frame, text="Версия для установки:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.version_combobox = ctk.CTkComboBox(
            settings_frame,
            variable=self.version_var,
            state="readonly",
            width=300
        )
        self.version_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.version_combobox.set("Загрузка версий...")

        refresh_btn = ctk.CTkButton(settings_frame, text="🔄", width=40, command=self.refresh_versions)
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # Кнопка установки
        install_button = ctk.CTkButton(
            settings_frame,
            text="Установить",
            command=self.start_installation_thread,
            fg_color="#2aa44f",
            hover_color="#207a3d"
        )
        install_button.grid(row=1, column=0, columnspan=3, pady=10)

        # Прогресс и статус
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", padx=5, pady=5)

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        status_label = ctk.CTkLabel(progress_frame, textvariable=self.status_var)
        status_label.pack(fill="x", padx=5, pady=(0, 5))

        # Консоль
        console_frame = ctk.CTkFrame(main_frame)
        console_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.console_text = ctk.CTkTextbox(console_frame, wrap="word", height=150)
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.console_text.configure(state="disabled")

        # Обновляем список версий
        if self.versions_data:
            self.update_version_combobox()

    def refresh_versions(self):
        self.version_combobox.set("Обновление...")
        threading.Thread(target=self.load_versions_list, daemon=True).start()

    def load_versions_list(self):
        try:
            self.status_var.set("Получение списка версий...")
            all_versions = mcl.utils.get_version_list()
            versions_data = []
            for v in all_versions:
                version_type = v.get('type', 'unknown')
                versions_data.append({
                    'id': v['id'],
                    'type': version_type,
                    'display': f"{v['id']} ({version_type})"
                })
            self.add_forge_versions(versions_data)
            self.add_fabric_versions(versions_data)
            self.versions_data = versions_data
            self.after(0, self.update_version_combobox)
            self.status_var.set("Готово")
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось загрузить версии: {e}"))

    def update_version_combobox(self):
        if self.versions_data:
            display_versions = [v['display'] for v in self.versions_data]
            self.version_combobox.configure(values=display_versions)
            self.version_combobox.set(display_versions[0] if display_versions else "Нет доступных версий")
        else:
            self.version_combobox.set("Не удалось загрузить")

    def start_installation_thread(self):
        if hasattr(self, 'install_thread') and self.install_thread and self.install_thread.is_alive():
            messagebox.showwarning("Внимание", "Установка уже выполняется!")
            return
        self.install_thread = threading.Thread(target=self.install_minecraft, daemon=True)
        self.install_thread.start()

    def install_minecraft(self):
        selected_display = self.version_var.get()
        version_data = next((v for v in self.versions_data if v['display'] == selected_display), None)
        if not version_data:
            self.after(0, lambda: messagebox.showerror("Ошибка", "Выберите версию"))
            return

        version_id = version_data['id']
        version_type = version_data['type']

        self.max_value = 100
        self.current_progress = 0

        def callback_set_status(text):
            self.status_var.set(text)
            self.print_to_console(text)

        def callback_set_progress(value):
            self.current_progress = value
            self.progress_var.set((value / self.max_value) * 100)

        def callback_set_max(value):
            self.max_value = value

        callback = {
            "setStatus": callback_set_status,
            "setProgress": callback_set_progress,
            "setMax": callback_set_max
        }

        try:
            self.after(0, lambda: self.disable_buttons(True))
            if version_type == "forge":
                mcl.forge.install_forge_version(version_id, self.minecraft_directory, callback=callback)
            elif version_type == "fabric":
                mcl.fabric.install_fabric(version_id, self.minecraft_directory, callback=callback)
            else:
                mcl.install.install_minecraft_version(version_id, self.minecraft_directory, callback=callback)

            # Обновляем список установленных версий
            self.installed_versions = self.get_installed_versions()

            self.after(0, lambda: messagebox.showinfo("Успех", "Установка завершена!"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка установки: {e}"))
        finally:
            self.after(0, lambda: self.disable_buttons(False))
            self.status_var.set("Готов к работе")

    def disable_buttons(self, state):
        widgets = self.winfo_children()
        for widget in widgets:
            if isinstance(widget, (ctk.CTkButton, ctk.CTkComboBox, ctk.CTkEntry)):
                widget.configure(state="disabled" if state else "normal")

    def print_to_console(self, text):
        if hasattr(self, 'console_text'):
            self.console_text.configure(state="normal")
            self.console_text.insert("end", text + "\n")
            self.console_text.see("end")
            self.console_text.configure(state="disabled")

    def run_minecraft_process(self, command):
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in process.stdout:
                self.after(0, self.print_to_console, line.strip())
            process.wait()
        except Exception as e:
            self.after(0, self.print_to_console, f"Ошибка: {e}")

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

    def check_required_packages(self):
        required_packages = ["random-username", "minecraft_launcher_lib", "psutil"]
        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                self.update_status_splash(f"Установка {package}...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось установить {package}: {e}")


if __name__ == "__main__":
    app = MinecraftLauncherApp()
    app.mainloop()