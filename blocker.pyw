from customtkinter import *
import time
import threading
import keyboard
from tkinter import messagebox


pin_file = "pin.txt"

def read_pin():
    try:
        with open(pin_file, 'r') as file:
            return str(file.readline().strip())
    except Exception as e:
        print(f"Error reading pin file: {e}")
        return "0000"
pin = read_pin()

class LockScreenApp:
    def __init__(self, root):
        self.root = root
        self.pin = read_pin()
        self.locked = False
        self.running = True

        self.root.attributes("-fullscreen", True)
        self.root.attributes("-alpha", 0.8)  
        self.root.configure(bg="#242424")
        self.root.withdraw()

        self.check_time_thread = threading.Thread(target=self.check_time, daemon=True)
        self.check_time_thread.start()

    def check_time(self):
        while self.running:
            current_time = time.strftime("%H:%M")
            hour = int(time.strftime("%H"))
            minute = int(time.strftime("%M"))
            print(f"Current time: {current_time}, Locked: {self.locked}, Running: {self.running}")  # Debugging

        
            if hour == 21  and minute == 0: 
                self.stop_keyboard_blocker()
                self.running = False
                self.locked = False
                self.root.withdraw()

                break

         
            if (hour >= 21 or hour < 4) and not self.locked:
                print("Locking screen.") 
                self.lock_screen()

            time.sleep(1)

    def lock_screen(self):
        self.locked = True
        self.root.deiconify()
        self.start_keyboard_blocker()
        self.create_lock_screen()

    def unlock_screen(self):
        entered_pin = self.pin_entry.get()
        if entered_pin == self.pin:
            self.locked = False
            self.running = False
            self.stop_keyboard_blocker()
            self.root.quit()  # Stop the Tkinter main loop
            self.root.destroy()  # Destroy the root window
        else:
            messagebox.showerror("Error", "Incorrect PIN. Try again.")
            self.pin_entry.delete(0, END)

    def create_lock_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        CTkLabel(self.root, text="\nLocked", font=("Arial", 64), text_color="white", bg_color="#242424").pack(pady=30)
        CTkLabel(self.root, text="The PC is locked. Please come back at 4:00 AM.", font=("Arial", 18), text_color="white", bg_color="#242424").pack(pady=10)
        CTkLabel(self.root, text="Enter PIN to Unlock", font=("Arial", 36), text_color="white", bg_color="#242424").pack(pady=20)
        self.pin_entry = CTkEntry(self.root, font=("Arial", 28), show="*", justify="center", bg_color="#242424", text_color="white", width=300, height=50)
        self.pin_entry.pack(pady=20)

        button_frame = CTkFrame(self.root, fg_color="#242424")
        button_frame.pack(pady=20)

        for i in reversed(range(1, 10)):  # Reverse the range to iterate from 9 to 1
            CTkButton(
                button_frame,
                text=str(i),
                font=("Arial", 24),
                width=80,
                height=60,
                bg_color="#242424",
                text_color="white",
                fg_color="green",
                hover_color="lightgreen",
                border_color="black",
                corner_radius=100,
                command=lambda num=i: self.add_to_pin(num)
            ).grid(row=(9 - i) // 3, column=2 - (9 - i) % 3, padx=10, pady=10)

        # Add the "0" button
        CTkButton(
            button_frame,
            text="0",
            font=("Arial", 24),
            width=80,
            height=60,
            bg_color="#242424",
            text_color="white",
            fg_color="green",
            hover_color="lightgreen",
            border_color="black",
            corner_radius=100,
            command=lambda: self.add_to_pin(0)
        ).grid(row=3, column=1, padx=10, pady=10)  # Place "0" in the center of the last row

        # Add the "Undo" button
        CTkButton(
            button_frame,
            text="Undo",
            font=("Arial", 24),
            width=80,
            height=60,
            fg_color="red",
            text_color="white",
            hover_color="lightcoral",
            corner_radius=5,
            border_color="black",
            command=self.undo_last_digit
        ).grid(row=3, column=0, padx=10, pady=10)  # Place "Undo" on the left of the last row

        CTkButton(
            button_frame,
            text=" ✓ ",
            font=("Arial", 24),
            width=80,
            height=60,
            fg_color="green",
            text_color="white",
            hover_color="lightgreen",
            corner_radius=5,
            border_color="black",
            command=self.unlock_screen
        ).grid(row=3, column=2, padx=10, pady=10)  # Place "✔️" on the right of the last ro
 
        CTkLabel(self.root, text="Ask Admin for the PIN.", font=("Arial", 18), text_color="white", bg_color="#242424").pack(pady=10)
 

    def undo_last_digit(self):
        current_pin = self.pin_entry.get()
        self.pin_entry.delete(0, END)
        self.pin_entry.insert(0, current_pin[:-1])

    def add_to_pin(self, num):
        current_pin = self.pin_entry.get()
        self.pin_entry.delete(0, END)
        self.pin_entry.insert(0, current_pin + str(num))

    def start_keyboard_blocker(self):
        keyboard.block_key("alt")
        keyboard.block_key("tab")
        keyboard.block_key("windows")
        keyboard.block_key("ctrl")
        keyboard.block_key("shift")
        keyboard.block_key("esc")
        keyboard.block_key("f4")
        keyboard.block_key("f1")
        keyboard.block_key("f2")
        keyboard.block_key("f3")
        keyboard.block_key("f5")
        keyboard.block_key("f6")
        keyboard.block_key("f7")
        keyboard.block_key("f8")
        keyboard.block_key("f9")
        keyboard.block_key("f10")
        keyboard.block_key("f11")
        keyboard.block_key("f12")
        keyboard.block_key("print_screen")
        keyboard.block_key("pause")
        keyboard.block_key("insert")

    def stop_keyboard_blocker(self):
        keyboard.unhook_all()

if __name__ == "__main__":
    root = CTk()
    app = LockScreenApp(root)
    root.mainloop()