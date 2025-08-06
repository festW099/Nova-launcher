import json
import sys
import subprocess
import os
import psutil
import threading
import webbrowser
import tkinter as tk
from uuid import uuid1
from random_username.generate import generate_username
import customtkinter as ctk
from tkinter import messagebox, ttk
import minecraft_launcher_lib as mcl
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
        # Настройки фильтрации
        self.show_snapshots_var = ctk.BooleanVar(value=False)
        self.show_experimental_var = ctk.BooleanVar(value=False)
        self.show_modded_var = ctk.BooleanVar(value=True)
        self.versions_data = []
        self.installed_versions = []
        self.total_ram = psutil.virtual_memory().total // (1024 ** 3)
        self.ram_var.set(min(4, self.total_ram // 2))
        self.current_view = "splash"
        self.console_text = None  # Инициализируем как None
        self.install_thread = None
        # Показываем заставку
        self.show_splash_screen()
        # Проверка и установка пакетов
        self.check_required_packages()
        threading.Thread(target=self.load_data_async, daemon=True).start()

    def load_data_async(self):
        """Асинхронная загрузка списка версий"""
        self.update_status_splash("Загрузка списка версий...")
        try:
            all_versions = mcl.utils.get_version_list()
            versions_data = []
            for v in all_versions:
                version_id = v['id']
                version_type = v.get('type', 'unknown')
                if version_type == "snapshot" and not self.show_snapshots_var.get():
                    continue
                if version_type == "experimental" and not self.show_experimental_var.get():
                    continue
                versions_data.append({
                    'id': version_id,
                    'type': version_type,
                    'display': f"{version_id} ({version_type})"
                })

            if self.show_modded_var.get():
                self.add_forge_versions(versions_data)
                self.add_fabric_versions(versions_data)
                self.add_optifine_versions(versions_data)

            self.versions_data = versions_data
            self.installed_versions = self.get_installed_versions()

            # Переключаемся на экран игры
            if self.winfo_exists():
                self.after(0, self.show_play_screen)
        except Exception as e:
            if self.winfo_exists():
                self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {e}"))
                self.after(0, self.show_play_screen)

    def add_forge_versions(self, versions_data):
        try:
            forge_versions = mcl.forge.list_forge_versions()
            for version in forge_versions:
                if not any(v['id'] == f"forge:{version}" for v in versions_data):
                    versions_data.append({
                        'id': f"forge:{version}",
                        'type': 'forge',
                        'display': f"{version} (Forge)"
                    })
        except Exception as e:
            self.print_to_console(f"⚠️ Ошибка при загрузке Forge: {e}")

    def add_fabric_versions(self, versions_data):
        try:
            fabric_mc_versions = mcl.fabric.get_all_minecraft_versions()
            for entry in fabric_mc_versions:
                mc_version = entry['version']
                is_stable = entry['stable']
                if not is_stable and not self.show_experimental_var.get():
                    continue
                # Мы не знаем точное имя версии (оно будет после установки), но храним тип
                display_name = f"{mc_version} (Fabric)"
                if not any(v['id'] == f"fabric:{mc_version}" for v in versions_data):
                    versions_data.append({
                        'id': f"fabric:{mc_version}",
                        'type': 'fabric',
                        'display': display_name
                    })
        except Exception as e:
            self.print_to_console(f"⚠️ Ошибка при загрузке Fabric: {e}")

    def add_optifine_versions(self, versions_data):
        try:
            optifine_versions = mcl.optifine.get_optifine_versions()
            for version in optifine_versions:
                mc_version = version["mcVersion"]
                type_ = version["type"]
                patch = version["patch"]
                version_id = f"{mc_version}-OptiFine_{type_}_{patch}"
                full_id = f"optifine:{version_id}"
                display_name = f"{version_id} (OptiFine)"
                if not any(v['id'] == full_id for v in versions_data):
                    versions_data.append({
                        'id': full_id,
                        'type': 'optifine',
                        'display': display_name
                    })
        except Exception as e:
            self.print_to_console(f"⚠️ Ошибка при загрузке OptiFine: {e}")

    def get_installed_versions(self):
        versions_path = os.path.join(self.minecraft_directory, "versions")
        if not os.path.exists(versions_path):
            return []
        installed = []
        for d in os.listdir(versions_path):
            json_path = os.path.join(versions_path, d, f"{d}.json")
            if os.path.exists(json_path):
                installed.append(d)
        return sorted(installed, reverse=True)

    # === ЭКРАНЫ ===
    def show_splash_screen(self):
        self.current_view = "splash"
        self.clear_window()
        splash_frame = ctk.CTkFrame(self)
        splash_frame.pack(fill="both", expand=True, padx=20, pady=20)
        logo = ctk.CTkLabel(splash_frame, text="🎮", font=("Arial", 80))
        logo.pack(pady=40)
        title = ctk.CTkLabel(splash_frame, text="Загрузка лаунчера...", font=("Arial", 24, "bold"))
        title.pack(pady=10)
        self.splash_status = ctk.CTkLabel(splash_frame, text="Инициализация...", font=("Arial", 14))
        self.splash_status.pack(pady=5)
        self.splash_progress = ttk.Progressbar(splash_frame, mode="indeterminate", length=300)
        self.splash_progress.pack(pady=20)
        self.splash_progress.start()

    def update_status_splash(self, text):
        if hasattr(self, 'splash_status') and self.splash_status is not None:
            self.splash_status.configure(text=text)

    def show_play_screen(self):
        if self.current_view == "splash":
            if hasattr(self, 'splash_progress'):
                self.splash_progress.stop()
        self.current_view = "play"
        self.clear_window()
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)
        title_label = ctk.CTkLabel(header_frame, text="Играть", font=("Arial", 20, "bold"))
        title_label.pack(side="left")
        settings_btn = ctk.CTkButton(
            header_frame,
            text="⚙️ Выбор версии",
            width=120,
            command=self.show_settings_screen
        )
        settings_btn.pack(side="right")

        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(list_frame, text="Выберите версию для запуска:", font=("Arial", 14)).pack(anchor="w", padx=10, pady=(10, 5))

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
            ctk.CTkLabel(
                scrollable_frame,
                text="Нет установленных версий. Перейдите в Выбор версии для установки.",
                text_color="gray",
                wraplength=500
            ).pack(pady=30)
        else:
            for version in self.installed_versions:
                btn = ctk.CTkButton(
                    scrollable_frame,
                    text=version,
                    height=45,
                    font=("Arial", 14),
                    command=partial(self.launch_with_version, version)
                )
                btn.pack(fill="x", padx=20, pady=6)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(input_frame, text="Никнейм:").grid(row=0, column=0, padx=10, sticky="w")
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
        if not self.winfo_exists():
            return
        username = self.username_var.get() or generate_username()[0]
        uuid = self.uuid_var.get() or str(uuid1())
        ram = self.ram_var.get()
        options = {
            'username': username,
            'uuid': uuid,
            'token': self.token_var.get(),
            'jvmArguments': [f"-Xmx{ram}G", "-Xms128m"],
            'gameDirectory': self.minecraft_directory
        }
        try:
            command = mcl.command.get_minecraft_command(version_id, self.minecraft_directory, options)
            self.print_to_console(f"🎮 Запуск: {version_id} ({username})")
            threading.Thread(target=self.run_minecraft_process, args=(command,), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить: {e}")

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
                if not self.winfo_exists():
                    break
                self.after(0, self.print_to_console, line.strip())
            process.wait()
        except Exception as e:
            if self.winfo_exists():
                self.after(0, self.print_to_console, f"❌ Ошибка: {e}")

    def show_settings_screen(self):
        self.current_view = "settings"
        self.clear_window()
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header_frame, text="Выбор версии", font=("Arial", 20, "bold")).pack(side="left")
        back_btn = ctk.CTkButton(
            header_frame,
            text="⬅️ Назад",
            width=100,
            command=self.show_play_screen
        )
        back_btn.pack(side="right")

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        filter_frame = ctk.CTkFrame(main_frame)
        filter_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkCheckBox(filter_frame, text="Показывать снепшоты", variable=self.show_snapshots_var).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkCheckBox(filter_frame, text="Показывать экспериментальные", variable=self.show_experimental_var).grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkCheckBox(filter_frame, text="Показывать модифицированные (Forge/Fabric/OptiFine)", variable=self.show_modded_var).grid(row=2, column=0, sticky="w", padx=10, pady=5)

        search_frame = ctk.CTkFrame(main_frame)
        search_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(search_frame, text="Поиск версии:").grid(row=0, column=0, padx=5, sticky="w")
        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=200)
        search_entry.grid(row=0, column=1, padx=5)
        search_entry.bind("<KeyRelease>", self.filter_versions_list)

        btn_frame = ctk.CTkFrame(search_frame)
        btn_frame.grid(row=0, column=2, padx=5)
        ctk.CTkButton(
            btn_frame,
            text="🔧 Выбрать",
            command=self.open_version_selector
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_frame,
            text="⚡ OptiFine",
            command=self.open_optifine_selector
        ).pack(side="left", padx=2)

        self.selected_version_label = ctk.CTkLabel(search_frame, text="Ничего не выбрано", text_color="gray")
        self.selected_version_label.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        install_button = ctk.CTkButton(
            main_frame,
            text="Установить выбранную версию",
            command=self.start_installation_thread,
            fg_color="#2aa44f",
            hover_color="#207a3d"
        )
        install_button.pack(pady=10)

        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", padx=5, pady=5)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        status_label = ctk.CTkLabel(progress_frame, textvariable=self.status_var)
        status_label.pack(fill="x", padx=5, pady=(0, 5))

        # Кнопка открытия папки mods
        mods_button_frame = ctk.CTkFrame(main_frame)
        mods_button_frame.pack(fill="x", padx=5, pady=5)

        def open_mods_folder():
            mods_path = os.path.join(self.minecraft_directory, "mods")
            if not os.path.exists(mods_path):
                os.makedirs(mods_path, exist_ok=True)
            try:
                if sys.platform == "win32":
                    os.startfile(mods_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", mods_path])
                else:
                    subprocess.run(["xdg-open", mods_path])
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть папку mods: {e}")

        mods_btn = ctk.CTkButton(
            mods_button_frame,
            text="📂 Открыть папку mods",
            command=open_mods_folder
        )
        if not os.path.exists(os.path.join(self.minecraft_directory, "mods")):
            mods_btn.configure(state="disabled", text_color_disabled="gray")
        mods_btn.pack(pady=5)

        console_frame = ctk.CTkFrame(main_frame)
        console_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.console_text = ctk.CTkTextbox(console_frame, wrap="word", height=150)
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.console_text.configure(state="disabled")

        self.refresh_versions()

    def refresh_versions(self):
        threading.Thread(target=self.load_versions_list, daemon=True).start()

    def load_versions_list(self):
        try:
            self.status_var.set("Получение списка версий...")
            all_versions = mcl.utils.get_version_list()
            versions_data = []
            for v in all_versions:
                version_id = v['id']
                version_type = v.get('type', 'unknown')
                if version_type == "snapshot" and not self.show_snapshots_var.get():
                    continue
                if version_type == "experimental" and not self.show_experimental_var.get():
                    continue
                versions_data.append({
                    'id': version_id,
                    'type': version_type,
                    'display': f"{version_id} ({version_type})"
                })

            if self.show_modded_var.get():
                self.add_forge_versions(versions_data)
                self.add_fabric_versions(versions_data)
                self.add_optifine_versions(versions_data)

            self.versions_data = versions_data
            self.filtered_versions = versions_data.copy()

            if self.winfo_exists():
                self.after(0, self.update_selected_label)
                self.status_var.set("Готово")
        except Exception as e:
            if self.winfo_exists():
                self.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось загрузить версии: {e}"))

    def update_selected_label(self):
        if hasattr(self, 'selected_version') and self.selected_version:
            self.selected_version_label.configure(text=f"Выбрано: {self.selected_version['display']}", text_color="lightblue")
        else:
            self.selected_version_label.configure(text="Ничего не выбрано", text_color="gray")

    def open_version_selector(self):
        selector_window = ctk.CTkToplevel(self)
        selector_window.title("Выберите версию")
        selector_window.geometry("500x500")
        selector_window.transient(self)
        selector_window.grab_set()

        search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(selector_window, placeholder_text="Поиск...", textvariable=search_var)
        search_entry.pack(fill="x", padx=10, pady=10)
        search_entry.bind("<KeyRelease>", lambda e: self.filter_versions_in_window(search_var.get(), listbox, listbox_items))

        listbox_frame = ctk.CTkFrame(selector_window)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)

        listbox = tk.Listbox(listbox_frame, font=("Arial", 12), bg="#2b2b2b", fg="white", selectmode="single", bd=0, highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(listbox_frame, orientation="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        listbox_items = []
        for v in self.versions_data:
            listbox.insert("end", v['display'])
            listbox_items.append(v)

        def on_select():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                self.selected_version = listbox_items[index]
                self.version_var.set(self.selected_version['id'])
                self.update_selected_label()
                selector_window.destroy()

        select_btn = ctk.CTkButton(selector_window, text="Выбрать", command=on_select)
        select_btn.pack(pady=10)
        selector_window.focus()

    def open_optifine_selector(self):
        selector_window = ctk.CTkToplevel(self)
        selector_window.title("Выберите OptiFine")
        selector_window.geometry("500x500")
        selector_window.transient(self)
        selector_window.grab_set()
        ctk.CTkLabel(selector_window, text="Выберите версию OptiFine", font=("Arial", 16)).pack(pady=10)

        try:
            optifine_versions = mcl.optifine.get_optifine_versions()
        except Exception as e:
            optifine_versions = []
            self.print_to_console(f"❌ Не удалось загрузить OptiFine версии: {e}")

        if not optifine_versions:
            ctk.CTkLabel(selector_window, text="Не удалось загрузить версии OptiFine.", text_color="red").pack(pady=20)
            ctk.CTkButton(selector_window, text="Закрыть", command=selector_window.destroy).pack(pady=10)
            return

        listbox_frame = ctk.CTkFrame(selector_window)
        listbox_frame.pack(fill="both", expand=True, padx=10, pady=5)

        listbox = tk.Listbox(listbox_frame, font=("Arial", 12), bg="#2b2b2b", fg="white", selectmode="single", bd=0, highlightthickness=0)
        scrollbar = ctk.CTkScrollbar(listbox_frame, orientation="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for v in optifine_versions:
            version_id = f"{v['mcVersion']}-OptiFine_{v['type']}_{v['patch']}"
            listbox.insert("end", version_id)

        def on_select():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Внимание", "Выберите версию OptiFine!")
                return
            index = selection[0]
            selected = optifine_versions[index]
            version_id = f"{selected['mcVersion']}-OptiFine_{selected['type']}_{selected['patch']}"
            full_id = f"optifine:{version_id}"
            self.selected_version = {
                'id': full_id,
                'type': 'optifine',
                'display': f"{version_id} (OptiFine)"
            }
            self.version_var.set(version_id)
            self.update_selected_label()
            selector_window.destroy()

        ctk.CTkButton(selector_window, text="Выбрать", command=on_select).pack(pady=10)
        selector_window.focus()

    def filter_versions_in_window(self, search_term, listbox_widget, items_ref):
        listbox_widget.delete(0, "end")
        items_ref.clear()
        for v in self.versions_data:
            if search_term.lower() in v['display'].lower():
                listbox_widget.insert("end", v['display'])
                items_ref.append(v)

    def filter_versions_list(self, event=None):
        pass

    def start_installation_thread(self):
        if hasattr(self, 'install_thread') and self.install_thread and self.install_thread.is_alive():
            messagebox.showwarning("Внимание", "Установка уже выполняется!")
            return
        if not hasattr(self, 'selected_version') or not self.selected_version:
            messagebox.showwarning("Внимание", "Сначала выберите версию!")
            return
        self.install_thread = threading.Thread(target=self.install_minecraft, daemon=True)
        self.install_thread.start()

    def install_minecraft(self):
        version_data = self.selected_version
        version_id = version_data['id']
        version_type = version_data['type']

        self.max_value = 100
        self.current_progress = 0

        def callback_set_status(text):
            if self.winfo_exists():
                self.status_var.set(text)
                self.after(0, self.print_to_console, text)

        def callback_set_progress(value):
            if self.winfo_exists():
                self.current_progress = value
                self.progress_var.set((value / max(self.max_value, 1)) * 100)

        def callback_set_max(value):
            if self.winfo_exists():
                self.max_value = value

        callback = {
            "setStatus": callback_set_status,
            "setProgress": callback_set_progress,
            "setMax": callback_set_max
        }

        try:
            if self.winfo_exists():
                self.after(0, lambda: self.disable_buttons(True))
            self.print_to_console(f"📥 Начало установки: {version_id} ({version_type})")

            if version_type == "forge":
                forge_version = version_id.split(":", 1)[1]
                mcl.forge.install_forge_version(forge_version, self.minecraft_directory, callback=callback)
            elif version_type == "fabric":
                mc_version = version_id.split(":", 1)[1]
                mcl.fabric.install_fabric(mc_version, self.minecraft_directory, callback=callback)
            elif version_type == "optifine":
                mc_version = version_id.split(":", 1)[1]
                mcl.install.install_minecraft_version(mc_version, self.minecraft_directory, callback=callback)
            else:
                mcl.install.install_minecraft_version(version_id, self.minecraft_directory, callback=callback)

            # Обновляем список установленных версий
            self.installed_versions = self.get_installed_versions()
            if self.winfo_exists():
                self.after(0, lambda: messagebox.showinfo("Успех", "Установка завершена!"))
                self.print_to_console("✅ Установка завершена.")
        except Exception as e:
            if self.winfo_exists():
                self.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка установки: {e}"))
                self.print_to_console(f"❌ Ошибка: {e}")
        finally:
            if self.winfo_exists():
                self.after(0, lambda: self.disable_buttons(False))
                self.status_var.set("Готов к работе")

    def disable_buttons(self, state):
        if not self.winfo_exists():
            return
        for widget in self.winfo_children():
            if isinstance(widget, (ctk.CTkButton, ctk.CTkComboBox, ctk.CTkEntry)):
                try:
                    widget.configure(state="disabled" if state else "normal")
                except tk.TclError:
                    pass

    def print_to_console(self, text):
        if not self.winfo_exists() or not hasattr(self, 'console_text') or self.console_text is None:
            return
        try:
            self.console_text.configure(state="normal")
            self.console_text.insert("end", text + "\n")
            self.console_text.see("end")
            self.console_text.configure(state="disabled")
        except tk.TclError:
            pass

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.console_text = None
        self.splash_progress = None
        self.splash_status = None

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
                    if self.winfo_exists():
                        messagebox.showerror("Ошибка", f"Не удалось установить {package}: {e}")


if __name__ == "__main__":
    app = MinecraftLauncherApp()
    app.mainloop()