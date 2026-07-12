import subprocess
import json
import os
import threading
import queue

class SplitterCore:
    def __init__(self):
        self.is_running = False
        self.is_canceled = False
        self.current_process = None
        self.log_queue = queue.Queue()
        self.status = "PŘIPRAVENO."
        self.progress = 0.0

    def log(self, message):
        self.log_queue.put({"type": "log", "message": message})

    def update_status(self, text, progress_val=None):
        self.status = text
        if progress_val is not None:
            self.progress = progress_val
        self.log_queue.put({"type": "status", "status": self.status, "progress": self.progress})

    def cancel(self):
        if self.is_running:
            self.is_canceled = True
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.kill()
                except Exception:
                    pass

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

    def start_split(self, input_file, output_dir, num_parts, overlap):
        self.is_running = True
        self.is_canceled = False
        
        t = threading.Thread(target=self._split_worker, args=(input_file, output_dir, num_parts, overlap))
        t.daemon = True
        t.start()

    def _split_worker(self, input_file, output_dir, n, overlap):
        try:
            self.update_status("ZJIŠŤUJI DÉLKU SOUBORU...", 0)
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
                self.log_queue.put({"type": "done"})

        except Exception as e:
            err_msg = str(e)
            self.log(f"CHYBA: {err_msg}")
            self.update_status("NASTALA KRITICKÁ CHYBA.")
            self.log_queue.put({"type": "error", "message": err_msg})
        finally:
            self.is_running = False
            self.current_process = None
