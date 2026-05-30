import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import json
import os

class VortexSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Marian's Splitter")
        self.root.geometry("650x750")
        
        # Obsidian Brutalist Palette
        self.C_BLACK = "#0f0f11"
        self.C_DEEP = "#1a1a1d"
        self.C_SURFACE = "#26262b"
        self.C_BORDER = "#3e3e46"
        self.C_WHITE = "#f2f0e6"
        self.C_MUTED = "#888891"
        self.C_ACCENT = "#eaa028"  # Warm amber
        self.C_ACCENT_FG = "#111113"
        self.C_DANGER = "#d93b3b"
        
        self.FONT_MAIN = ("Segoe UI", 10)
        self.FONT_MONO = ("Consolas", 9)
        self.FONT_HEAD = ("Segoe UI", 22, "bold")
        
        self.root.configure(bg=self.C_BLACK)
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # General Label
        self.style.configure("TLabel", background=self.C_DEEP, foreground=self.C_WHITE, font=self.FONT_MAIN)
        self.style.configure("Header.TLabel", background=self.C_DEEP, foreground=self.C_WHITE, font=self.FONT_HEAD)
        
        # Buttons (Geometric, no curves, 1px border)
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background=self.C_SURFACE, foreground=self.C_WHITE, borderwidth=1, bordercolor=self.C_BORDER, relief="solid", padding=8)
        self.style.map("TButton", background=[("active", self.C_BORDER)], foreground=[("active", self.C_WHITE)])
        
        self.style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), background=self.C_ACCENT, foreground=self.C_ACCENT_FG, borderwidth=0, padding=12)
        self.style.map("Accent.TButton", background=[("active", "#ffb845")])
        
        self.style.configure("Cancel.TButton", font=("Segoe UI", 12, "bold"), background=self.C_DANGER, foreground="#ffffff", borderwidth=0, padding=12)
        self.style.map("Cancel.TButton", background=[("active", "#ff4d4d")])

        # Entries
        self.style.configure("TEntry", fieldbackground=self.C_SURFACE, foreground=self.C_WHITE, font=self.FONT_MAIN, borderwidth=1, bordercolor=self.C_BORDER, relief="solid")
        
        # Progressbar
        self.style.configure("Horizontal.TProgressbar", background=self.C_ACCENT, troughcolor=self.C_SURFACE, bordercolor=self.C_BORDER, lightcolor=self.C_ACCENT, darkcolor=self.C_ACCENT, borderwidth=1)

        self.input_file = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.num_parts = tk.IntVar(value=2)
        self.overlap = tk.DoubleVar(value=5.0)

        # Tracing process and thread
        self.is_running = False
        self.is_canceled = False
        self.current_process = None

        self.create_widgets()

    def create_widgets(self):
        # Main shell
        main_frame = tk.Frame(self.root, bg=self.C_BLACK, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Masthead
        masthead = tk.Frame(main_frame, bg=self.C_DEEP, bd=1, relief="solid", highlightbackground=self.C_BORDER, highlightcolor=self.C_BORDER, highlightthickness=1)
        masthead.pack(fill=tk.X, pady=(0, 20))
        # left accent line simulated by a 4px frame
        accent_line = tk.Frame(masthead, bg=self.C_ACCENT, width=4)
        accent_line.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(masthead, text="MARIAN'S SPLITTER", style="Header.TLabel").pack(side=tk.LEFT, padx=20, pady=20)
        
        version_lbl = tk.Label(masthead, text="v3", bg=self.C_ACCENT, fg=self.C_ACCENT_FG, font=("Segoe UI", 8, "bold"), padx=5, pady=2)
        version_lbl.pack(side=tk.LEFT, pady=25)

        # Card
        card_frame = tk.Frame(main_frame, bg=self.C_DEEP, highlightbackground=self.C_BORDER, highlightthickness=1)
        card_frame.pack(fill=tk.X, pady=5)
        
        inner_pad = tk.Frame(card_frame, bg=self.C_DEEP, padx=25, pady=25)
        inner_pad.pack(fill=tk.BOTH, expand=True)

        card_title = tk.Label(inner_pad, text="PARAMETRY DĚLENÍ", bg=self.C_DEEP, fg=self.C_WHITE, font=("Segoe UI", 12, "bold"))
        card_title.pack(anchor="w", pady=(0, 15))
        
        # Separator
        tk.Frame(inner_pad, bg=self.C_BORDER, height=1).pack(fill=tk.X, pady=(0, 15))

        # Input File
        file_frame = tk.Frame(inner_pad, bg=self.C_DEEP)
        file_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(file_frame, text="ZDROJOVÝ SOUBOR (MP3/MP4)", bg=self.C_DEEP, fg=self.C_ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 5))
        file_entry_frame = tk.Frame(file_frame, bg=self.C_DEEP)
        file_entry_frame.pack(fill=tk.X)
        self.file_entry = ttk.Entry(file_entry_frame, textvariable=self.input_file, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.browse_file_btn = ttk.Button(file_entry_frame, text="VYBRAT", command=self.browse_file)
        self.browse_file_btn.pack(side=tk.RIGHT)

        # Output Dir
        dir_frame = tk.Frame(inner_pad, bg=self.C_DEEP)
        dir_frame.pack(fill=tk.X, pady=(0, 15))
        tk.Label(dir_frame, text="CÍLOVÁ SLOŽKA", bg=self.C_DEEP, fg=self.C_ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 5))
        dir_entry_frame = tk.Frame(dir_frame, bg=self.C_DEEP)
        dir_entry_frame.pack(fill=tk.X)
        self.dir_entry = ttk.Entry(dir_entry_frame, textvariable=self.output_dir, state="readonly")
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.browse_dir_btn = ttk.Button(dir_entry_frame, text="VYBRAT", command=self.browse_dir)
        self.browse_dir_btn.pack(side=tk.RIGHT)

        # Settings Grid
        settings_frame = tk.Frame(inner_pad, bg=self.C_DEEP)
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(settings_frame, text="POČET ČÁSTÍ", bg=self.C_DEEP, fg=self.C_ACCENT, font=("Segoe UI", 8, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 5), padx=(0, 20))
        self.num_parts_entry = ttk.Entry(settings_frame, textvariable=self.num_parts, width=15)
        self.num_parts_entry.grid(row=1, column=0, sticky="w", padx=(0, 20))

        tk.Label(settings_frame, text="PŘEKRYV (S)", bg=self.C_DEEP, fg=self.C_ACCENT, font=("Segoe UI", 8, "bold")).grid(row=0, column=1, sticky="w", pady=(0, 5))
        self.overlap_entry = ttk.Entry(settings_frame, textvariable=self.overlap, width=15)
        self.overlap_entry.grid(row=1, column=1, sticky="w")

        # Start/Cancel Buttons container
        self.btn_frame = tk.Frame(inner_pad, bg=self.C_DEEP)
        self.btn_frame.pack(pady=(15, 0), fill=tk.X)

        self.start_btn = ttk.Button(self.btn_frame, text="ROZDĚLIT SOUBOR", style="Accent.TButton", command=self.start_splitting)
        self.start_btn.pack(fill=tk.X)

        self.cancel_btn = ttk.Button(self.btn_frame, text="ZRUŠIT PROCES", style="Cancel.TButton", command=self.cancel_splitting)
        
        # Terminal Unit
        term_frame = tk.Frame(main_frame, bg=self.C_DEEP, highlightbackground=self.C_BORDER, highlightthickness=1)
        term_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        
        term_pad = tk.Frame(term_frame, bg=self.C_DEEP, padx=20, pady=20)
        term_pad.pack(fill=tk.BOTH, expand=True)

        term_header = tk.Frame(term_pad, bg=self.C_DEEP)
        term_header.pack(fill=tk.X, pady=(0, 10))
        tk.Label(term_header, text="TERMINÁL / STAV", bg=self.C_DEEP, fg=self.C_WHITE, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="PŘIPRAVENO.")
        tk.Label(term_header, textvariable=self.status_var, bg=self.C_DEEP, fg=self.C_ACCENT, font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT)
        
        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(term_pad, variable=self.progress_var, maximum=100)
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Log Console
        log_bg = tk.Frame(term_pad, bg=self.C_BLACK, highlightbackground=self.C_BORDER, highlightthickness=1)
        log_bg.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_bg, bg=self.C_BLACK, fg=self.C_WHITE, font=self.FONT_MONO, state="disabled", bd=0, padx=10, pady=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_bg, command=self.log_text.yview, bg=self.C_SURFACE)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text['yscrollcommand'] = scrollbar.set
        
        self.log_init("> SYSTEM READY.")

    def set_ui_state(self, running):
        state = "disabled" if running else "normal"
        self.browse_file_btn.config(state=state)
        self.browse_dir_btn.config(state=state)
        self.num_parts_entry.config(state=state)
        self.overlap_entry.config(state=state)
        
        if running:
            self.start_btn.pack_forget()
            self.cancel_btn.pack(fill=tk.X)
        else:
            self.cancel_btn.pack_forget()
            self.start_btn.pack(fill=tk.X)

    def browse_file(self):
        file = filedialog.askopenfilename(filetypes=[("Media Files", "*.mp3 *.mp4")])
        if file:
            self.input_file.set(file)
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(file))

    def browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir.set(d)

    def log_init(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def log(self, message):
        self.root.after(0, self._log_ui, message)

    def _log_ui(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", "> " + message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def update_status(self, text, progress_val=None):
        def _update():
            self.status_var.set(text)
            if progress_val is not None:
                self.progress_var.set(progress_val)
        self.root.after(0, _update)

    def cancel_splitting(self):
        if self.is_running:
            self.is_canceled = True
            self.cancel_btn.config(text="RUŠÍM...", state="disabled")
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.kill()
                except Exception:
                    pass

    def start_splitting(self):
        if not self.input_file.get() or not self.output_dir.get():
            self.log("CHYBA: VYBERTE VSTUPNÍ SOUBOR A CÍLOVOU SLOŽKU.")
            return
        
        try:
            n = self.num_parts.get()
            o = self.overlap.get()
            if n < 2:
                raise ValueError()
        except ValueError:
            self.log("CHYBA: POČET ČÁSTÍ MUSÍ BÝT ALESPOŇ 2 A PŘEKRYV PLATNÉ ČÍSLO.")
            return

        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        self.progress_var.set(0)
        
        self.set_ui_state(True)
        self.cancel_btn.config(text="ZRUŠIT PROCES", state="normal")
        self.is_running = True
        self.is_canceled = False

        t = threading.Thread(target=self.split_worker, args=(self.input_file.get(), self.output_dir.get(), n, o))
        t.daemon = True
        t.start()

    def get_duration(self, filepath):
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath]
        self.log(f"Zjišťuji délku: {' '.join(cmd)}")
        
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo)
        if result.returncode != 0:
            raise Exception(f"Nepodařilo se spustit ffprobe. Detaily: {result.stderr}")
        
        data = json.loads(result.stdout)
        duration = None
        if 'format' in data and 'duration' in data['format']:
            duration = float(data['format']['duration'])
        else:
            for stream in data.get('streams', []):
                if 'duration' in stream:
                    duration = float(stream['duration'])
                    break
        if duration is None:
            raise Exception("Délka souboru nenalezena. Může jít o poškozený nebo nepodporovaný soubor.")
        return duration

    def split_worker(self, input_file, output_dir, n, overlap):
        try:
            self.update_status("ZJIŠŤUJI DÉLKU SOUBORU...")
            duration = self.get_duration(input_file)
            self.log(f"CELKOVÁ DÉLKA SOUBORU: {duration:.2f} S")

            part_length = duration / n
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            ext = os.path.splitext(input_file)[1].lower()

            for i in range(n):
                if self.is_canceled:
                    break
                    
                start_time = i * part_length
                
                if i < n - 1:
                    end_time = min((i + 1) * part_length + overlap, duration)
                else:
                    end_time = duration

                part_dur = end_time - start_time
                out_name = f"{base_name}_cast_{i+1}{ext}"
                out_path = os.path.join(output_dir, out_name)
                
                counter = 1
                while os.path.exists(out_path):
                    out_name = f"{base_name}_cast_{i+1}_{counter}{ext}"
                    out_path = os.path.join(output_dir, out_name)
                    counter += 1

                self.update_status(f"ZPRACOVÁVÁM ČÁST {i+1} Z {n}...", (i / n) * 100)
                self.log(f"==== ČÁST {i+1} ====")
                self.log(f"ČAS: {start_time:.2f}S - {end_time:.2f}S (DÉLKA: {part_dur:.2f}S)")
                self.log(f"CÍL: {out_name}")

                # FAST MODE ONLY
                cmd = ['ffmpeg', '-y', '-ss', str(start_time), '-t', str(part_dur), '-i', input_file, '-c', 'copy', out_path]

                self.log(f"FFMPEG: {' '.join(cmd[1:])}")
                
                startupinfo = None
                if os.name == 'nt':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                    text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo
                )
                
                self.current_process = process
                
                last_lines = []
                for line in process.stdout:
                    if self.is_canceled:
                        break
                    stripped = line.strip()
                    last_lines.append(stripped)
                    if len(last_lines) > 5:
                        last_lines.pop(0)
                    if "time=" in stripped or "Error" in stripped or "Exception" in stripped:
                        self.log(stripped)
                
                process.wait()
                self.current_process = None
                
                if self.is_canceled:
                    break
                
                if process.returncode != 0 and process.returncode != 9 and process.returncode != -15:
                    err_details = "\\n".join(last_lines)
                    raise Exception(f"PROCES SELHAL NA ČÁSTI {i+1}. POSLEDNÍ VÝSTUP:\n{err_details}")

            if self.is_canceled:
                self.update_status("ZRUŠENO UŽIVATELEM.", 0)
                self.log("===============================")
                self.log("PROCES BYL ZRUŠEN UŽIVATELEM.")
            else:
                self.update_status("HOTOVO!", 100)
                self.log("===============================")
                self.log("ROZDĚLOVÁNÍ BYLO ÚSPĚŠNĚ DOKONČENO!")

        except Exception as e:
            err_msg = str(e)
            self.log(f"CHYBA: {err_msg}")
            self.update_status("NASTALA KRITICKÁ CHYBA.")
        finally:
            self.is_running = False
            self.current_process = None
            self.root.after(0, lambda: self.set_ui_state(False))

if __name__ == "__main__":
    root = tk.Tk()
    app = VortexSplitterApp(root)
    root.mainloop()
