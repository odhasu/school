import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, colorchooser
from PIL import Image, ImageTk, ImageFilter, ImageDraw
import time
import threading
import os
import platform

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

QUOTES = [
    "Stay focused. You got this.",
    "One step at a time.",
    "Progress, not perfection.",
    "Deep work = real results.",
    "Eliminate distraction. Dominate.",
    "The secret is to start.",
    "Focus is a superpower.",
    "You're closer than you think.",
    "Do it now. Thank yourself later.",
    "Breathe. Focus. Execute.",
]

PRESET_GRADIENTS = [
    ("#0f0c29", "#302b63", "#24243e"),
    ("#141e30", "#243b55", "#141e30"),
    ("#1a1a2e", "#16213e", "#0f3460"),
    ("#0d0d0d", "#1a1a1a", "#0d0d0d"),
    ("#0f2027", "#203a43", "#2c5364"),
    ("#1f0036", "#3d0066", "#1f0036"),
    ("#001f3f", "#003366", "#001f3f"),
    ("#1a0000", "#3d0000", "#1a0000"),
]
PRESET_NAMES = ["Night Sky", "Dark Ocean", "Midnight", "Pure Dark",
                "Dark Teal", "Violet", "Navy", "Ember"]

# Pomodoro sequence: True = work session, False = break
# Pattern: work, short, work, short, work, short, work, LONG
POMO_WORK  = 25 * 60
POMO_SHORT =  5 * 60
POMO_LONG  = 15 * 60
POMO_SEQ   = [POMO_WORK, POMO_SHORT, POMO_WORK, POMO_SHORT,
              POMO_WORK, POMO_SHORT, POMO_WORK, POMO_LONG]
POMO_LABELS = ["Focus", "Short Break", "Focus", "Short Break",
               "Focus", "Short Break", "Focus", "Long Break!"]


class FocusTimerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Focus Timer")
        self.geometry("960x660")
        self.minsize(700, 520)
        self.resizable(True, True)

        # Timer state
        self.total_seconds = 25 * 60
        self.remaining = self.total_seconds
        self.running = False
        self.timer_thread = None
        self._stop_event = threading.Event()

        # Background state
        self.bg_image = None
        self.bg_photo = None
        self.current_gradient = PRESET_GRADIENTS[0]
        self.use_image_bg = False

        # Focus mode
        self.focus_mode = False
        self.quote_index = 0
        self._quote_job = None

        # Pomodoro
        self.pomo_on = False
        self.pomo_step = 0

        # Tasks
        self.tasks = []  # list of {"text": str, "done": tk.BooleanVar, "frame": widget}
        self.tasks_visible = False

        # Sessions
        self.session_count = 0
        self.session_dots = []

        self._build_ui()
        self._apply_gradient_bg(self.current_gradient)
        self._start_quote_cycle()

    # ═══════════════════════════════════════════════════════════════
    # UI BUILD
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Outer wrapper (fills window)
        self.outer = ctk.CTkFrame(self, fg_color="transparent")
        self.outer.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ── Top bar ──────────────────────────────────────────────
        top = ctk.CTkFrame(self.outer, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(12, 0))

        self.title_label = ctk.CTkLabel(
            top, text="FOCUS TIMER",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#666666"
        )
        self.title_label.pack(side="left")

        self.focus_btn = ctk.CTkButton(
            top, text="⬛  Focus Mode",
            font=ctk.CTkFont(size=12), width=130, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._toggle_focus_mode
        )
        self.focus_btn.pack(side="right")

        self.bg_btn = ctk.CTkButton(
            top, text="🎨  BG",
            font=ctk.CTkFont(size=12), width=70, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._open_bg_panel
        )
        self.bg_btn.pack(side="right", padx=(0, 6))

        self.tasks_btn = ctk.CTkButton(
            top, text="☑  Tasks",
            font=ctk.CTkFont(size=12), width=80, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._toggle_tasks
        )
        self.tasks_btn.pack(side="right", padx=(0, 6))

        # ── Body (timer + optional task panel) ───────────────────
        self.body = ctk.CTkFrame(self.outer, fg_color="transparent")
        self.body.pack(expand=True, fill="both", padx=24, pady=(0, 12))

        # Timer column
        self.timer_col = ctk.CTkFrame(self.body, fg_color="transparent")
        self.timer_col.pack(side="left", expand=True, fill="both")

        self._build_timer_col(self.timer_col)

        # Task panel (hidden initially)
        self.task_panel = ctk.CTkFrame(
            self.body,
            fg_color="#0d0d1a",
            corner_radius=14,
            border_width=1, border_color="#2a2a4a"
        )
        # Not packed yet — shown on toggle

        self.bg_panel = None

    def _build_timer_col(self, parent):
        # Quote
        self.quote_label = ctk.CTkLabel(
            parent, text=QUOTES[0],
            font=ctk.CTkFont(family="Segoe UI", size=14, slant="italic"),
            text_color="#aaaaaa", wraplength=460
        )
        self.quote_label.pack(pady=(22, 0))

        # Pomodoro step label
        self.pomo_label = ctk.CTkLabel(
            parent, text="",
            font=ctk.CTkFont(size=11), text_color="#5b8dee"
        )
        self.pomo_label.pack(pady=(2, 0))

        # Timer display
        self.timer_display = ctk.CTkLabel(
            parent, text=self._fmt(self.remaining),
            font=ctk.CTkFont(family="Segoe UI", size=96, weight="bold"),
            text_color="#ffffff"
        )
        self.timer_display.pack(pady=(6, 0))

        # Progress bar
        self.progress = ctk.CTkProgressBar(
            parent, width=400, height=6,
            fg_color="#1a1a2e", progress_color="#5b8dee",
            corner_radius=3
        )
        self.progress.set(1.0)
        self.progress.pack(pady=(4, 18))

        # Preset buttons
        pf = ctk.CTkFrame(parent, fg_color="transparent")
        pf.pack(pady=(0, 10))
        for label, mins in [("5m", 5), ("10m", 10), ("25m", 25), ("45m", 45), ("60m", 60)]:
            ctk.CTkButton(
                pf, text=label, font=ctk.CTkFont(size=12),
                width=56, height=28,
                fg_color="#1a1a2e", hover_color="#2a2a4e",
                corner_radius=14,
                command=lambda m=mins: self._set_preset(m)
            ).pack(side="left", padx=3)

        # Custom time
        cf = ctk.CTkFrame(parent, fg_color="transparent")
        cf.pack(pady=(0, 14))
        ctk.CTkLabel(cf, text="Custom (min):",
                     font=ctk.CTkFont(size=12), text_color="#666666").pack(side="left", padx=(0, 6))
        self.custom_entry = ctk.CTkEntry(
            cf, width=60, height=28, font=ctk.CTkFont(size=12),
            fg_color="#1a1a2e", border_color="#2a2a4e", placeholder_text="25"
        )
        self.custom_entry.pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            cf, text="Set", width=46, height=28,
            font=ctk.CTkFont(size=12),
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=8,
            command=self._set_custom
        ).pack(side="left")

        # Control buttons + Pomodoro toggle
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.pack(pady=(0, 8))

        self.start_btn = ctk.CTkButton(
            ctrl, text="▶  Start",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=120, height=44,
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=22,
            command=self._toggle_timer
        )
        self.start_btn.pack(side="left", padx=8)

        self.reset_btn = ctk.CTkButton(
            ctrl, text="↺  Reset",
            font=ctk.CTkFont(size=14),
            width=100, height=44,
            fg_color="#1e1e1e", hover_color="#2e2e2e", corner_radius=22,
            command=self._reset_timer
        )
        self.reset_btn.pack(side="left", padx=8)

        self.pomo_btn = ctk.CTkButton(
            ctrl, text="🍅  Pomodoro",
            font=ctk.CTkFont(size=13),
            width=120, height=44,
            fg_color="#1e1e1e", hover_color="#2e1e1e", corner_radius=22,
            command=self._toggle_pomodoro
        )
        self.pomo_btn.pack(side="left", padx=8)

        # Session dots
        self.session_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.session_frame.pack(pady=(4, 0))
        self._update_session_dots()

    def _build_task_panel(self, parent):
        ctk.CTkLabel(
            parent, text="TASKS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#555588"
        ).pack(pady=(14, 8))

        # Add task row
        add_row = ctk.CTkFrame(parent, fg_color="transparent")
        add_row.pack(fill="x", padx=12, pady=(0, 8))

        self.task_entry = ctk.CTkEntry(
            add_row, placeholder_text="Add a task...",
            font=ctk.CTkFont(size=12),
            fg_color="#13131f", border_color="#2a2a4a",
            height=30
        )
        self.task_entry.pack(side="left", expand=True, fill="x", padx=(0, 6))
        self.task_entry.bind("<Return>", lambda e: self._add_task())

        ctk.CTkButton(
            add_row, text="+", width=30, height=30,
            font=ctk.CTkFont(size=16),
            fg_color="#5b8dee", hover_color="#3a6ccc",
            corner_radius=8,
            command=self._add_task
        ).pack(side="left")

        # Scrollable task list
        self.task_list = ctk.CTkScrollableFrame(
            parent, fg_color="transparent",
            scrollbar_button_color="#2a2a4a"
        )
        self.task_list.pack(expand=True, fill="both", padx=8, pady=(0, 10))

        # Clear done button
        ctk.CTkButton(
            parent, text="Clear done",
            font=ctk.CTkFont(size=11),
            height=26, width=90,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._clear_done_tasks
        ).pack(pady=(0, 10))

    # ═══════════════════════════════════════════════════════════════
    # TIMER
    # ═══════════════════════════════════════════════════════════════

    def _fmt(self, secs):
        m, s = divmod(max(0, secs), 60)
        return f"{m:02d}:{s:02d}"

    def _toggle_timer(self):
        if self.running:
            self._pause_timer()
        else:
            self._start_timer()

    def _start_timer(self):
        if self.remaining <= 0:
            return
        self.running = True
        self.start_btn.configure(text="⏸  Pause")
        self._stop_event.clear()
        self.timer_thread = threading.Thread(target=self._tick, daemon=True)
        self.timer_thread.start()

    def _pause_timer(self):
        self.running = False
        self._stop_event.set()
        self.start_btn.configure(text="▶  Resume")

    def _reset_timer(self):
        self._stop_event.set()
        self.running = False
        if self.pomo_on:
            self.pomo_step = 0
            self._apply_pomo_step()
        else:
            self.remaining = self.total_seconds
            self.after(0, self._update_display)
        self.start_btn.configure(text="▶  Start")

    def _tick(self):
        last = time.monotonic()
        while not self._stop_event.is_set() and self.remaining > 0:
            now = time.monotonic()
            if now - last >= 1.0:
                self.remaining -= 1
                last = now
                self.after(0, self._update_display)
            time.sleep(0.05)
        if self.remaining <= 0:
            self.after(0, self._on_complete)

    def _update_display(self):
        self.timer_display.configure(text=self._fmt(self.remaining))
        ratio = self.remaining / self.total_seconds if self.total_seconds > 0 else 0
        self.progress.set(ratio)

        if self.remaining <= 60 and self.running:
            self.timer_display.configure(text_color="#ff6b6b")
            self.progress.configure(progress_color="#ff6b6b")
        elif self.remaining <= 300 and self.running:
            self.timer_display.configure(text_color="#ffcc00")
            self.progress.configure(progress_color="#ffcc00")
        else:
            self.timer_display.configure(text_color="#ffffff")
            self.progress.configure(progress_color="#5b8dee")

    def _on_complete(self):
        self.running = False
        self.start_btn.configure(text="▶  Start")
        self.timer_display.configure(text="DONE!", text_color="#5b8dee")
        self.progress.set(0)
        self.session_count += 1
        self._update_session_dots()
        self._flash_done()
        self._play_done_sound()

        if self.pomo_on:
            self.after(2000, self._advance_pomodoro)

    def _flash_done(self, count=0):
        if count >= 6:
            return
        color = "#5b8dee" if count % 2 == 0 else "#ffffff"
        self.timer_display.configure(text_color=color)
        self.after(350, lambda: self._flash_done(count + 1))

    def _set_preset(self, mins):
        self.pomo_on = False
        self.pomo_btn.configure(fg_color="#1e1e1e")
        self.pomo_label.configure(text="")
        self.total_seconds = mins * 60
        self.remaining = self.total_seconds
        self._stop_event.set()
        self.running = False
        self.start_btn.configure(text="▶  Start")
        self._update_display()

    def _set_custom(self):
        val = self.custom_entry.get().strip()
        try:
            mins = float(val)
            if 0.5 <= mins <= 999:
                self.pomo_on = False
                self.pomo_btn.configure(fg_color="#1e1e1e")
                self.pomo_label.configure(text="")
                self.total_seconds = int(mins * 60)
                self.remaining = self.total_seconds
                self._stop_event.set()
                self.running = False
                self.start_btn.configure(text="▶  Start")
                self._update_display()
        except ValueError:
            pass

    def _update_session_dots(self):
        for w in self.session_dots:
            w.destroy()
        self.session_dots.clear()
        for _ in range(min(self.session_count, 8)):
            dot = ctk.CTkLabel(
                self.session_frame, text="●",
                font=ctk.CTkFont(size=12), text_color="#5b8dee"
            )
            dot.pack(side="left", padx=2)
            self.session_dots.append(dot)

    # ═══════════════════════════════════════════════════════════════
    # SOUND
    # ═══════════════════════════════════════════════════════════════

    def _play_done_sound(self):
        def _sound():
            try:
                sys_name = platform.system()
                if sys_name == "Windows":
                    import winsound
                    for freq, dur in [(880, 180), (1100, 180), (1320, 300)]:
                        winsound.Beep(freq, dur)
                        time.sleep(0.05)
                elif sys_name == "Darwin":
                    os.system("afplay /System/Library/Sounds/Glass.aiff")
                else:
                    os.system("paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null")
            except Exception:
                self.after(0, self.bell)
        threading.Thread(target=_sound, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════
    # POMODORO
    # ═══════════════════════════════════════════════════════════════

    def _toggle_pomodoro(self):
        self.pomo_on = not self.pomo_on
        if self.pomo_on:
            self.pomo_step = 0
            self.pomo_btn.configure(fg_color="#7a2020", hover_color="#8a3030")
            self._stop_event.set()
            self.running = False
            self.start_btn.configure(text="▶  Start")
            self._apply_pomo_step()
        else:
            self.pomo_btn.configure(fg_color="#1e1e1e", hover_color="#2e1e1e")
            self.pomo_label.configure(text="")

    def _apply_pomo_step(self):
        secs = POMO_SEQ[self.pomo_step % len(POMO_SEQ)]
        label = POMO_LABELS[self.pomo_step % len(POMO_LABELS)]
        self.total_seconds = secs
        self.remaining = secs
        self.pomo_label.configure(text=f"🍅  {label}  ({self.pomo_step + 1}/{len(POMO_SEQ)})")
        self._update_display()

    def _advance_pomodoro(self):
        self.pomo_step = (self.pomo_step + 1) % len(POMO_SEQ)
        self._apply_pomo_step()
        # Show a brief banner
        label = POMO_LABELS[self.pomo_step % len(POMO_LABELS)]
        self._show_banner(f"Next: {label} — press Start")

    def _show_banner(self, msg):
        banner = ctk.CTkLabel(
            self, text=msg,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#5b8dee", text_color="#ffffff",
            corner_radius=8, padx=16, pady=8
        )
        banner.place(relx=0.5, rely=0.12, anchor="center")
        self.after(3000, banner.destroy)

    # ═══════════════════════════════════════════════════════════════
    # TASKS
    # ═══════════════════════════════════════════════════════════════

    def _toggle_tasks(self):
        self.tasks_visible = not self.tasks_visible
        if self.tasks_visible:
            self.task_panel.pack(side="right", fill="y", padx=(10, 0), ipadx=4)
            self.task_panel.configure(width=220)
            self._build_task_panel(self.task_panel)
            self.tasks_btn.configure(fg_color="#5b8dee")
        else:
            for w in self.task_panel.winfo_children():
                w.destroy()
            self.task_panel.pack_forget()
            self.tasks_btn.configure(fg_color="#1e1e1e")

    def _add_task(self):
        text = self.task_entry.get().strip()
        if not text:
            return
        self.task_entry.delete(0, "end")

        done_var = tk.BooleanVar(value=False)

        row = ctk.CTkFrame(self.task_list, fg_color="#13131f", corner_radius=8)
        row.pack(fill="x", pady=3, padx=2)

        cb = ctk.CTkCheckBox(
            row, text=text,
            font=ctk.CTkFont(size=12),
            text_color="#cccccc",
            fg_color="#5b8dee", hover_color="#3a6ccc",
            border_color="#2a2a4a",
            variable=done_var,
            command=lambda v=done_var, c=None, t=text, r=row: self._on_task_toggle(v, r),
            wraplength=140
        )
        cb.pack(side="left", padx=(8, 4), pady=6, expand=True, anchor="w")

        del_btn = ctk.CTkButton(
            row, text="×", width=24, height=24,
            font=ctk.CTkFont(size=14),
            fg_color="transparent", hover_color="#2a1a1a",
            text_color="#555555",
            command=lambda r=row, task=None: self._delete_task(r)
        )
        del_btn.pack(side="right", padx=4)

        task_data = {"text": text, "done": done_var, "frame": row, "cb": cb}
        self.tasks.append(task_data)

    def _on_task_toggle(self, done_var, row):
        # Dim row when checked
        if done_var.get():
            row.configure(fg_color="#0d0d14")
            for child in row.winfo_children():
                if isinstance(child, ctk.CTkCheckBox):
                    child.configure(text_color="#444444")
        else:
            row.configure(fg_color="#13131f")
            for child in row.winfo_children():
                if isinstance(child, ctk.CTkCheckBox):
                    child.configure(text_color="#cccccc")

    def _delete_task(self, row):
        self.tasks = [t for t in self.tasks if t["frame"] is not row]
        row.destroy()

    def _clear_done_tasks(self):
        to_remove = [t for t in self.tasks if t["done"].get()]
        for t in to_remove:
            t["frame"].destroy()
        self.tasks = [t for t in self.tasks if not t["done"].get()]

    # ═══════════════════════════════════════════════════════════════
    # BACKGROUND
    # ═══════════════════════════════════════════════════════════════

    def _on_canvas_resize(self, event=None):
        if self.use_image_bg and self.bg_image:
            self._draw_image_bg()
        else:
            self._apply_gradient_bg(self.current_gradient)

    def _apply_gradient_bg(self, colors):
        self.current_gradient = colors
        self.use_image_bg = False
        w = self.winfo_width() or 960
        h = self.winfo_height() or 660
        img = self._make_gradient(w, h, colors)
        self._set_canvas_bg(img)

    def _make_gradient(self, w, h, colors):
        img = Image.new("RGB", (max(w, 1), max(h, 1)))
        draw = ImageDraw.Draw(img)
        c1 = self._hex_to_rgb(colors[0])
        c2 = self._hex_to_rgb(colors[-1])
        for y in range(h):
            t = y / max(h - 1, 1)
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            draw.line([(0, y), (w, y)], fill=(r, g, b))
        return img

    def _hex_to_rgb(self, hex_str):
        h = hex_str.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _draw_image_bg(self):
        if not self.bg_image:
            return
        w = self.winfo_width() or 960
        h = self.winfo_height() or 660
        img = self.bg_image.copy().resize((w, h), Image.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(radius=4))
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 130))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        self._set_canvas_bg(img)

    def _set_canvas_bg(self, img):
        self.bg_photo = ImageTk.PhotoImage(img)
        self.canvas.delete("bg")
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_photo, tags="bg")
        self.canvas.lower("bg")

    def _open_bg_panel(self):
        if self.bg_panel and self.bg_panel.winfo_exists():
            self.bg_panel.focus()
            return

        self.bg_panel = ctk.CTkToplevel(self)
        self.bg_panel.title("Choose Background")
        self.bg_panel.geometry("480x340")
        self.bg_panel.resizable(False, False)
        self.bg_panel.grab_set()

        ctk.CTkLabel(self.bg_panel, text="Presets",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(16, 8))

        grid = ctk.CTkFrame(self.bg_panel, fg_color="transparent")
        grid.pack(padx=20, fill="x")

        for i, (grad, name) in enumerate(zip(PRESET_GRADIENTS, PRESET_NAMES)):
            row, col = divmod(i, 4)
            ctk.CTkButton(
                grid, text=name, font=ctk.CTkFont(size=11),
                width=96, height=52,
                fg_color=grad[1], hover_color=grad[0], corner_radius=8,
                command=lambda g=grad: self._apply_gradient_bg(g)
            ).grid(row=row, column=col, padx=4, pady=4)

        ctk.CTkSeparator(self.bg_panel).pack(fill="x", padx=20, pady=10)

        btn_row = ctk.CTkFrame(self.bg_panel, fg_color="transparent")
        btn_row.pack()

        ctk.CTkButton(btn_row, text="📁  Load Image", width=140, height=34,
                      command=self._load_image_bg).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="🎨  Custom Color", width=140, height=34,
                      command=self._pick_custom_color).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="↺  Reset", width=80, height=34,
                      fg_color="#333333", hover_color="#444444",
                      command=lambda: self._apply_gradient_bg(PRESET_GRADIENTS[0])
                      ).pack(side="left", padx=6)

    def _load_image_bg(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp")]
        )
        if path:
            self.bg_image = Image.open(path)
            self.use_image_bg = True
            self._draw_image_bg()

    def _pick_custom_color(self):
        color = colorchooser.askcolor(color="#141e30")[1]
        if color:
            self._apply_gradient_bg([color, color, color])

    # ═══════════════════════════════════════════════════════════════
    # FOCUS MODE
    # ═══════════════════════════════════════════════════════════════

    def _toggle_focus_mode(self):
        self.focus_mode = not self.focus_mode
        if self.focus_mode:
            self.attributes("-fullscreen", True)
            self.focus_btn.configure(text="⬜  Exit Focus",
                                     fg_color="#5b8dee", hover_color="#3a6ccc")
            self.bg_btn.configure(state="disabled")
            self.tasks_btn.configure(state="disabled")
            self.title_label.configure(text="")
        else:
            self.attributes("-fullscreen", False)
            self.geometry("960x660")
            self.focus_btn.configure(text="⬛  Focus Mode",
                                     fg_color="#1e1e1e", hover_color="#2e2e2e")
            self.bg_btn.configure(state="normal")
            self.tasks_btn.configure(state="normal")
            self.title_label.configure(text="FOCUS TIMER")
        self._on_canvas_resize()

    # ═══════════════════════════════════════════════════════════════
    # QUOTES
    # ═══════════════════════════════════════════════════════════════

    def _start_quote_cycle(self):
        self._fade_in_quote()

    def _fade_in_quote(self, alpha=0):
        if alpha > 100:
            self._quote_job = self.after(8000, self._fade_out_quote)
            return
        gray = int(170 * (alpha / 100))
        self.quote_label.configure(text_color=f"#{gray:02x}{gray:02x}{gray:02x}")
        self.after(18, lambda: self._fade_in_quote(alpha + 5))

    def _fade_out_quote(self, alpha=100):
        if alpha < 0:
            self.quote_index = (self.quote_index + 1) % len(QUOTES)
            self.quote_label.configure(text=QUOTES[self.quote_index])
            self._fade_in_quote()
            return
        gray = int(170 * (alpha / 100))
        self.quote_label.configure(text_color=f"#{gray:02x}{gray:02x}{gray:02x}")
        self.after(18, lambda: self._fade_out_quote(alpha - 5))

    def on_close(self):
        self._stop_event.set()
        self.destroy()


if __name__ == "__main__":
    app = FocusTimerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
