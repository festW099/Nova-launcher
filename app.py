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
        self.versions_data = []
        self.install_thread = None
        
        # Получаем доступную RAM
        self.total_ram = psutil.virtual_memory().total // (1024 ** 3)
        self.ram_var.set(min(4, self.total_ram // 2))  # Устанавливаем разумное значение по умолчанию
        
        # Создание интерфейса
        self.create_widgets()
        
        # Загрузка списка версий в фоновом режиме
        threading.Thread(target=self.load_versions_list, daemon=True).start()
        
        # Проверка и установка необходимых пакетов
        self.check_required_packages()
    
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
    
    def print_to_console(self, text):
        self.console_text.configure(state="normal")
        self.console_text.insert("end", text + "\n")
        self.console_text.see("end")
        self.console_text.configure(state="disabled")
    
    def load_versions_list(self):
        try:
            self.status_var.set("Получение списка версий...")
            self.print_to_console("Загрузка списка версий Minecraft...")
            
            # Получаем список всех версий
            all_versions = mcl.utils.get_version_list()
            
            # Собираем все версии с указанием типа
            versions_data = []
            for v in all_versions:
                version_type = v.get('type', 'unknown')
                versions_data.append({
                    'id': v['id'],
                    'type': version_type,
                    'display': f"{v['id']} ({version_type})"
                })
            
            # Добавляем Forge и Fabric версии
            self.add_forge_versions(versions_data)
            self.add_fabric_versions(versions_data)
            
            
            # Сохраняем данные
            self.versions_data = versions_data
            
            # Обновляем комбобокс
            self.after(0, self.update_version_combobox)
            
            self.print_to_console(f"Загружено {len(versions_data)} версий")
            self.status_var.set("Готов к работе")
            
        except Exception as e:
            self.print_to_console(f"Ошибка при загрузке версий: {str(e)}")
            self.status_var.set("Ошибка загрузки версий")
            self.version_combobox.set("Ошибка загрузки")
    
    def add_forge_versions(self, versions_data):
        try:
            forge_versions = mcl.forge.list_forge_versions()
            for version in forge_versions:
                versions_data.append({
                    'id': version,
                    'type': 'forge',
                    'display': f"{version} (forge)"
                })
        except Exception as e:
            self.print_to_console(f"Ошибка загрузки Forge версий: {str(e)}")
    
    def add_fabric_versions(self, versions_data):
        try:
            fabric_versions = mcl.fabric.get_all_minecraft_versions()
            for version in fabric_versions:
                if version['stable']:
                    versions_data.append({
                        'id': version['version'],
                        'type': 'fabric',
                        'display': f"{version['version']} (fabric)"
                    })
        except Exception as e:
            self.print_to_console(f"Ошибка загрузки Fabric версий: {str(e)}")
    
    def update_version_combobox(self):
        if self.versions_data:
            display_versions = [v['display'] for v in self.versions_data]
            self.version_combobox.configure(values=display_versions)
            self.version_combobox.set(display_versions[0])
        else:
            self.version_combobox.set("Не удалось загрузить версии")
    
    def refresh_versions(self):
        self.version_combobox.set("Обновление...")
        self.version_combobox.configure(state="disabled")
        threading.Thread(target=self.load_versions_list, daemon=True).start()
    
    def check_required_packages(self):
        required_packages = ["random-username", "minecraft_launcher_lib", "psutil"]
        
        def is_package_installed(package):
            try:
                subprocess.check_output([sys.executable, "-m", "pip", "show", package])
                return True
            except subprocess.CalledProcessError:
                return False
        
        for package in required_packages:
            if not is_package_installed(package):
                self.print_to_console(f"Установка необходимого пакета: {package}")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                    self.print_to_console(f"Пакет {package} успешно установлен")
                except subprocess.CalledProcessError:
                    self.print_to_console(f"Не удалось установить {package}")
                    messagebox.showerror("Ошибка", f"Не удалось установить необходимый пакет: {package}")
    
    def start_installation_thread(self):
        if self.install_thread and self.install_thread.is_alive():
            messagebox.showwarning("Внимание", "Установка уже выполняется!")
            return
        
        self.install_thread = threading.Thread(target=self.install_minecraft, daemon=True)
        self.install_thread.start()
    
    def install_minecraft(self):
        selected_version = self.version_var.get()
        if not selected_version or selected_version == "Загрузка версий..." or selected_version == "Ошибка загрузки":
            messagebox.showerror("Ошибка", "Пожалуйста, выберите версию Minecraft")
            return
        
        # Находим полные данные о выбранной версии
        version_data = next((v for v in self.versions_data if v['display'] == selected_version), None)
        if not version_data:
            messagebox.showerror("Ошибка", "Не удалось определить выбранную версию")
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
            # Блокируем кнопки во время установки
            self.after(0, partial(self.disable_buttons, True))
            
            if version_type == "forge":
                self.print_to_console(f"Установка Forge версии: {version_id}")
                mcl.forge.install_forge_version(version_id, self.minecraft_directory, callback=callback)
            
            elif version_type == "fabric":
                self.print_to_console(f"Установка Fabric для версии: {version_id}")
                mcl.fabric.install_fabric(version_id, self.minecraft_directory, callback=callback)
            
            else:
                self.print_to_console(f"Установка версии Minecraft: {version_id}")
                mcl.install.install_minecraft_version(
                    versionid=version_id, 
                    minecraft_directory=self.minecraft_directory, 
                    callback=callback
                )
            
            self.print_to_console("Установка успешно завершена!")
            self.after(0, lambda: messagebox.showinfo("Успех", "Minecraft успешно установлен!"))
        
        except Exception as e:
            self.print_to_console(f"Ошибка при установке: {str(e)}")
            self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка установки: {str(e)}"))
        
        finally:
            # Разблокируем кнопки после установки
            self.after(0, partial(self.disable_buttons, False))
            self.status_var.set("Готов к работе")
    
    def disable_buttons(self, state):
        widgets = [
            self.version_combobox,
            *self.winfo_children()[0].winfo_children()[1].winfo_children()  # Все элементы settings_frame
        ]
        
        for widget in widgets:
            if isinstance(widget, (ctk.CTkButton, ctk.CTkComboBox, ctk.CTkOptionMenu, ctk.CTkEntry)):
                widget.configure(state="disabled" if state else "normal")
    
    def launch_minecraft(self):
        selected_version = self.version_var.get()
        username = self.username_var.get()
        uuid = self.uuid_var.get()
        token = self.token_var.get()
        ram = self.ram_var.get()
        
        if not selected_version or selected_version == "Загрузка версий..." or selected_version == "Ошибка загрузки":
            messagebox.showerror("Ошибка", "Пожалуйста, выберите версию Minecraft")
            return
        
        if not username:
            username = generate_username()[0]
            self.username_var.set(username)
        
        if not uuid:
            uuid = str(uuid1())
            self.uuid_var.set(uuid)
        
        # Находим полные данные о выбранной версии
        version_data = next((v for v in self.versions_data if v['display'] == selected_version), None)
        if not version_data:
            messagebox.showerror("Ошибка", "Не удалось определить выбранную версию")
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
            self.print_to_console("Запуск Minecraft...")
            
            if version_type == "fabric":
                fabric_loader = mcl.fabric.get_latest_loader_version()
                version_name = f"fabric-loader-{fabric_loader}-{version_id}"
                command = mcl.command.get_minecraft_command(
                    version=version_name, 
                    minecraft_directory=self.minecraft_directory,
                    options=options)
            
            elif version_type == "forge":
                version_name = version_id  # Forge версии уже имеют правильный формат
                command = mcl.command.get_minecraft_command(
                    version=version_name, 
                    minecraft_directory=self.minecraft_directory,
                    options=options)
            
            else:
                command = mcl.command.get_minecraft_command(
                    version=version_id, 
                    minecraft_directory=self.minecraft_directory,
                    options=options)
            
            self.print_to_console(f"Команда запуска: {' '.join(command)}")
            
            # Запуск в отдельном потоке
            threading.Thread(target=self.run_minecraft_process, args=(command,), daemon=True).start()
        
        except Exception as e:
            self.print_to_console(f"Ошибка при подготовке запуска: {str(e)}")
            messagebox.showerror("Ошибка", f"Ошибка запуска: {str(e)}")
    
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

if __name__ == "__main__":
    app = MinecraftLauncherApp()
    app.mainloop()