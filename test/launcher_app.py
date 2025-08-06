import customtkinter as ctk
from tkinter import messagebox
from tkinter import ttk
import threading
import psutil
from functools import partial

from minecraft_manager import MinecraftManager
from test.utils import generate_random_username, generate_random_uuid
from console import print_to_console
from config import MINECRAFT_DIRECTORY, DEFAULT_RAM

class MinecraftLauncherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Minecraft Launcher")
        self.geometry("900x700")
        self.resizable(True, True)

        # Инициализация
        self.minecraft_directory = MINECRAFT_DIRECTORY
        self.manager = MinecraftManager(self.minecraft_directory)

        self.version_var = ctk.StringVar()
        self.username_var = ctk.StringVar()
        self.uuid_var = ctk.StringVar()
        self.token_var = ctk.StringVar()
        self.ram_var = ctk.IntVar(value=DEFAULT_RAM)
        self.progress_var = ctk.DoubleVar()
        self.status_var = ctk.StringVar(value="Готов к работе")
        self.versions_data = []

        self.total_ram = psutil.virtual_memory().total // (1024 ** 3)
        self.ram_var.set(min(DEFAULT_RAM, self.total_ram // 2))

        self.install_thread = None

        self.create_widgets()
        threading.Thread(target=self.load_versions_list, daemon=True).start()

    def create_widgets(self):
            # Основной фрейм
            main_frame = ctk.CTkFrame(self)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Фрейм настроек
            settings_frame = ctk.CTkFrame(main_frame)
            settings_frame.pack(fill="x", padx=5, pady=5)
            
            # Версия Minecraft
            ctk.CTkLabel(settings_frame, text="Версия Minecraft:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
            self.version_combobox = ctk.CTkComboBox(
                settings_frame, 
                variable=self.version_var, 
                state="readonly",
                width=300
            )
            self.version_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.version_combobox.set("Загрузка версий...")
            
            # Кнопка обновления списка версий
            refresh_btn = ctk.CTkButton(
                settings_frame, 
                text="🔄", 
                width=40,
                command=self.refresh_versions
            )
            refresh_btn.grid(row=0, column=2, padx=5, pady=5)
            
            # Никнейм
            ctk.CTkLabel(settings_frame, text="Никнейм:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
            username_entry = ctk.CTkEntry(settings_frame, textvariable=self.username_var)
            username_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
            
            # UUID (необязательно)
            ctk.CTkLabel(settings_frame, text="UUID (необязательно):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
            uuid_entry = ctk.CTkEntry(settings_frame, textvariable=self.uuid_var)
            uuid_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
            
            # Access Token (необязательно)
            ctk.CTkLabel(settings_frame, text="Access Token (необязательно):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
            token_entry = ctk.CTkEntry(settings_frame, textvariable=self.token_var, show="*")
            token_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew", columnspan=2)
            
            # Выделяемая RAM
            ctk.CTkLabel(settings_frame, text=f"RAM (ГБ) (Доступно: {self.total_ram} ГБ):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
            ram_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
            ram_frame.grid(row=4, column=1, padx=0, pady=0, sticky="ew", columnspan=2)
            
            ram_slider = ctk.CTkSlider(
                ram_frame, 
                from_=1, 
                to=self.total_ram, 
                variable=self.ram_var, 
                number_of_steps=self.total_ram-1,
                width=200
            )
            ram_slider.pack(side="left", padx=(0, 10), pady=5)
            
            ram_label = ctk.CTkLabel(ram_frame, textvariable=self.ram_var, width=30)
            ram_label.pack(side="left", padx=0, pady=5)
            
            # Кнопки
            button_frame = ctk.CTkFrame(main_frame)
            button_frame.pack(fill="x", padx=5, pady=5)
            
            install_button = ctk.CTkButton(
                button_frame, 
                text="Установить", 
                command=self.start_installation_thread,
                fg_color="#2aa44f",
                hover_color="#207a3d"
            )
            install_button.pack(side="left", padx=5, pady=5, expand=True)
            
            launch_button = ctk.CTkButton(
                button_frame, 
                text="Запустить", 
                command=self.launch_minecraft,
                fg_color="#1a66ff",
                hover_color="#0052cc"
            )
            launch_button.pack(side="left", padx=5, pady=5, expand=True)
            
            # Прогресс бар и статус
            progress_frame = ctk.CTkFrame(main_frame)
            progress_frame.pack(fill="x", padx=5, pady=5)
            
            self.progress_bar = ttk.Progressbar(
                progress_frame, 
                variable=self.progress_var, 
                maximum=100,
                mode='determinate'
            )
            self.progress_bar.pack(fill="x", padx=5, pady=5)
            
            status_label = ctk.CTkLabel(progress_frame, textvariable=self.status_var)
            status_label.pack(fill="x", padx=5, pady=(0, 5))
            
            # Консольный вывод
            console_frame = ctk.CTkFrame(main_frame)
            console_frame.pack(fill="both", expand=True, padx=5, pady=5)
            
            self.console_text = ctk.CTkTextbox(console_frame, wrap="word")
            self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
            self.console_text.configure(state="disabled")

    def print_to_console(self, text: str):
        print_to_console(self.console_text, text)

    def load_versions_list(self):
        try:
            self.status_var.set("Получение списка версий...")
            self.print_to_console("Загрузка списка версий...")
            self.versions_data = self.manager.get_version_list()
            self.after(0, self.update_version_combobox)
            self.print_to_console(f"Загружено {len(self.versions_data)} версий")
            self.status_var.set("Готов к работе")
        except Exception as e:
            self.print_to_console(f"Ошибка: {e}")
            self.status_var.set("Ошибка загрузки")

    def update_version_combobox(self):
        if self.versions_data:
            display_versions = [v['display'] for v in self.versions_data]
            self.version_combobox.configure(values=display_versions)
            self.version_combobox.set(display_versions[0] if display_versions else "Нет версий")
        else:
            self.version_combobox.set("Не удалось загрузить")

    def refresh_versions(self):
        self.version_combobox.set("Обновление...")
        self.version_combobox.configure(state="disabled")
        threading.Thread(target=self.load_versions_list, daemon=True).start()

    def start_installation_thread(self):
        if self.install_thread and self.install_thread.is_alive():
            messagebox.showwarning("Внимание", "Установка уже идёт!")
            return
        self.install_thread = threading.Thread(target=self.install_minecraft, daemon=True)
        self.install_thread.start()

    def install_minecraft(self):
        selected = self.version_var.get()
        version_data = next((v for v in self.versions_data if v['display'] == selected), None)
        if not version_data:
            messagebox.showerror("Ошибка", "Выберите версию")
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
            self.after(0, partial(self.disable_buttons, True))
            self.manager.install_version(version_id, version_type, callback)
            self.print_to_console("Установка завершена!")
            self.after(0, lambda: messagebox.showinfo("Успех", "Minecraft установлен!"))
        except Exception as e:
            self.print_to_console(f"Ошибка: {e}")
            self.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.after(0, partial(self.disable_buttons, False))
            self.status_var.set("Готов к работе")

    def disable_buttons(self, state):
        # ... (остаётся как есть)
        pass

    def launch_minecraft(self):
        selected = self.version_var.get()
        username = self.username_var.get() or generate_random_username()
        uuid = self.uuid_var.get() or generate_random_uuid()
        token = self.token_var.get()
        ram = self.ram_var.get()

        version_data = next((v for v in self.versions_data if v['display'] == selected), None)
        if not version_data:
            messagebox.showerror("Ошибка", "Выберите версию")
            return

        version_id = version_data['id']
        version_type = version_data['type']

        options = {
            'username': username,
            'uuid': uuid,
            'token': token,
            'jvmArguments': [f"-Xmx{ram}G", "-Xms128m"],
            'gameDirectory': self.minecraft_directory
        }

        try:
            self.print_to_console("Запуск...")
            command = self.manager.get_launch_command(version_id, version_type, options)
            self.print_to_console(f"Команда: {' '.join(command)}")
            threading.Thread(target=self.run_minecraft_process, args=(command,), daemon=True).start()
        except Exception as e:
            self.print_to_console(f"Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))

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
            self.after(0, self.print_to_console, f"Процесс Minecraft завершился с кодом {process.returncode}")
        
        except Exception as e:
            self.after(0, self.print_to_console, f"Ошибка запуска Minecraft: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка запуска: {str(e)}"))