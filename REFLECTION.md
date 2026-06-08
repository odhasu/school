# Focus Timer — End Reflection

## What is Focus Timer?

Focus Timer is a desktop productivity application built in Python using the **CustomTkinter** UI library. It is packaged as a standalone `.app` (macOS) / `.exe` (Windows) using PyInstaller, so no Python installation is required to run it.

The app combines a **focus timer** with **mini-games**, motivational **quotes**, a **task manager**, and a customisable **background system** — all in one window.

---

## How the App Works

### Application Architecture

The entire application is a single Python class `App` that extends `ctk.CTk` (the main window). On launch, `__init__` sets up all state variables, builds the UI, applies the default background, and starts the quote cycle. The window uses a `tk.Canvas` as a full-window background layer, with all UI widgets placed on top using a transparent `CTkFrame` overlay.

```
App (ctk.CTk)
├── Canvas          ← full-window background (gradient or image)
├── Transparent wrap frame
│   ├── Top bar     ← navigation, BG button, Tasks button, Focus button
│   └── Body
│       ├── Content area (swappable pages)
│       │   ├── Timer Page
│       │   └── Games Page
│       │       ├── Snake
│       │       ├── Reaction Test
│       │       └── Memory Game
│       └── Task Panel (side panel, shown/hidden)
```

---

### Timer Page

The timer page is the core feature of the app. It displays a large countdown (`92pt` bold font), a thin progress bar underneath, motivational quotes that fade in and out, and session dot indicators.

**How the timer works:**  
When the user presses Start, a **background daemon thread** (`_tick`) is launched. This thread uses `time.monotonic()` — a high-precision, non-adjustable clock — to count down seconds without being affected by system clock changes. It checks every 50ms whether a second has passed, then decrements `self.remaining` and schedules a UI update on the main thread using `self.after(0, self._update_display)`. This is important because Tkinter is not thread-safe — all UI updates must happen on the main thread. A `threading.Event` (`_stop_event`) is used to signal the thread to stop when the user pauses or resets.

**Progress bar:**  
The bar fills left to right and changes colour based on remaining time:
- Blue (`#5b8dee`) — normal
- Yellow (`#ffcc00`) — under 5 minutes
- Red (`#ff6b6b`) — under 1 minute

**Time presets:**  
Buttons for 5m, 10m, 25m, 45m, 60m instantly reset the timer to that duration. A custom input field accepts any value from 0.5 to 999 minutes.

**Session dots:**  
Each completed session adds a blue dot `●` to the dot row. Up to 8 dots are shown visually. The total count is always displayed as text next to the dots (e.g. `12 done`).

**Completion:**  
When the timer hits zero, the label flashes blue/white 6 times, a sound plays (platform-specific), and the session counter increments. In Pomodoro mode, the next phase loads automatically after 2 seconds.

---

### Pomodoro Mode

Activating the 🍅 Pomodoro button loads a pre-defined 8-phase sequence:

| Step | Duration | Label |
|------|----------|-------|
| 1 | 25 min | Focus |
| 2 | 5 min | Short Break |
| 3 | 25 min | Focus |
| 4 | 5 min | Short Break |
| 5 | 25 min | Focus |
| 6 | 5 min | Short Break |
| 7 | 25 min | Focus |
| 8 | 15 min | Long Break! |

After each phase completes, a floating banner notification appears and the app loads the next phase. The Pomodoro button turns dark red to indicate it is active.

---

### Background System

The background is a full-window `tk.Canvas` image, rendered using **Pillow (PIL)**. It supports three modes:

1. **Gradient presets** — 14 built-in gradients split into "Dark" and "Light" categories. Each preset is defined by two hex colours (`c1`, `c2`) and a `light` flag. The gradient is rendered pixel-row by pixel-row by linearly interpolating between the two RGB values.

2. **Custom image** — the user can load any PNG/JPG/BMP/WEBP from disk. The image is scaled with `LANCZOS` (high-quality) resampling, then a Gaussian blur (`radius=4`) and a semi-transparent black overlay (`RGBA (0,0,0,130)`) are applied to keep the UI legible.

3. **Custom solid colour** — the system colour picker selects a colour, which is then used as both gradient stops (no gradient, flat colour).

On window resize, `_redraw_bg` is called automatically via a `<Configure>` event binding on the canvas, regenerating the background at the new size.

The `light` flag on each preset adjusts text colours across the UI (timer label, quote, title bar text) so they remain readable on both dark and light backgrounds.

---

### Focus Mode

Pressing the `⬛ Focus` button enters fullscreen mode. In this mode:
- The window goes fullscreen
- Navigation and sidebar buttons are disabled
- Only the timer and Start/Reset/Pomodoro controls are accessible
- The title bar text is hidden
- Pressing the button again exits fullscreen and restores all controls

---

### Quote System

Ten motivational quotes cycle continuously on the timer page. Each quote fades in over ~360ms, stays visible for 8 seconds, then fades out before the next one appears. The fade is implemented as a recursive `self.after()` call that increments an alpha value `a` from 0 to 100 in steps of 5, computing a greyscale hex colour for each step.

On **dark backgrounds**, the max brightness is `0xAA` per channel (medium grey, readable but not harsh).  
On **light backgrounds**, the max brightness is `0x50` per channel (dark grey, visible on white).

---

### Task Manager

The task panel slides in from the right side of the window. Tasks are stored as a list of Python dicts, each containing the text, a `tk.BooleanVar` for the done state, and a reference to the UI row widget.

**Persistence:** Tasks are saved to `~/.focus_timer_tasks.json` automatically whenever the task list changes (add, delete, check/uncheck, clear done). On startup, this file is loaded and tasks are restored.

Task operations:
- **Add** — type in the entry box and press Enter or `+`
- **Check** — dims the task row to indicate completion
- **Delete** — `×` button removes the task immediately
- **Clear done** — removes all completed tasks at once

---

### Games Page

Three mini-games are available under the 🎮 Games tab.

#### Snake

A classic Snake game on an 18×24 grid (cell size 18px). The snake starts at the centre moving right, and food appears as a red circle at a random empty cell.

- **Controls:** Arrow keys or WASD
- **Speed:** Starts at 220ms per step, decreases by 7ms per point eaten, minimum 75ms (very fast at high scores)
- **Rendering:** Each snake segment is drawn as a circle (`create_oval`) — blue for the head, darker blue for the body. Food is a red circle. Grid dots are drawn at cell centres as tiny dark rectangles.
- **Collision:** Game over when the head hits a wall or any body segment
- **High score** is tracked for the current session

#### Reaction Test

Tests how fast the user can react to a visual stimulus. The flow:

1. Click "Ready?" — button goes grey ("Wait...")
2. A random delay between 1.5s and 4.5s passes
3. Button turns green ("NOW!") — click as fast as possible
4. Result is shown in milliseconds with a grade:
   - Under 200ms → "Insane! 🔥"
   - Under 280ms → "Excellent!"
   - Under 380ms → "Good!"
   - 380ms+ → "Keep practising"
5. Clicking before the green = "Too early!" penalty

Best and average times are tracked and displayed. Space bar also triggers the click.

#### Memory Game

A 4×4 card-matching game with 8 emoji pairs. Cards start face-down (`?`). The player flips two cards at a time — if they match, they stay revealed (green); if not, they flip back after 800ms.

- **Moves counter** tracks how many pairs the player has attempted
- **Live timer** starts on the first card flip and stops when all pairs are matched
- **Win condition** is all 16 cards matched; the final time is displayed
- "New Game" reshuffles and resets everything

---

### Sound

When a timer session completes, a sound plays via a background thread:
- **macOS:** `afplay /System/Library/Sounds/Glass.aiff`
- **Windows:** Three ascending `winsound.Beep` tones (880Hz → 1100Hz → 1320Hz)
- **Linux:** `paplay` with a freedesktop sound file
- **Fallback:** Tkinter's built-in `bell()` if the above all fail

---

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Start/Pause timer (on Timer page) |
| Space | Trigger reaction click (on Reaction game) |
| Arrow keys / WASD | Control snake direction |

---

## Development Steps & Improvements

### Step 1 — Initial Build

The first version of the app was built from scratch. It included:
- A countdown timer with preset and custom durations
- Pomodoro mode with the 4×25/5/15 sequence
- Animated session dots
- A full background gradient/image system with 14 presets
- A task side panel with add/delete/check
- Motivational quote rotation with fade animation
- Focus/fullscreen mode

The app was packaged using **PyInstaller** via `build.sh` and `FocusTimer.spec`, producing a standalone `.app` for macOS and a `.exe` for Windows.

---

### Step 2 — Games Page

A second page was added for mini-games. Three games were implemented:

- **Snake** — full grid-based snake with score tracking and increasing speed
- **Reaction Test** — random-delay stimulus with ms timing and grade feedback
- **Memory Game** — 4×4 card flip with move counter

Navigation was added to the top bar to switch between Timer and Games pages.

Background presets were also expanded at this stage (dark gradients + grey/white range).

---

### Step 3 — Bug Fixes & Polish

Several issues and improvements were identified and fixed:

#### Bug: Quote fade invisible on light backgrounds
The fade animation computed a greyscale hex colour with a max of `0xAA` per channel. On light (white/grey) backgrounds, `#aaaaaa` is nearly invisible. Fixed by checking `self.light_bg` in `_fade_in_quote` and `_fade_out_quote`, using `0x50` max on light backgrounds so quotes appear as dark grey.

#### Bug: Progress bar could exceed 1.0
In Pomodoro mode, `total_seconds` is updated when a new phase loads. If `remaining` somehow exceeded `total_seconds` (e.g. after a rapid reset), the ratio passed to `progress.set()` could be > 1.0, causing an internal widget error. Fixed by clamping with `min(1.0, ratio)`.

#### Feature: Task Persistence
Tasks were previously lost every time the app closed. Fixed by adding `_save_tasks()` and `_load_tasks()` methods using the `json` module and Python's `pathlib.Path`. Tasks are saved to `~/.focus_timer_tasks.json` automatically on every change (add, delete, toggle, clear). On startup, the file is read and tasks are reconstructed with their done state.

#### Feature: Keyboard Shortcut — Space Bar
The `_on_key` handler was extended to handle `key == "space"`:
- On the Timer page: toggles start/pause
- On the Games page with Reaction game active: triggers the click  

This makes the reaction test much faster to use and the timer more accessible.

#### Feature: Memory Game Timer
A live elapsed timer was added to the Memory game. `mem_start_time` is recorded on the first card flip. A repeating `self.after(1000, ...)` loop updates the `mem_time_lbl` label every second. When all pairs are matched, the timer job is cancelled and the final elapsed time is frozen on screen.

#### Improvement: Snake Rounded Segments
Snake body segments were previously drawn as squares using `create_rectangle`. Changed to `create_oval` with the same bounding box coordinates for a cleaner, circular look that feels more polished.

#### Improvement: Session Count Label
`_refresh_dots` previously showed up to 8 dot icons with no indication of the actual count beyond 8. A `"N done"` text label was added after the dots, visible whenever at least one session has been completed.

---

## Technologies Used

| Library | Purpose |
|---------|---------|
| `customtkinter` | Modern themed UI widgets |
| `tkinter` | Base canvas and core widgets |
| `Pillow (PIL)` | Image rendering: gradients, blur, overlay |
| `threading` | Background timer tick without freezing UI |
| `time.monotonic()` | Precise, drift-free timing |
| `json` / `pathlib` | Task persistence to disk |
| `random` | Snake food placement, quote selection, reaction delay |
| `platform` / `os` | Cross-platform sound playback |
| `PyInstaller` | Packaging to standalone `.app` / `.exe` |

---

## What I Learned

- **Threading in GUI apps** requires strict separation: background threads do computation, main thread does all UI updates. Using `self.after(0, callback)` is the correct Tkinter pattern for this.
- **`time.monotonic()`** is the right clock for measuring elapsed time — unlike `time.time()`, it never jumps backwards or adjusts for time zone changes.
- **Pillow** is very powerful for programmatic image generation. Building gradient backgrounds pixel-by-pixel gave full control over the visual style.
- **State machines** (idle/waiting/ready) are the cleanest way to manage multi-step interactive flows like the reaction test.
- **PyInstaller** packaging requires specifying hidden imports and data files explicitly in the `.spec` file; bundling assets (sounds, icons) needs careful path handling.
- Small UX details — a keyboard shortcut, a live timer, rounded corners on a canvas — make a real difference to how polished the app feels.
