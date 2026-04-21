import tkinter as tk
from tkinter import messagebox
import threading
import yt_dlp
import os
from datetime import datetime

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads")
LOG_FILE     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloaded_videos.txt")

# --- Theme ---
C = {
    "BG":           "#121212",
    "CARD":         "#1e1e1e",
    "INPUT_BG":     "#2a2a2a",
    "BORDER":       "#333333",
    "TEXT":         "#e4e4e7",
    "TEXT_SEC":     "#a1a1aa",
    "TEXT_DIM":     "#71717a",
    "ACCENT":       "#7c3aed",
    "ACCENT_HOVER": "#6d28d9",
    "ACCENT_LIGHT": "#a78bfa",
    "GREEN":        "#10b981",
    "RED":          "#ef4444",
    "BTN_BG":       "#2a2a2a",
    "BTN_HOVER":    "#3a3a3a",
}
FONT       = ("Segoe UI", 11)
FONT_SM    = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI", 16, "bold")


# --- Log helper ---
def log_download(title, url, quality):
    """Append a numbered entry to the download log."""
    # Count existing entries to get next number
    count = 0
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and line[0].isdigit():
                    count += 1
    count += 1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"{count}. [{timestamp}] {title}  |  {quality}  |  {url}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def round_rect(canvas, x1, y1, x2, y2, r=14, **kwargs):
    points = [
        x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
        x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
        x1, y2, x1, y2-r, x1, y1+r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


class StyledButton(tk.Canvas):
    def __init__(self, parent, text, command=None, accent=False, width=140, height=38, bg_parent=None):
        bg = bg_parent or C["CARD"]
        super().__init__(parent, width=width, height=height,
                         bg=bg, highlightthickness=0, cursor="hand2")
        self.command = command
        self.accent  = accent
        self.text    = text
        self.w       = width
        self.h       = height
        self._disabled = False
        self._draw()
        self.bind("<Enter>",          self._on_enter)
        self.bind("<Leave>",          self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)

    def _colors(self, hover=False):
        if self._disabled:
            return C["INPUT_BG"], C["TEXT_DIM"]
        if self.accent:
            return (C["ACCENT_HOVER"] if hover else C["ACCENT"]), "#ffffff"
        return (C["BTN_HOVER"] if hover else C["BTN_BG"]), C["TEXT"]

    def _draw(self, hover=False):
        self.delete("all")
        bg, fg = self._colors(hover)
        round_rect(self, 0, 0, self.w, self.h, r=10, fill=bg, outline="")
        self.create_text(self.w // 2, self.h // 2, text=self.text,
                         fill=fg, font=("Segoe UI", 10, "bold"))

    def _on_enter(self, e):
        if not self._disabled:
            self._draw(hover=True)

    def _on_leave(self, e):
        self._draw(hover=False)

    def _on_click(self, e):
        if not self._disabled and self.command:
            self.command()

    def set_state(self, state):
        self._disabled = (state == "disabled")
        self._draw()


class StyledProgress(tk.Canvas):
    def __init__(self, parent, width=440, height=6):
        super().__init__(parent, width=width, height=height,
                         bg=C["CARD"], highlightthickness=0)
        self.w = width
        self.h = height
        self._value = 0
        self._draw()

    def _draw(self):
        self.delete("all")
        round_rect(self, 0, 0, self.w, self.h, r=3, fill=C["BORDER"], outline="")
        if self._value > 0:
            fill_w = max(6, self.w * self._value / 100)
            round_rect(self, 0, 0, fill_w, self.h, r=3, fill=C["ACCENT"], outline="")

    def set(self, value):
        self._value = min(100, max(0, value))
        self._draw()


class URLRow(tk.Frame):
    def __init__(self, parent, on_remove=None, removable=True):
        super().__init__(parent, bg=C["CARD"])
        self.on_remove = on_remove

        input_frame = tk.Frame(self, bg=C["INPUT_BG"], highlightbackground=C["BORDER"],
                               highlightthickness=1, padx=8, pady=5)
        input_frame.pack(side="left", fill="x", expand=True)

        self.entry = tk.Entry(input_frame, font=FONT, bg=C["INPUT_BG"], fg=C["TEXT"],
                              insertbackground=C["ACCENT_LIGHT"], relief="flat",
                              selectbackground=C["ACCENT"], selectforeground="#fff")
        self.entry.pack(fill="x")

        if removable:
            remove_btn = tk.Label(self, text="  ✕  ", font=("Segoe UI", 11), bg=C["CARD"],
                                  fg=C["TEXT_DIM"], cursor="hand2")
            remove_btn.pack(side="right", padx=(6, 0))
            remove_btn.bind("<Enter>",          lambda e: remove_btn.config(fg=C["RED"]))
            remove_btn.bind("<Leave>",          lambda e: remove_btn.config(fg=C["TEXT_DIM"]))
            remove_btn.bind("<ButtonRelease-1>", lambda e: self._remove())

        self.status_label = tk.Label(self, text="", font=("Segoe UI", 8),
                                     bg=C["CARD"], fg=C["TEXT_DIM"])
        self.status_label.pack(side="right", padx=(6, 0))

    def _remove(self):
        if self.on_remove:
            self.on_remove(self)

    def get_url(self):
        return self.entry.get().strip()


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Video Downloader")
        self.root.configure(bg=C["BG"])
        self.url_rows        = []
        self.quality_radios  = []
        self.fetched_qualities = []

        # Card
        self.card = tk.Frame(self.root, bg=C["CARD"], highlightbackground=C["BORDER"],
                             highlightthickness=1, padx=28, pady=20)
        self.card.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        tk.Label(self.card, text="Video Downloader", font=FONT_TITLE,
                 bg=C["CARD"], fg=C["TEXT"]).pack(anchor="w")
        tk.Label(self.card, text="Paste links and download in your chosen quality",
                 font=FONT_SM, bg=C["CARD"], fg=C["TEXT_DIM"]).pack(anchor="w", pady=(0, 14))

        # --- URL section ---
        url_header = tk.Frame(self.card, bg=C["CARD"])
        url_header.pack(fill="x")
        tk.Label(url_header, text="URLs", font=("Segoe UI", 10, "bold"),
                 bg=C["CARD"], fg=C["TEXT_SEC"]).pack(side="left")

        self.add_btn = tk.Label(url_header, text="  + Add URL  ", font=("Segoe UI", 9, "bold"),
                                bg=C["CARD"], fg=C["ACCENT_LIGHT"], cursor="hand2")
        self.add_btn.pack(side="right")
        self.add_btn.bind("<Enter>",          lambda e: self.add_btn.config(fg=C["ACCENT"]))
        self.add_btn.bind("<Leave>",          lambda e: self.add_btn.config(fg=C["ACCENT_LIGHT"]))
        self.add_btn.bind("<ButtonRelease-1>", lambda e: self.add_url_row())

        self.urls_container = tk.Frame(self.card, bg=C["CARD"])
        self.urls_container.pack(fill="x", pady=(6, 0))

        # --- Quality section ---
        tk.Frame(self.card, bg=C["BORDER"], height=1).pack(fill="x", pady=(14, 14))

        quality_header = tk.Frame(self.card, bg=C["CARD"])
        quality_header.pack(fill="x")
        tk.Label(quality_header, text="Quality", font=("Segoe UI", 10, "bold"),
                 bg=C["CARD"], fg=C["TEXT_SEC"]).pack(side="left")
        self.quality_hint = tk.Label(quality_header, text="", font=("Segoe UI", 8),
                                     bg=C["CARD"], fg=C["TEXT_DIM"])
        self.quality_hint.pack(side="right")

        self.quality_var   = tk.StringVar(value="Highest available")
        self.quality_frame = tk.Frame(self.card, bg=C["CARD"])
        self.quality_frame.pack(fill="x", pady=(6, 0))

        self._build_quality_radios(["Highest available"])

        # --- Divider ---
        tk.Frame(self.card, bg=C["BORDER"], height=1).pack(fill="x", pady=(14, 14))

        # --- Buttons ---
        btn_frame = tk.Frame(self.card, bg=C["CARD"])
        btn_frame.pack()

        self.fetch_btn = StyledButton(btn_frame, "Fetch Quality", command=self.fetch_quality,
                                      accent=False, width=130, height=40)
        self.fetch_btn.pack(side="left", padx=(0, 10))

        self.download_btn = StyledButton(btn_frame, "Download", command=self.download_all,
                                         accent=True, width=140, height=40)
        self.download_btn.pack(side="left", padx=(0, 10))

        self.done_btn = StyledButton(btn_frame, "Done", command=self.reset_gui,
                                     accent=False, width=100, height=40)
        self.done_btn.set_state("disabled")
        self.done_btn.pack(side="left")

        # --- Status area ---
        self.quality_label = tk.Label(self.card, text="", font=FONT_SM,
                                      bg=C["CARD"], fg=C["ACCENT_LIGHT"])
        self.quality_label.pack(pady=(10, 0))

        self.progress_bar = StyledProgress(self.card, width=460, height=6)
        self.progress_bar.pack(pady=(6, 0))

        self.status_label = tk.Label(self.card, text="", font=FONT_SM,
                                     bg=C["CARD"], fg=C["TEXT_SEC"])
        self.status_label.pack(pady=(4, 0))

        # Add first URL row AFTER everything is built
        self.add_url_row(removable=False)

        self.root.mainloop()

    # ------------------------------------------------------------------ #
    #  Quality helpers
    # ------------------------------------------------------------------ #
    def _build_quality_radios(self, options, enabled=True):
        for rb in self.quality_radios:
            rb.destroy()
        self.quality_radios.clear()

        for i, q in enumerate(options):
            state = "normal" if enabled else "disabled"
            fg    = C["TEXT_SEC"] if enabled else C["TEXT_DIM"]
            rb = tk.Radiobutton(
                self.quality_frame, text=q, variable=self.quality_var, value=q,
                font=FONT_SM, bg=C["CARD"], fg=fg, disabledforeground=C["TEXT_DIM"],
                selectcolor=C["INPUT_BG"], activebackground=C["CARD"],
                activeforeground=C["TEXT"], highlightthickness=0,
                borderwidth=0, indicatoron=True, state=state,
            )
            rb.grid(row=i // 4, column=i % 4, sticky="w", padx=(0, 18), pady=2)
            self.quality_radios.append(rb)
        self._fit_window()

    def _update_quality_section(self):
        url_count = len(self.url_rows)
        if url_count > 1:
            self.quality_var.set("Highest available")
            self._build_quality_radios(["Highest available"], enabled=False)
            self.quality_hint.config(text="Quality selection available for single video only")
            self.fetched_qualities.clear()
            self.fetch_btn.set_state("disabled")
        elif self.fetched_qualities:
            self._build_quality_radios(self.fetched_qualities, enabled=True)
            self.quality_hint.config(text="")
            self.fetch_btn.set_state("normal")
        else:
            self._build_quality_radios(["Highest available"], enabled=True)
            self.quality_hint.config(text="")
            self.fetch_btn.set_state("normal")

    def _fetch_qualities(self, url):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
                info = ydl.extract_info(url, download=False)
                heights = set()
                for f in info.get("formats", []):
                    h = f.get("height")
                    if h and f.get("vcodec", "none") != "none":
                        heights.add(h)
                return sorted(heights, reverse=True)
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    #  URL row management
    # ------------------------------------------------------------------ #
    def add_url_row(self, removable=True):
        row = URLRow(self.urls_container, on_remove=self.remove_url_row, removable=removable)
        row.pack(fill="x", pady=(0, 6))
        self.url_rows.append(row)
        self._update_quality_section()

    def remove_url_row(self, row):
        if row in self.url_rows:
            self.url_rows.remove(row)
            row.destroy()
            self._update_quality_section()

    def _fit_window(self):
        self.root.update_idletasks()
        w = self.card.winfo_reqwidth() + 40
        h = self.card.winfo_reqheight() + 40
        self.root.geometry(f"{max(w, 580)}x{max(h, 300)}")

    def _get_format_string(self, max_height=None):
        if max_height is None:
            return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
        return (f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best")

    # ------------------------------------------------------------------ #
    #  Fetch quality button
    # ------------------------------------------------------------------ #
    def fetch_quality(self):
        if len(self.url_rows) > 1:
            messagebox.showinfo("Info", "Quality selection is only available for a single video.")
            return
        url = self.url_rows[0].get_url() if self.url_rows else ""
        if not url:
            messagebox.showwarning("No URL", "Please paste a link first.")
            return

        self.fetch_btn.set_state("disabled")
        self.status_label.config(text="Fetching available qualities...", fg=C["TEXT_SEC"])

        def run():
            heights = self._fetch_qualities(url)
            if heights:
                options = ["Highest available"] + [f"{h}p" for h in heights]
                self.fetched_qualities = options
                self.quality_var.set("Highest available")
                self._build_quality_radios(options, enabled=True)
                self.status_label.config(
                    text="Available: " + ", ".join(f"{h}p" for h in heights),
                    fg=C["ACCENT_LIGHT"])
            else:
                self.status_label.config(text="Could not fetch qualities.", fg=C["RED"])
            self.fetch_btn.set_state("normal")

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Download
    # ------------------------------------------------------------------ #
    def download_all(self):
        urls = [(i, row) for i, row in enumerate(self.url_rows) if row.get_url()]
        if not urls:
            messagebox.showwarning("No URLs", "Please paste at least one link.")
            return

        self.download_btn.set_state("disabled")
        self.fetch_btn.set_state("disabled")
        self.done_btn.set_state("disabled")
        self.progress_bar.set(0)
        self.quality_label.config(text="")

        def run():
            total      = len(urls)
            choice     = self.quality_var.get()
            max_height = None
            if choice != "Highest available":
                try:
                    max_height = int(choice.replace("p", ""))
                except ValueError:
                    pass

            fmt = self._get_format_string(max_height)

            for idx, (i, row) in enumerate(urls):
                url = row.get_url()
                row.status_label.config(text="⏳", fg=C["ACCENT_LIGHT"])
                self.status_label.config(text=f"Downloading {idx+1}/{total}...", fg=C["TEXT_SEC"])

                try:
                    def progress_hook(d, _idx=idx, _row=row):
                        if d["status"] == "downloading":
                            t  = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                            dl = d.get("downloaded_bytes", 0)
                            if t:
                                base    = _idx / total * 100
                                current = (dl / t) * (100 / total)
                                self.progress_bar.set(base + current)
                        elif d["status"] == "finished":
                            _row.status_label.config(text="Merging...", fg=C["TEXT_SEC"])

                    ydl_opts = {
                        "format": fmt,
                        "merge_output_format": "mp4",
                        "postprocessors": [{
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": "mp4",
                        }],
                        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
                        "progress_hooks": [progress_hook],
                        "quiet": True,
                        "no_warnings": True,
                    }

                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info    = ydl.extract_info(url, download=False)
                        title   = info.get("title", url)
                        best_h  = 0
                        best_fps = 0
                        for f in info.get("formats", []):
                            h   = f.get("height") or 0
                            fps = f.get("fps") or 0
                            if max_height and h > max_height:
                                continue
                            if h > best_h or (h == best_h and fps > best_fps):
                                best_h   = h
                                best_fps = fps

                        quality_str = f"{best_h}p{best_fps}"
                        label = f"Video {idx+1}: " if total > 1 else ""
                        self.quality_label.config(
                            text=f"{label}Downloading at {quality_str}")

                        ydl.download([url])

                    # Log successful download
                    log_download(title, url, quality_str)
                    row.status_label.config(text="✓", fg=C["GREEN"])

                except Exception as e:
                    row.status_label.config(text="✗", fg=C["RED"])
                    messagebox.showerror("Error", f"Failed: {url}\n\n{e}")

            self.progress_bar.set(100)
            self.status_label.config(
                text=f"All done! ({total} video{'s' if total > 1 else ''})",
                fg=C["GREEN"])
            self.quality_label.config(text="")
            self.done_btn.set_state("normal")
            self.download_btn.set_state("normal")
            self.fetch_btn.set_state("normal")

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Reset
    # ------------------------------------------------------------------ #
    def reset_gui(self):
        while len(self.url_rows) > 1:
            row = self.url_rows.pop()
            row.destroy()
        self.url_rows[0].entry.delete(0, tk.END)
        self.url_rows[0].status_label.config(text="")
        self.quality_var.set("Highest available")
        self.fetched_qualities.clear()
        self._build_quality_radios(["Highest available"])
        self.quality_hint.config(text="")
        self.quality_label.config(text="")
        self.progress_bar.set(0)
        self.status_label.config(text="", fg=C["TEXT_SEC"])
        self.done_btn.set_state("disabled")


App()
