import customtkinter as ctk

def print_to_console(textbox: ctk.CTkTextbox, text: str):
    textbox.configure(state="normal")
    textbox.insert("end", text + "\n")
    textbox.see("end")
    textbox.configure(state="disabled")