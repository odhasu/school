import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, colorchooser
from PIL import Image, ImageTk, ImageFilter, ImageDraw
import time, threading, os, platform, random, json, datetime
from pathlib import Path

TASKS_FILE = Path.home() / ".focus_timer_tasks.json"
PLAN_FILE  = Path.home() / ".focus_timer_plan.json"

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

BG_PRESETS = [
    # ── Dark gradients ──
    {"name": "Night Sky",  "c1": "#0f0c29", "c2": "#302b63", "light": False},
    {"name": "Dark Ocean", "c1": "#141e30", "c2": "#243b55", "light": False},
    {"name": "Midnight",   "c1": "#1a1a2e", "c2": "#0f3460", "light": False},
    {"name": "Dark Teal",  "c1": "#0f2027", "c2": "#2c5364", "light": False},
    {"name": "Violet",     "c1": "#1f0036", "c2": "#3d0066", "light": False},
    {"name": "Ember",      "c1": "#1a0000", "c2": "#3d1500", "light": False},
    # ── Black / Grey / White ──
    {"name": "Pure Black", "c1": "#000000", "c2": "#0a0a0a", "light": False},
    {"name": "Charcoal",   "c1": "#181818", "c2": "#2a2a2a", "light": False},
    {"name": "Dark Grey",  "c1": "#2e2e2e", "c2": "#3c3c3c", "light": False},
    {"name": "Mid Grey",   "c1": "#505050", "c2": "#606060", "light": False},
    {"name": "Cool Grey",  "c1": "#787878", "c2": "#909090", "light": True},
    {"name": "Silver",     "c1": "#b0b0b0", "c2": "#c8c8c8", "light": True},
    {"name": "Off White",  "c1": "#e0e0e0", "c2": "#eeeeee", "light": True},
    {"name": "Pure White", "c1": "#f8f8f8", "c2": "#ffffff", "light": True},
]

POMO_SEQ    = [25*60, 5*60, 25*60, 5*60, 25*60, 5*60, 25*60, 15*60]
POMO_LABELS = ["Focus","Short Break","Focus","Short Break",
               "Focus","Short Break","Focus","Long Break!"]

MEM_ICONS = ["🎯","🎨","🎮","🎵","🌟","🚀","🦄","🎃"]

SNAKE_ROWS, SNAKE_COLS, SNAKE_CELL = 18, 24, 18


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Focus Timer")
        self.geometry("1000x690")
        self.minsize(760, 560)

        # timer state
        self.total_seconds = 25*60
        self.remaining     = self.total_seconds
        self.running       = False
        self._stop_event   = threading.Event()
        self.session_count = 0
        self.session_dots  = []

        # pomodoro
        self.pomo_on   = False
        self.pomo_step = 0

        # bg
        self.bg_src     = None
        self.bg_photo   = None
        self.cur_preset = BG_PRESETS[0]
        self.use_img_bg = False
        self.light_bg   = False

        # ui
        self.current_page  = "timer"
        self.tasks_visible = False
        self.focus_mode    = False
        self.tasks         = self._load_tasks()
        self.plan_tasks    = self._load_plan_tasks()
        self.quote_index   = 0
        self._quote_job    = None

        # snake
        self.snake_running  = False
        self._snake_job     = None
        self.snake_body     = []
        self.snake_dir      = (0, 1)
        self.snake_next_dir = (0, 1)
        self.snake_food     = (0, 0)
        self.snake_score    = 0

        # reaction
        self.react_state    = "idle"   # idle / waiting / ready / result
        self._react_job     = None
        self.react_start_t  = 0.0

        # memory
        self.mem_board      = []
        self.mem_matched    = []
        self.mem_btns       = []
        self.mem_first      = None
        self.mem_locked     = False
        self.mem_moves      = 0
        self.mem_start_time = None
        self._mem_timer_job = None

        self._build_ui()
        self._apply_preset(BG_PRESETS[0], init=True)
        self._start_quote_cycle()
        self.bind_all("<KeyPress>", self._on_key)

    # ══════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.canvas.bind("<Configure>", lambda e: self._redraw_bg())

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ── top bar ─────────────────────────────────────────────────
        top = ctk.CTkFrame(wrap, fg_color="transparent")
        top.pack(fill="x", padx=22, pady=(10, 0))

        self.title_lbl = ctk.CTkLabel(top, text="FOCUS TIMER",
            font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color="#555555")
        self.title_lbl.pack(side="left")

        # page nav (center)
        nav = ctk.CTkFrame(top, fg_color="transparent")
        nav.pack(side="left", expand=True)

        self.nav_timer = ctk.CTkButton(nav, text="Timer",
            font=ctk.CTkFont(size=13), width=88, height=30,
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=15,
            command=lambda: self._show_page("timer"))
        self.nav_timer.pack(side="left", padx=4)

        self.nav_games = ctk.CTkButton(nav, text="🎮 Games",
            font=ctk.CTkFont(size=13), width=100, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e", corner_radius=15,
            command=lambda: self._show_page("games"))
        self.nav_games.pack(side="left", padx=4)

        self.nav_plan = ctk.CTkButton(nav, text="📅 Plan",
            font=ctk.CTkFont(size=13), width=88, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e", corner_radius=15,
            command=lambda: self._show_page("plan"))
        self.nav_plan.pack(side="left", padx=4)

        # right buttons
        self.focus_btn = ctk.CTkButton(top, text="⬛ Focus",
            font=ctk.CTkFont(size=12), width=82, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._toggle_focus)
        self.focus_btn.pack(side="right")

        self.bg_btn = ctk.CTkButton(top, text="🎨 BG",
            font=ctk.CTkFont(size=12), width=64, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._open_bg_panel)
        self.bg_btn.pack(side="right", padx=(0,5))

        self.tasks_btn = ctk.CTkButton(top, text="☑ Tasks",
            font=ctk.CTkFont(size=12), width=72, height=30,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._toggle_tasks)
        self.tasks_btn.pack(side="right", padx=(0,5))

        # ── body ────────────────────────────────────────────────────
        body = ctk.CTkFrame(wrap, fg_color="transparent")
        body.pack(expand=True, fill="both", padx=22, pady=(6, 12))

        # content (swappable pages)
        self.content = ctk.CTkFrame(body, fg_color="transparent")
        self.content.pack(side="left", expand=True, fill="both")

        # task side panel (hidden initially)
        self.task_panel = ctk.CTkFrame(body, fg_color="#0d0d1a",
            corner_radius=12, border_width=1, border_color="#1e1e3a", width=210)

        # ── build both pages ────────────────────────────────────────
        self.timer_page = ctk.CTkFrame(self.content, fg_color="transparent")
        self.games_page = ctk.CTkFrame(self.content, fg_color="transparent")
        self.plan_page  = ctk.CTkFrame(self.content, fg_color="transparent")
        self._build_timer_page(self.timer_page)
        self._build_games_page(self.games_page)
        self._build_plan_page(self.plan_page)
        self.timer_page.pack(expand=True, fill="both")

        self.bg_panel_win = None

    # ── TIMER PAGE ──────────────────────────────────────────────────
    def _build_timer_page(self, p):
        self.quote_lbl = ctk.CTkLabel(p, text=QUOTES[0],
            font=ctk.CTkFont("Segoe UI", 14, slant="italic"),
            text_color="#888888", wraplength=460)
        self.quote_lbl.pack(pady=(18, 0))

        self.pomo_lbl = ctk.CTkLabel(p, text="",
            font=ctk.CTkFont(size=11), text_color="#5b8dee")
        self.pomo_lbl.pack(pady=(2, 0))

        self.timer_lbl = ctk.CTkLabel(p, text=self._fmt(self.remaining),
            font=ctk.CTkFont("Segoe UI", 92, "bold"), text_color="#ffffff")
        self.timer_lbl.pack(pady=(4, 0))

        self.progress = ctk.CTkProgressBar(p, width=400, height=6,
            fg_color="#1a1a2e", progress_color="#5b8dee", corner_radius=3)
        self.progress.set(1.0)
        self.progress.pack(pady=(4, 16))

        # presets
        pf = ctk.CTkFrame(p, fg_color="transparent"); pf.pack(pady=(0, 8))
        for lbl, m in [("5m",5),("10m",10),("25m",25),("45m",45),("60m",60)]:
            ctk.CTkButton(pf, text=lbl, font=ctk.CTkFont(size=12),
                width=54, height=26, fg_color="#1a1a2e", hover_color="#2a2a4e",
                corner_radius=13, command=lambda m=m: self._set_preset(m)
            ).pack(side="left", padx=3)

        # custom time
        cf = ctk.CTkFrame(p, fg_color="transparent"); cf.pack(pady=(0, 12))
        ctk.CTkLabel(cf, text="Custom min:", font=ctk.CTkFont(size=12),
            text_color="#555555").pack(side="left", padx=(0,5))
        self.custom_ent = ctk.CTkEntry(cf, width=58, height=26,
            font=ctk.CTkFont(size=12), fg_color="#1a1a2e",
            border_color="#2a2a4e", placeholder_text="25")
        self.custom_ent.pack(side="left", padx=(0,5))
        ctk.CTkButton(cf, text="Set", width=44, height=26,
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=7,
            command=self._set_custom).pack(side="left")

        # controls
        ctrl = ctk.CTkFrame(p, fg_color="transparent"); ctrl.pack(pady=(0, 6))
        self.start_btn = ctk.CTkButton(ctrl, text="▶  Start",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=116, height=42, fg_color="#5b8dee", hover_color="#3a6ccc",
            corner_radius=21, command=self._toggle_timer)
        self.start_btn.pack(side="left", padx=7)

        ctk.CTkButton(ctrl, text="↺  Reset",
            font=ctk.CTkFont(size=13), width=100, height=42,
            fg_color="#1e1e1e", hover_color="#2e2e2e", corner_radius=21,
            command=self._reset_timer).pack(side="left", padx=7)

        self.pomo_btn = ctk.CTkButton(ctrl, text="🍅 Pomodoro",
            font=ctk.CTkFont(size=13), width=118, height=42,
            fg_color="#1e1e1e", hover_color="#2e1818", corner_radius=21,
            command=self._toggle_pomodoro)
        self.pomo_btn.pack(side="left", padx=7)

        # session dots
        self.dot_frame = ctk.CTkFrame(p, fg_color="transparent")
        self.dot_frame.pack(pady=(4, 0))
        self._refresh_dots()

    # ── GAMES PAGE ──────────────────────────────────────────────────
    def _build_games_page(self, p):
        # sub-nav
        gnav = ctk.CTkFrame(p, fg_color="transparent")
        gnav.pack(pady=(10, 8))
        self.game_btns = {}
        for key, label in [("snake","🐍 Snake"),("react","⚡ Reaction"),("memory","🃏 Memory")]:
            b = ctk.CTkButton(gnav, text=label, font=ctk.CTkFont(size=12),
                width=110, height=30,
                fg_color="#5b8dee" if key=="snake" else "#1e1e1e",
                hover_color="#3a6ccc" if key=="snake" else "#2e2e2e",
                corner_radius=15,
                command=lambda k=key: self._show_game(k))
            b.pack(side="left", padx=5)
            self.game_btns[key] = b

        # game frames
        self.game_frames = {}
        for key in ("snake","react","memory"):
            f = ctk.CTkFrame(p, fg_color="transparent")
            self.game_frames[key] = f

        self._build_snake(self.game_frames["snake"])
        self._build_reaction(self.game_frames["react"])
        self._build_memory(self.game_frames["memory"])

        self.active_game = "snake"
        self.game_frames["snake"].pack(expand=True, fill="both")

    # ── SNAKE ────────────────────────────────────────────────────────
    def _build_snake(self, p):
        info = ctk.CTkFrame(p, fg_color="transparent"); info.pack(pady=(4,4))
        self.snake_score_lbl = ctk.CTkLabel(info, text="Score: 0",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#5b8dee")
        self.snake_score_lbl.pack(side="left", padx=12)
        self.snake_hi_lbl = ctk.CTkLabel(info, text="Best: 0",
            font=ctk.CTkFont(size=13), text_color="#555555")
        self.snake_hi_lbl.pack(side="left", padx=12)
        self.snake_status = ctk.CTkLabel(info, text="Press Start",
            font=ctk.CTkFont(size=12), text_color="#666666")
        self.snake_status.pack(side="left", padx=12)

        cw = SNAKE_COLS * SNAKE_CELL
        ch = SNAKE_ROWS * SNAKE_CELL
        canvas_wrap = ctk.CTkFrame(p, fg_color="#0a0a14",
            corner_radius=10, border_width=1, border_color="#1e1e3a")
        canvas_wrap.pack()
        self.snake_cv = tk.Canvas(canvas_wrap, width=cw, height=ch,
            bg="#0a0a14", highlightthickness=0)
        self.snake_cv.pack(padx=2, pady=2)
        self.snake_hi = 0

        btns = ctk.CTkFrame(p, fg_color="transparent"); btns.pack(pady=(6,0))
        self.snake_start_btn = ctk.CTkButton(btns, text="▶ Start",
            font=ctk.CTkFont(size=13), width=90, height=32,
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=16,
            command=self._snake_toggle)
        self.snake_start_btn.pack(side="left", padx=6)
        ctk.CTkButton(btns, text="↺ Reset",
            font=ctk.CTkFont(size=13), width=80, height=32,
            fg_color="#1e1e1e", hover_color="#2e2e2e", corner_radius=16,
            command=self._snake_reset).pack(side="left", padx=6)
        ctk.CTkLabel(btns, text="Arrow keys / WASD",
            font=ctk.CTkFont(size=11), text_color="#444444").pack(side="left", padx=8)

        self._snake_reset()

    def _snake_reset(self):
        if self._snake_job:
            self.after_cancel(self._snake_job)
            self._snake_job = None
        self.snake_running = False
        mid_r = SNAKE_ROWS // 2
        mid_c = SNAKE_COLS // 2
        self.snake_body = [(mid_r, mid_c), (mid_r, mid_c-1), (mid_r, mid_c-2)]
        self.snake_dir = (0, 1)
        self.snake_next_dir = (0, 1)
        self.snake_score = 0
        self.snake_score_lbl.configure(text="Score: 0")
        self.snake_status.configure(text="Press Start")
        self.snake_start_btn.configure(text="▶ Start")
        self._snake_place_food()
        self._snake_draw()

    def _snake_toggle(self):
        if self.snake_running:
            self.snake_running = False
            self.snake_start_btn.configure(text="▶ Start")
            self.snake_status.configure(text="Paused")
        else:
            self.snake_running = True
            self.snake_start_btn.configure(text="⏸ Pause")
            self.snake_status.configure(text="Playing")
            self._snake_loop()

    def _snake_loop(self):
        if not self.snake_running:
            return
        dr, dc = self.snake_next_dir
        self.snake_dir = (dr, dc)
        hr, hc = self.snake_body[0]
        nr, nc = hr + dr, hc + dc

        if not (0 <= nr < SNAKE_ROWS and 0 <= nc < SNAKE_COLS) or (nr,nc) in self.snake_body:
            self._snake_game_over()
            return

        self.snake_body.insert(0, (nr, nc))
        if (nr, nc) == self.snake_food:
            self.snake_score += 1
            self.snake_score_lbl.configure(text=f"Score: {self.snake_score}")
            if self.snake_score > self.snake_hi:
                self.snake_hi = self.snake_score
                self.snake_hi_lbl.configure(text=f"Best: {self.snake_hi}")
            self._snake_place_food()
        else:
            self.snake_body.pop()

        self._snake_draw()
        speed = max(75, 220 - self.snake_score * 7)
        self._snake_job = self.after(speed, self._snake_loop)

    def _snake_place_food(self):
        empty = [(r,c) for r in range(SNAKE_ROWS) for c in range(SNAKE_COLS)
                 if (r,c) not in self.snake_body]
        self.snake_food = random.choice(empty) if empty else (0,0)

    def _snake_draw(self):
        cv = self.snake_cv
        cv.delete("all")
        s = SNAKE_CELL
        # grid dots
        for r in range(SNAKE_ROWS):
            for c in range(SNAKE_COLS):
                cv.create_rectangle(c*s+s//2-1, r*s+s//2-1,
                    c*s+s//2+1, r*s+s//2+1, fill="#141428", outline="")
        # food
        fr, fc = self.snake_food
        cv.create_oval(fc*s+3, fr*s+3, fc*s+s-3, fr*s+s-3,
            fill="#ff4444", outline="#ff8888", width=1)
        # snake
        for i, (r,c) in enumerate(self.snake_body):
            color = "#5b8dee" if i == 0 else "#2a4a8a"
            cv.create_oval(c*s+2, r*s+2, c*s+s-2, r*s+s-2,
                fill=color, outline="", width=0)
        # score overlay
        cv.create_text(6, 6, anchor="nw", text=f"{self.snake_score}",
            fill="#5b8dee", font=("Segoe UI", 11, "bold"))

    def _snake_game_over(self):
        self.snake_running = False
        self.snake_start_btn.configure(text="▶ Start")
        self.snake_status.configure(text=f"Game Over! Score: {self.snake_score}")
        cv = self.snake_cv
        cw = SNAKE_COLS * SNAKE_CELL
        ch = SNAKE_ROWS * SNAKE_CELL
        cv.create_rectangle(cw//2-90, ch//2-22, cw//2+90, ch//2+22,
            fill="#0a0a14", outline="#5b8dee", width=1)
        cv.create_text(cw//2, ch//2, text=f"GAME OVER  Score: {self.snake_score}",
            fill="#ff4444", font=("Segoe UI", 13, "bold"))

    # ── REACTION ─────────────────────────────────────────────────────
    def _build_reaction(self, p):
        ctk.CTkLabel(p, text="Click the button the moment it turns green!",
            font=ctk.CTkFont(size=13), text_color="#888888").pack(pady=(20, 12))

        self.react_btn = ctk.CTkButton(p, text="Ready?",
            font=ctk.CTkFont(size=18, weight="bold"),
            width=220, height=220,
            fg_color="#1e1e1e", hover_color="#1e1e1e",
            corner_radius=110,
            command=self._react_click)
        self.react_btn.pack()

        self.react_result = ctk.CTkLabel(p, text="",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#5b8dee")
        self.react_result.pack(pady=(14, 4))

        self.react_stats = ctk.CTkLabel(p, text="Best: —   Avg: —",
            font=ctk.CTkFont(size=12), text_color="#444444")
        self.react_stats.pack()

        self.react_times = []
        self.react_best  = None

        ctk.CTkButton(p, text="↺ Reset stats",
            font=ctk.CTkFont(size=11), width=100, height=26,
            fg_color="#1e1e1e", hover_color="#2e2e2e",
            command=self._react_reset_stats).pack(pady=(10,0))

    def _react_click(self):
        if self.react_state == "idle":
            self.react_state = "waiting"
            self.react_btn.configure(text="Wait...", fg_color="#2a2a2a", hover_color="#2a2a2a")
            self.react_result.configure(text="")
            delay = random.randint(1500, 4500)
            self._react_job = self.after(delay, self._react_go)

        elif self.react_state == "waiting":
            if self._react_job:
                self.after_cancel(self._react_job)
            self.react_state = "idle"
            self.react_btn.configure(text="Ready?", fg_color="#1e1e1e", hover_color="#1e1e1e")
            self.react_result.configure(text="Too early! Try again.", text_color="#ff6b6b")

        elif self.react_state == "ready":
            ms = int((time.monotonic() - self.react_start_t) * 1000)
            self.react_times.append(ms)
            if self.react_best is None or ms < self.react_best:
                self.react_best = ms
            avg = int(sum(self.react_times) / len(self.react_times))
            self.react_stats.configure(
                text=f"Best: {self.react_best} ms   Avg: {avg} ms")

            if ms < 200:
                grade, color = "Insane! 🔥", "#ff4444"
            elif ms < 280:
                grade, color = "Excellent!", "#ffcc00"
            elif ms < 380:
                grade, color = "Good!", "#5b8dee"
            else:
                grade, color = "Keep practising", "#888888"

            self.react_result.configure(text=f"{ms} ms — {grade}", text_color=color)
            self.react_state = "idle"
            self.react_btn.configure(text="Ready?", fg_color="#1e1e1e", hover_color="#1e1e1e")

    def _react_go(self):
        self.react_state = "ready"
        self.react_start_t = time.monotonic()
        self.react_btn.configure(text="NOW!", fg_color="#22aa44", hover_color="#22aa44")

    def _react_reset_stats(self):
        self.react_times = []
        self.react_best  = None
        self.react_stats.configure(text="Best: —   Avg: —")
        self.react_result.configure(text="")
        if self.react_state != "idle":
            if self._react_job:
                self.after_cancel(self._react_job)
            self.react_state = "idle"
            self.react_btn.configure(text="Ready?", fg_color="#1e1e1e", hover_color="#1e1e1e")

    # ── MEMORY ───────────────────────────────────────────────────────
    def _build_memory(self, p):
        hdr = ctk.CTkFrame(p, fg_color="transparent"); hdr.pack(pady=(12,6))
        self.mem_moves_lbl = ctk.CTkLabel(hdr, text="Moves: 0",
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#5b8dee")
        self.mem_moves_lbl.pack(side="left", padx=10)
        self.mem_time_lbl = ctk.CTkLabel(hdr, text="Time: 0s",
            font=ctk.CTkFont(size=13), text_color="#666666")
        self.mem_time_lbl.pack(side="left", padx=10)
        self.mem_status_lbl = ctk.CTkLabel(hdr, text="Match all pairs!",
            font=ctk.CTkFont(size=12), text_color="#666666")
        self.mem_status_lbl.pack(side="left", padx=10)
        ctk.CTkButton(hdr, text="↺ New Game",
            font=ctk.CTkFont(size=12), width=96, height=28,
            fg_color="#1e1e1e", hover_color="#2e2e2e", corner_radius=14,
            command=self._mem_new_game).pack(side="left", padx=10)

        self.mem_grid = ctk.CTkFrame(p, fg_color="transparent")
        self.mem_grid.pack()
        self._mem_new_game()

    def _mem_new_game(self):
        for w in self.mem_grid.winfo_children():
            w.destroy()
        self.mem_btns   = []
        self.mem_first  = None
        self.mem_locked = False
        self.mem_moves  = 0
        self.mem_moves_lbl.configure(text="Moves: 0")
        self.mem_status_lbl.configure(text="Match all pairs!")
        self.mem_start_time = None
        if self._mem_timer_job:
            self.after_cancel(self._mem_timer_job)
            self._mem_timer_job = None
        self.mem_time_lbl.configure(text="Time: 0s")

        icons = (MEM_ICONS * 2)
        random.shuffle(icons)
        self.mem_board   = icons
        self.mem_matched = [False] * 16

        for i, icon in enumerate(icons):
            r, c = divmod(i, 4)
            b = ctk.CTkButton(self.mem_grid, text="?",
                font=ctk.CTkFont(size=20), width=70, height=70,
                fg_color="#1a1a2e", hover_color="#2a2a4e",
                corner_radius=10,
                command=lambda idx=i: self._mem_flip(idx))
            b.grid(row=r, column=c, padx=4, pady=4)
            self.mem_btns.append(b)

    def _mem_flip(self, idx):
        if self.mem_locked or self.mem_matched[idx]:
            return
        btn = self.mem_btns[idx]
        if self.mem_first is not None and self.mem_first == idx:
            return

        # start timer on very first card flip
        if self.mem_start_time is None:
            self.mem_start_time = time.monotonic()
            self._mem_tick_timer()

        btn.configure(text=self.mem_board[idx], fg_color="#2a2a4e")

        if self.mem_first is None:
            self.mem_first = idx
        else:
            self.mem_moves += 1
            self.mem_moves_lbl.configure(text=f"Moves: {self.mem_moves}")
            first = self.mem_first
            self.mem_first = None
            if self.mem_board[first] == self.mem_board[idx]:
                self.mem_matched[first] = True
                self.mem_matched[idx]   = True
                self.mem_btns[first].configure(fg_color="#1a3a1a", text_color="#44cc44")
                btn.configure(fg_color="#1a3a1a", text_color="#44cc44")
                if all(self.mem_matched):
                    # stop timer on win
                    if self._mem_timer_job:
                        self.after_cancel(self._mem_timer_job)
                        self._mem_timer_job = None
                    elapsed = int(time.monotonic() - self.mem_start_time)
                    self.mem_time_lbl.configure(text=f"Time: {elapsed}s")
                    self.mem_status_lbl.configure(
                        text=f"You won in {self.mem_moves} moves! 🎉")
            else:
                self.mem_locked = True
                self.after(800, lambda: self._mem_flip_back(first, idx))

    def _mem_flip_back(self, a, b):
        if not self.mem_matched[a]:
            self.mem_btns[a].configure(text="?", fg_color="#1a1a2e")
        if not self.mem_matched[b]:
            self.mem_btns[b].configure(text="?", fg_color="#1a1a2e")
        self.mem_locked = False

    def _mem_tick_timer(self):
        if self.mem_start_time is None or all(self.mem_matched):
            return
        elapsed = int(time.monotonic() - self.mem_start_time)
        self.mem_time_lbl.configure(text=f"Time: {elapsed}s")
        self._mem_timer_job = self.after(1000, self._mem_tick_timer)

    # ── GAME NAVIGATION ──────────────────────────────────────────────
    def _show_game(self, key):
        self.game_frames[self.active_game].pack_forget()
        self.active_game = key
        self.game_frames[key].pack(expand=True, fill="both")
        for k, b in self.game_btns.items():
            b.configure(
                fg_color="#5b8dee" if k==key else "#1e1e1e",
                hover_color="#3a6ccc" if k==key else "#2e2e2e")

    # ── PAGE NAVIGATION ──────────────────────────────────────────────
    def _show_page(self, page):
        if page == self.current_page:
            return
        # hide current
        if self.current_page == "timer":
            self.timer_page.pack_forget()
        elif self.current_page == "games":
            self.games_page.pack_forget()
        elif self.current_page == "plan":
            self.plan_page.pack_forget()
        # show new
        if page == "timer":
            self.timer_page.pack(expand=True, fill="both")
            self.nav_timer.configure(fg_color="#5b8dee", hover_color="#3a6ccc")
            self.nav_games.configure(fg_color="#1e1e1e", hover_color="#2e2e2e")
            self.nav_plan.configure(fg_color="#1e1e1e", hover_color="#2e2e2e")
        elif page == "games":
            self.games_page.pack(expand=True, fill="both")
            self.nav_games.configure(fg_color="#5b8dee", hover_color="#3a6ccc")
            self.nav_timer.configure(fg_color="#1e1e1e", hover_color="#2e2e2e")
            self.nav_plan.configure(fg_color="#1e1e1e", hover_color="#2e2e2e")
        elif page == "plan":
            self.plan_page.pack(expand=True, fill="both")
            self.nav_plan.configure(fg_color="#5b8dee", hover_color="#3a6ccc")
            self.nav_timer.configure(fg_color="#1e1e1e", hover_color="#2e2e2e")
            self.nav_games.configure(fg_color="#1e1e1e", hover_color="#2e2e2e")
            self._refresh_plan_page()
        self.current_page = page

    # ══════════════════════════════════════════════════════════════════
    # TIMER
    # ══════════════════════════════════════════════════════════════════

    def _fmt(self, s):
        m, s = divmod(max(0, s), 60)
        return f"{m:02d}:{s:02d}"

    def _toggle_timer(self):
        self._pause_timer() if self.running else self._start_timer()

    def _start_timer(self):
        if self.remaining <= 0:
            return
        self.running = True
        self.start_btn.configure(text="⏸  Pause")
        self._stop_event.clear()
        threading.Thread(target=self._tick, daemon=True).start()

    def _pause_timer(self):
        self.running = False
        self._stop_event.set()
        self.start_btn.configure(text="▶  Resume")

    def _reset_timer(self):
        self._stop_event.set()
        self.running = False
        self.remaining = POMO_SEQ[self.pomo_step] if self.pomo_on else self.total_seconds
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
        self.timer_lbl.configure(text=self._fmt(self.remaining))
        ratio = min(1.0, self.remaining / self.total_seconds) if self.total_seconds else 0
        self.progress.set(ratio)
        tc = "#ff6b6b" if self.remaining<=60 and self.running else \
             "#ffcc00" if self.remaining<=300 and self.running else \
             ("#111111" if self.light_bg else "#ffffff")
        pc = "#ff6b6b" if self.remaining<=60 and self.running else \
             "#ffcc00" if self.remaining<=300 and self.running else "#5b8dee"
        self.timer_lbl.configure(text_color=tc)
        self.progress.configure(progress_color=pc)

    def _on_complete(self):
        self.running = False
        self.start_btn.configure(text="▶  Start")
        self.timer_lbl.configure(text="DONE!", text_color="#5b8dee")
        self.progress.set(0)
        self.session_count += 1
        self._refresh_dots()
        self._flash_done()
        self._play_sound()
        if self.pomo_on:
            self.after(2000, self._pomo_advance)

    def _flash_done(self, n=0):
        if n >= 6:
            return
        self.timer_lbl.configure(text_color="#5b8dee" if n%2==0 else "#ffffff")
        self.after(350, lambda: self._flash_done(n+1))

    def _set_preset(self, mins):
        self.pomo_on = False
        self.pomo_btn.configure(fg_color="#1e1e1e")
        self.pomo_lbl.configure(text="")
        self.total_seconds = mins * 60
        self.remaining = self.total_seconds
        self._stop_event.set()
        self.running = False
        self.start_btn.configure(text="▶  Start")
        self._update_display()

    def _set_custom(self):
        try:
            m = float(self.custom_ent.get().strip())
            if 0.5 <= m <= 999:
                self._set_preset_secs(int(m * 60))
        except ValueError:
            pass

    def _set_preset_secs(self, secs):
        self.pomo_on = False
        self.pomo_btn.configure(fg_color="#1e1e1e")
        self.pomo_lbl.configure(text="")
        self.total_seconds = secs
        self.remaining = secs
        self._stop_event.set()
        self.running = False
        self.start_btn.configure(text="▶  Start")
        self._update_display()

    def _refresh_dots(self):
        for w in self.dot_frame.winfo_children():
            w.destroy()
        self.session_dots.clear()
        for _ in range(min(self.session_count, 8)):
            d = ctk.CTkLabel(self.dot_frame, text="●",
                font=ctk.CTkFont(size=12), text_color="#5b8dee")
            d.pack(side="left", padx=2)
            self.session_dots.append(d)
        if self.session_count > 0:
            ctk.CTkLabel(self.dot_frame, text=f"  {self.session_count} done",
                font=ctk.CTkFont(size=11), text_color="#444444").pack(side="left")

    # ══════════════════════════════════════════════════════════════════
    # POMODORO
    # ══════════════════════════════════════════════════════════════════

    def _toggle_pomodoro(self):
        self.pomo_on = not self.pomo_on
        if self.pomo_on:
            self.pomo_step = 0
            self.pomo_btn.configure(fg_color="#7a1515", hover_color="#8a2525")
            self._stop_event.set()
            self.running = False
            self.start_btn.configure(text="▶  Start")
            self._pomo_apply()
        else:
            self.pomo_btn.configure(fg_color="#1e1e1e", hover_color="#2e1818")
            self.pomo_lbl.configure(text="")

    def _pomo_apply(self):
        secs = POMO_SEQ[self.pomo_step % len(POMO_SEQ)]
        lbl  = POMO_LABELS[self.pomo_step % len(POMO_LABELS)]
        self.total_seconds = secs
        self.remaining     = secs
        self.pomo_lbl.configure(
            text=f"🍅 {lbl}  ({self.pomo_step+1}/{len(POMO_SEQ)})")
        self._update_display()

    def _pomo_advance(self):
        self.pomo_step = (self.pomo_step + 1) % len(POMO_SEQ)
        self._pomo_apply()
        lbl = POMO_LABELS[self.pomo_step % len(POMO_LABELS)]
        self._banner(f"Next: {lbl} — press Start")

    def _banner(self, msg):
        b = ctk.CTkLabel(self, text=msg,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#5b8dee", text_color="#fff",
            corner_radius=8, padx=14, pady=7)
        b.place(relx=0.5, rely=0.1, anchor="center")
        self.after(3000, b.destroy)

    # ══════════════════════════════════════════════════════════════════
    # SOUND
    # ══════════════════════════════════════════════════════════════════

    def _play_sound(self):
        def _go():
            try:
                s = platform.system()
                if s == "Windows":
                    import winsound
                    for f, d in [(880,170),(1100,170),(1320,280)]:
                        winsound.Beep(f, d); time.sleep(0.05)
                elif s == "Darwin":
                    os.system("afplay /System/Library/Sounds/Glass.aiff")
                else:
                    os.system("paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null")
            except Exception:
                self.after(0, self.bell)
        threading.Thread(target=_go, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════
    # TASKS
    # ══════════════════════════════════════════════════════════════════

    def _load_tasks(self):
        try:
            data = json.loads(TASKS_FILE.read_text())
            tasks = []
            for item in data:
                done = tk.BooleanVar(value=item.get("done", False))
                tasks.append({"text": item["text"], "done": done, "row": None})
            return tasks
        except Exception:
            return []

    def _save_tasks(self):
        try:
            data = [{"text": t["text"], "done": t["done"].get()} for t in self.tasks]
            TASKS_FILE.write_text(json.dumps(data))
        except Exception:
            pass

    def _toggle_tasks(self):
        self.tasks_visible = not self.tasks_visible
        if self.tasks_visible:
            self.task_panel.pack(side="right", fill="y", padx=(8,0))
            self._build_task_panel()
            self.tasks_btn.configure(fg_color="#5b8dee")
        else:
            for w in self.task_panel.winfo_children():
                w.destroy()
            self.task_panel.pack_forget()
            self.tasks_btn.configure(fg_color="#1e1e1e")

    def _build_task_panel(self):
        ctk.CTkLabel(self.task_panel, text="MY TASKS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#3a3a6a").pack(pady=(14,6))

        add_row = ctk.CTkFrame(self.task_panel, fg_color="transparent")
        add_row.pack(fill="x", padx=10, pady=(0,8))
        self.task_ent = ctk.CTkEntry(add_row, placeholder_text="Add task...",
            font=ctk.CTkFont(size=12), fg_color="#0d0d14",
            border_color="#1e1e3a", height=30)
        self.task_ent.pack(side="left", expand=True, fill="x", padx=(0,5))
        self.task_ent.bind("<Return>", lambda e: self._add_task())
        ctk.CTkButton(add_row, text="+", width=30, height=30,
            font=ctk.CTkFont(size=16), fg_color="#5b8dee",
            hover_color="#3a6ccc", corner_radius=8,
            command=self._add_task).pack(side="left")

        self.task_scroll = ctk.CTkScrollableFrame(self.task_panel,
            fg_color="transparent",
            scrollbar_button_color="#1e1e3a")
        self.task_scroll.pack(expand=True, fill="both", padx=6, pady=(0,6))

        # re-render existing tasks
        for t in self.tasks:
            self._render_task(t)

        ctk.CTkButton(self.task_panel, text="Clear done ✕",
            font=ctk.CTkFont(size=11), height=26,
            fg_color="#1e1e1e", hover_color="#2e1e1e",
            command=self._clear_done).pack(pady=(0,10))

    def _add_task(self):
        text = self.task_ent.get().strip()
        if not text:
            return
        self.task_ent.delete(0, "end")
        done = tk.BooleanVar(value=False)
        task = {"text": text, "done": done, "row": None}
        self.tasks.append(task)
        self._save_tasks()
        if self.tasks_visible:
            self._render_task(task)

    def _render_task(self, task):
        row = ctk.CTkFrame(self.task_scroll, fg_color="#0f0f1e",
            corner_radius=8)
        row.pack(fill="x", pady=2, padx=2)
        task["row"] = row

        cb = ctk.CTkCheckBox(row, text=task["text"],
            font=ctk.CTkFont(size=12), text_color="#bbbbbb",
            fg_color="#5b8dee", hover_color="#3a6ccc",
            border_color="#2a2a4a",
            variable=task["done"], wraplength=130,
            command=lambda t=task, r=row: self._task_toggle(t, r))
        cb.pack(side="left", padx=(8,4), pady=6, expand=True, anchor="w")

        ctk.CTkButton(row, text="×", width=22, height=22,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color="#2a1a1a",
            text_color="#444444",
            command=lambda t=task, r=row: self._del_task(t, r)
        ).pack(side="right", padx=4)

    def _task_toggle(self, task, row):
        if task["done"].get():
            row.configure(fg_color="#0a0a10")
            for c in row.winfo_children():
                if isinstance(c, ctk.CTkCheckBox):
                    c.configure(text_color="#333333")
        else:
            row.configure(fg_color="#0f0f1e")
            for c in row.winfo_children():
                if isinstance(c, ctk.CTkCheckBox):
                    c.configure(text_color="#bbbbbb")
        self._save_tasks()

    def _del_task(self, task, row):
        self.tasks = [t for t in self.tasks if t is not task]
        row.destroy()
        self._save_tasks()

    def _clear_done(self):
        remaining = []
        for t in self.tasks:
            if t["done"].get() and t["row"]:
                t["row"].destroy()
            else:
                remaining.append(t)
        self.tasks = remaining
        self._save_tasks()

    # ══════════════════════════════════════════════════════════════════
    # BACKGROUND
    # ══════════════════════════════════════════════════════════════════

    def _apply_preset(self, preset, init=False):
        self.cur_preset = preset
        self.light_bg   = preset["light"]
        self.use_img_bg = False
        if not init:
            self._update_text_colors()
        self.configure(fg_color=preset["c1"])
        self.canvas.configure(bg=preset["c1"])
        w = self.winfo_width()  or 1000
        h = self.winfo_height() or 690
        self._set_canvas_bg(self._make_gradient(w, h, preset["c1"], preset["c2"]))

    def _make_gradient(self, w, h, c1, c2):
        img = Image.new("RGB", (max(w,1), max(h,1)))
        draw = ImageDraw.Draw(img)
        r1,g1,b1 = self._h2rgb(c1)
        r2,g2,b2 = self._h2rgb(c2)
        for y in range(h):
            t = y / max(h-1, 1)
            draw.line([(0,y),(w,y)], fill=(
                int(r1+(r2-r1)*t), int(g1+(g2-g1)*t), int(b1+(b2-b1)*t)))
        return img

    def _h2rgb(self, h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2],16) for i in (0,2,4))

    def _update_text_colors(self):
        fg  = "#111111" if self.light_bg else "#ffffff"
        dim = "#555555" if self.light_bg else "#888888"
        self.timer_lbl.configure(text_color=fg)
        self.quote_lbl.configure(text_color=dim)
        self.title_lbl.configure(text_color="#333333" if self.light_bg else "#555555")

    def _redraw_bg(self):
        if self.use_img_bg and self.bg_src:
            self._draw_img_bg()
        else:
            self._apply_preset(self.cur_preset)

    def _draw_img_bg(self):
        w = self.winfo_width()  or 1000
        h = self.winfo_height() or 690
        img = self.bg_src.copy().resize((w,h), Image.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(4))
        ov  = Image.new("RGBA", img.size, (0,0,0,130))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        self.configure(fg_color="#000000")
        self.canvas.configure(bg="#000000")
        self._set_canvas_bg(img)

    def _set_canvas_bg(self, img):
        self.bg_photo = ImageTk.PhotoImage(img)
        self.canvas.delete("bg")
        self.canvas.create_image(0,0, anchor="nw", image=self.bg_photo, tags="bg")
        self.canvas.lower("bg")

    def _open_bg_panel(self):
        if self.bg_panel_win and self.bg_panel_win.winfo_exists():
            self.bg_panel_win.focus(); return

        win = ctk.CTkToplevel(self)
        self.bg_panel_win = win
        win.title("Background")
        win.geometry("560x420")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="Dark Gradients",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#555555").pack(pady=(14,4))

        dark_grid = ctk.CTkFrame(win, fg_color="transparent"); dark_grid.pack(padx=16)
        dark = [p for p in BG_PRESETS if not p["light"]]
        for i, p in enumerate(dark):
            r, c = divmod(i, 6)
            ctk.CTkButton(dark_grid, text=p["name"],
                font=ctk.CTkFont(size=10), width=80, height=44,
                fg_color=p["c2"], hover_color=p["c1"], corner_radius=7,
                command=lambda p=p: [self._apply_preset(p), win.destroy()]
            ).grid(row=r, column=c, padx=3, pady=3)

        ctk.CTkLabel(win, text="Black · Grey · White",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#555555").pack(pady=(10,4))

        light_grid = ctk.CTkFrame(win, fg_color="transparent"); light_grid.pack(padx=16)
        lights = [p for p in BG_PRESETS if p["light"]]
        for i, p in enumerate(lights):
            r, c = divmod(i, 4)
            ctk.CTkButton(light_grid, text=p["name"],
                font=ctk.CTkFont(size=10), width=100, height=44,
                fg_color=p["c2"], hover_color=p["c1"], corner_radius=7,
                text_color="#222222",
                command=lambda p=p: [self._apply_preset(p), win.destroy()]
            ).grid(row=r, column=c, padx=3, pady=3)

        ctk.CTkSeparator(win).pack(fill="x", padx=16, pady=10)
        row = ctk.CTkFrame(win, fg_color="transparent"); row.pack()
        ctk.CTkButton(row, text="📁 Load Image", width=130, height=32,
            command=self._load_img_bg).pack(side="left", padx=6)
        ctk.CTkButton(row, text="🎨 Custom Color", width=130, height=32,
            command=self._pick_color).pack(side="left", padx=6)
        ctk.CTkButton(row, text="↺ Reset", width=80, height=32,
            fg_color="#2a2a2a", hover_color="#3a3a3a",
            command=lambda: [self._apply_preset(BG_PRESETS[0]), win.destroy()]
        ).pack(side="left", padx=6)

    def _load_img_bg(self):
        path = filedialog.askopenfilename(
            filetypes=[("Images","*.png *.jpg *.jpeg *.bmp *.webp")])
        if path:
            self.bg_src     = Image.open(path)
            self.use_img_bg = True
            self.light_bg   = False
            self._draw_img_bg()

    def _pick_color(self):
        c = colorchooser.askcolor(color="#141e30")[1]
        if c:
            self._apply_preset({"name":"Custom","c1":c,"c2":c,"light":False})

    # ══════════════════════════════════════════════════════════════════
    # FOCUS MODE
    # ══════════════════════════════════════════════════════════════════

    def _toggle_focus(self):
        if self.focus_mode:
            self._show_math_exit()
        else:
            self._enter_focus()

    def _enter_focus(self):
        self.focus_mode = True
        self.attributes("-fullscreen", True)
        self._show_page("timer")
        self.nav_games.pack_forget()
        self.nav_plan.pack_forget()
        self.nav_timer.configure(state="disabled")
        self.focus_btn.configure(text="⬜ Exit Focus", fg_color="#5b8dee", hover_color="#3a6ccc")
        self.bg_btn.configure(state="disabled")
        self.tasks_btn.configure(state="disabled")
        self.title_lbl.configure(text="")
        self._redraw_bg()

    def _exit_focus(self):
        self.focus_mode = False
        self.attributes("-fullscreen", False)
        self.geometry("1000x690")
        self.nav_games.pack(side="left", padx=4)
        self.nav_plan.pack(side="left", padx=4)
        self.nav_timer.configure(state="normal")
        self.focus_btn.configure(text="⬛ Focus", fg_color="#1e1e1e", hover_color="#2e2e2e")
        self.bg_btn.configure(state="normal")
        self.tasks_btn.configure(state="normal")
        self.title_lbl.configure(text="FOCUS TIMER")
        self._redraw_bg()

    def _show_math_exit(self):
        import random as _r
        a = _r.randint(2, 9)
        b = _r.randint(2, 9)
        answer = a * b

        win = ctk.CTkToplevel(self)
        win.title("Exit Focus")
        win.geometry("320x210")
        win.resizable(False, False)
        win.grab_set()
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="Solve to exit Focus Mode",
            font=ctk.CTkFont(size=13), text_color="#888888").pack(pady=(20, 8))

        ctk.CTkLabel(win, text=f"{a}  ×  {b}  =  ?",
            font=ctk.CTkFont("Segoe UI", 36, "bold"), text_color="#ffffff").pack(pady=(0, 12))

        entry = ctk.CTkEntry(win, width=100, height=38, font=ctk.CTkFont(size=20),
            justify="center", placeholder_text="?")
        entry.pack()
        entry.focus()

        feedback = ctk.CTkLabel(win, text="", font=ctk.CTkFont(size=12), text_color="#ff6b6b")
        feedback.pack(pady=(6, 0))

        def _check(event=None):
            try:
                if int(entry.get().strip()) == answer:
                    win.destroy()
                    self._exit_focus()
                else:
                    feedback.configure(text="Wrong! Try again.")
                    entry.delete(0, "end")
            except ValueError:
                feedback.configure(text="Enter a number.")

        entry.bind("<Return>", _check)
        ctk.CTkButton(win, text="Confirm", width=100, height=34,
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=17,
            command=_check).pack(pady=(8, 0))

    # ══════════════════════════════════════════════════════════════════
    # QUOTES
    # ══════════════════════════════════════════════════════════════════

    def _start_quote_cycle(self):
        self._fade_in_quote()

    def _fade_in_quote(self, a=0):
        if a > 100:
            self._quote_job = self.after(8000, self._fade_out_quote)
            return
        if self.light_bg:
            v = int(0x50 * a / 100)
            self.quote_lbl.configure(text_color=f"#{v:02x}{v:02x}{v:02x}")
        else:
            v = int(0xaa * a / 100)
            self.quote_lbl.configure(text_color=f"#{v:02x}{v:02x}{v:02x}")
        self.after(18, lambda: self._fade_in_quote(a+5))

    def _fade_out_quote(self, a=100):
        if a < 0:
            self.quote_index = (self.quote_index+1) % len(QUOTES)
            self.quote_lbl.configure(text=QUOTES[self.quote_index])
            self._fade_in_quote()
            return
        if self.light_bg:
            v = int(0x50 * a / 100)
            self.quote_lbl.configure(text_color=f"#{v:02x}{v:02x}{v:02x}")
        else:
            v = int(0xaa * a / 100)
            self.quote_lbl.configure(text_color=f"#{v:02x}{v:02x}{v:02x}")
        self.after(18, lambda: self._fade_out_quote(a-5))

    # ══════════════════════════════════════════════════════════════════
    # KEY HANDLING
    # ══════════════════════════════════════════════════════════════════

    def _on_key(self, e):
        key = e.keysym

        # space: toggle timer on timer page, or trigger reaction click on games page
        if key == "space":
            if self.current_page == "timer":
                self._toggle_timer()
                return
            elif self.current_page == "games" and self.active_game == "react":
                self._react_click()
                return

        if not self.snake_running or self.current_page != "games" \
                or self.active_game != "snake":
            return
        dirs = {"Up":(-1,0),"Down":(1,0),"Left":(0,-1),"Right":(0,1),
                "w":(-1,0),"s":(1,0),"a":(0,-1),"d":(0,1)}
        if key in dirs:
            nd = dirs[key]
            # prevent 180 reverse
            if nd[0] + self.snake_dir[0] != 0 or nd[1] + self.snake_dir[1] != 0:
                self.snake_next_dir = nd

    # ══════════════════════════════════════════════════════════════════
    # WEEKLY PLANNER
    # ══════════════════════════════════════════════════════════════════

    def _build_plan_page(self, p):
        # header row
        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(hdr, text="WEEKLY PLANNER",
            font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color="#555555").pack(side="left")
        ctk.CTkButton(hdr, text="+ Add Task", width=90, height=28,
            font=ctk.CTkFont(size=12), fg_color="#5b8dee", hover_color="#3a6ccc",
            corner_radius=14, command=self._open_add_plan_task).pack(side="right")

        # 7 columns
        cols_frame = ctk.CTkFrame(p, fg_color="transparent")
        cols_frame.pack(expand=True, fill="both", padx=6, pady=(0, 8))

        self.plan_col_lists = {}  # day_idx -> CTkScrollableFrame
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        today = datetime.date.today().weekday()  # 0=Mon

        for i, day in enumerate(days):
            date = self._week_date(i)
            is_today = (i == today)
            border = "#5b8dee" if is_today else "#1e1e3a"
            col = ctk.CTkFrame(cols_frame, fg_color="#0d0d1a",
                corner_radius=10, border_width=1, border_color=border)
            col.pack(side="left", expand=True, fill="both", padx=3)

            # day header
            day_color = "#5b8dee" if is_today else "#3a3a6a"
            ctk.CTkLabel(col, text=day,
                font=ctk.CTkFont("Segoe UI", 12, "bold"), text_color=day_color
            ).pack(pady=(8, 0))
            ctk.CTkLabel(col, text=date.strftime("%d %b"),
                font=ctk.CTkFont(size=10), text_color="#444444").pack()

            # task list
            task_list = ctk.CTkScrollableFrame(col, fg_color="transparent",
                scrollbar_button_color="#1e1e3a")
            task_list.pack(expand=True, fill="both", padx=4, pady=4)
            self.plan_col_lists[i] = task_list

        # populate
        for task in self.plan_tasks:
            self._render_plan_task(task)

        # start notification checker
        self._check_plan_notifications()

    def _week_date(self, day_idx):
        """Return the date for day_idx (0=Mon) of the current ISO week."""
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        return week_start + datetime.timedelta(days=day_idx)

    def _current_week_str(self):
        return datetime.date.today().strftime("%G-W%V")

    def _load_plan_tasks(self):
        try:
            data = json.loads(PLAN_FILE.read_text())
            current_week = self._current_week_str()
            # discard old week's tasks
            tasks = [t for t in data if t.get("week") == current_week]
            return tasks
        except Exception:
            return []

    def _save_plan_tasks(self):
        try:
            PLAN_FILE.write_text(json.dumps(self.plan_tasks))
        except Exception:
            pass

    def _refresh_plan_page(self):
        """Re-render all task cards in their columns."""
        for col_list in self.plan_col_lists.values():
            for w in col_list.winfo_children():
                w.destroy()
        for task in self.plan_tasks:
            self._render_plan_task(task)

    def _open_add_plan_task(self, prefill_day=None):
        win = ctk.CTkToplevel(self)
        win.title("Add Task")
        win.geometry("340x280")
        win.resizable(False, False)
        win.grab_set()
        win.attributes("-topmost", True)

        ctk.CTkLabel(win, text="New Planned Task",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#ffffff").pack(pady=(18, 12))

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(padx=24, fill="x")

        # task name
        ctk.CTkLabel(form, text="Task", font=ctk.CTkFont(size=12), text_color="#888888",
            anchor="w").grid(row=0, column=0, sticky="w", pady=4)
        name_ent = ctk.CTkEntry(form, width=200, height=30, placeholder_text="e.g. Math homework")
        name_ent.grid(row=0, column=1, pady=4, padx=(8, 0))

        # day
        days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        today_idx = datetime.date.today().weekday()
        ctk.CTkLabel(form, text="Day", font=ctk.CTkFont(size=12), text_color="#888888",
            anchor="w").grid(row=1, column=0, sticky="w", pady=4)
        day_var = ctk.StringVar(value=days[prefill_day if prefill_day is not None else today_idx])
        day_menu = ctk.CTkOptionMenu(form, values=days, variable=day_var, width=200, height=30)
        day_menu.grid(row=1, column=1, pady=4, padx=(8, 0))

        # start time
        ctk.CTkLabel(form, text="Start", font=ctk.CTkFont(size=12), text_color="#888888",
            anchor="w").grid(row=2, column=0, sticky="w", pady=4)
        time_ent = ctk.CTkEntry(form, width=200, height=30, placeholder_text="14:00")
        time_ent.grid(row=2, column=1, pady=4, padx=(8, 0))

        # duration
        ctk.CTkLabel(form, text="Duration (min)", font=ctk.CTkFont(size=12), text_color="#888888",
            anchor="w").grid(row=3, column=0, sticky="w", pady=4)
        dur_ent = ctk.CTkEntry(form, width=200, height=30, placeholder_text="60")
        dur_ent.grid(row=3, column=1, pady=4, padx=(8, 0))

        err_lbl = ctk.CTkLabel(win, text="", font=ctk.CTkFont(size=11), text_color="#ff6b6b")
        err_lbl.pack(pady=(4, 0))

        def _confirm():
            name = name_ent.get().strip()
            if not name:
                err_lbl.configure(text="Task name required."); return
            # parse time
            raw_time = time_ent.get().strip() or "08:00"
            try:
                h, m = map(int, raw_time.split(":"))
                if not (0 <= h <= 23 and 0 <= m <= 59):
                    raise ValueError
                start_time = f"{h:02d}:{m:02d}"
            except Exception:
                err_lbl.configure(text="Time must be HH:MM (e.g. 14:00)"); return
            # parse duration
            raw_dur = dur_ent.get().strip() or "60"
            try:
                dur = int(raw_dur)
                if dur <= 0: raise ValueError
            except Exception:
                err_lbl.configure(text="Duration must be a positive number."); return

            day_idx = days.index(day_var.get())
            task = {
                "text": name,
                "day": day_idx,
                "start_time": start_time,
                "duration_min": dur,
                "done": False,
                "notified": False,
                "week": self._current_week_str(),
            }
            self.plan_tasks.append(task)
            self._save_plan_tasks()
            if self.current_page == "plan":
                self._render_plan_task(task)
            win.destroy()

        ctk.CTkButton(win, text="Add Task", width=120, height=34,
            fg_color="#5b8dee", hover_color="#3a6ccc", corner_radius=17,
            command=_confirm).pack(pady=(8, 0))
        name_ent.bind("<Return>", lambda e: _confirm())

    def _render_plan_task(self, task):
        if task["day"] not in self.plan_col_lists:
            return
        col = self.plan_col_lists[task["day"]]

        # compute end time
        try:
            h, m = map(int, task["start_time"].split(":"))
            end_min = h * 60 + m + task["duration_min"]
            end_str = f"{end_min // 60 % 24:02d}:{end_min % 60:02d}"
            time_str = f"{task['start_time']}–{end_str}"
        except Exception:
            time_str = task["start_time"]

        card = ctk.CTkFrame(col, fg_color="#0f0f1e" if not task["done"] else "#0a0a10",
            corner_radius=8, border_width=1,
            border_color="#1e1e3a" if not task["done"] else "#0d0d1a")
        card.pack(fill="x", pady=2, padx=1)
        task["card"] = card

        # time label
        ctk.CTkLabel(card, text=time_str,
            font=ctk.CTkFont(size=9), text_color="#5b8dee" if not task["done"] else "#333333"
        ).pack(anchor="w", padx=6, pady=(4, 0))

        # task name
        name_color = "#aaaaaa" if not task["done"] else "#333333"
        ctk.CTkLabel(card, text=task["text"],
            font=ctk.CTkFont(size=11, weight="bold"), text_color=name_color,
            wraplength=100, anchor="w", justify="left"
        ).pack(anchor="w", padx=6)

        # duration label
        ctk.CTkLabel(card, text=f"{task['duration_min']} min",
            font=ctk.CTkFont(size=9), text_color="#444444"
        ).pack(anchor="w", padx=6, pady=(0, 2))

        # bottom row: checkbox + delete
        bot = ctk.CTkFrame(card, fg_color="transparent")
        bot.pack(fill="x", padx=4, pady=(0, 4))

        done_var = tk.BooleanVar(value=task["done"])
        task["done_var"] = done_var

        def _toggle(t=task, c=card, v=done_var):
            t["done"] = v.get()
            self._save_plan_tasks()
            # refresh card style
            c.configure(fg_color="#0a0a10" if t["done"] else "#0f0f1e",
                        border_color="#0d0d1a" if t["done"] else "#1e1e3a")

        ctk.CTkCheckBox(bot, text="Done", variable=done_var,
            font=ctk.CTkFont(size=10), text_color="#555555",
            fg_color="#5b8dee", hover_color="#3a6ccc",
            border_color="#2a2a4a", width=14, height=14,
            command=_toggle).pack(side="left")

        ctk.CTkButton(bot, text="×", width=20, height=20,
            font=ctk.CTkFont(size=12), fg_color="transparent",
            hover_color="#2a1a1a", text_color="#444444",
            command=lambda t=task, c=card: self._del_plan_task(t, c)
        ).pack(side="right")

    def _del_plan_task(self, task, card):
        self.plan_tasks = [t for t in self.plan_tasks if t is not task]
        self._save_plan_tasks()
        card.destroy()

    def _check_plan_notifications(self):
        now = datetime.datetime.now()
        today_idx = now.weekday()
        now_str = now.strftime("%H:%M")
        for task in self.plan_tasks:
            if task["day"] == today_idx and not task["notified"] and not task["done"]:
                if task["start_time"] == now_str:
                    task["notified"] = True
                    self._save_plan_tasks()
                    self._banner(f"⏰ Task starting: {task['text']}")
        self.after(30000, self._check_plan_notifications)

    def on_close(self):
        self._stop_event.set()
        self.snake_running = False
        if self._snake_job:
            self.after_cancel(self._snake_job)
        if self._react_job:
            self.after_cancel(self._react_job)
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
