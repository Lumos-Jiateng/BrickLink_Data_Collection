"""
workflow_utils.py — reusable building blocks for Mac CUA workflows.

All coordinate arguments use the normalized 1000×1000 space that Qwen outputs.
Hard-coded click steps rescale to real screen pixels at runtime via pyautogui.size().
"""


# ── Screenshot ────────────────────────────────────────────────────────────────

def screenshot_step(prefix="screenshot", output_dir="."):
    """Direct-action step: capture a full-screen screenshot.

    The saved filename is  <prefix>_<YYYYMMDD_HHMMSS>.png.

    Args:
        prefix:     Filename prefix.  Defaults to "screenshot".
        output_dir: Directory to write the file into.

    Returns:
        A workflow step dict (direct_actions).
    """
    return {
        "name": f"Screenshot [{prefix}]",
        "direct_actions": [
            f"import pyautogui, os; "
            f"os.makedirs(r'{output_dir}', exist_ok=True); "
            f"path = os.path.join(r'{output_dir}', '{prefix}.png'); "
            f"pyautogui.screenshot().save(path); "
            f"print('Saved:', path)"
        ],
    }


# ── Single click ──────────────────────────────────────────────────────────────

def click_step(x_norm, y_norm, name=None):
    """Direct-action step: click at a normalized (0–1000, 0–1000) coordinate.

    The coordinate is rescaled to actual screen pixels at runtime:
        screen_px = round(norm / 1000 * screen_size)

    Args:
        x_norm: X in 1000×1000 space  (0 = left edge, 1000 = right edge).
        y_norm: Y in 1000×1000 space  (0 = top  edge, 1000 = bottom edge).
        name:   Optional step-name override.

    Returns:
        A workflow step dict (direct_actions).
    """
    return {
        "name": name or f"Click ({x_norm}, {y_norm})",
        "direct_actions": [
            f"import pyautogui; "
            f"sw, sh = pyautogui.size(); "
            f"px = round({x_norm} / 1000 * sw); "
            f"py = round({y_norm} / 1000 * sh); "
            f"pyautogui.click(px, py); "
            f"print(f'Clicked norm=({x_norm},{y_norm})"
            f" -> screen=({{px}},{{py}}) on {{sw}}x{{sh}}')"
        ],
    }


# ── Sleep ─────────────────────────────────────────────────────────────────────

def sleep_step(seconds):
    """Direct-action step: pause execution for a fixed number of seconds.

    Args:
        seconds: How long to sleep.

    Returns:
        A workflow step dict (direct_actions).
    """
    return {
        "name": f"Sleep {seconds}s",
        "direct_actions": [
            f"import time; time.sleep({seconds}); print('Slept {seconds}s')"
        ],
    }


# ── App window helpers ────────────────────────────────────────────────────────

def minimize_app_step():
    """Direct-action step: focus the current app via center click, then minimize it.

    Uses normalized center (500, 500) to click, then Command+M.

    Returns:
        A workflow step dict (direct_actions).
    """
    return {
        "name": "Minimize current app",
        "direct_actions": [
            "import pyautogui; "
            "sw, sh = pyautogui.size(); "
            "pyautogui.click(round(500 / 1000 * sw), round(500 / 1000 * sh)); "
            "pyautogui.hotkey('command', 'm'); "
            "print('Minimized current app')"
        ],
    }


def fullscreen_app_step():
    """Direct-action step: focus the current app via center click, then fullscreen it.

    Uses normalized center (500, 500) to click, then Ctrl+Command+F.

    Returns:
        A workflow step dict (direct_actions).
    """
    return {
        "name": "Fullscreen current app",
        "direct_actions": [
            "import pyautogui; "
            "sw, sh = pyautogui.size(); "
            "pyautogui.click(round(500 / 1000 * sw), round(500 / 1000 * sh)); "
            "pyautogui.hotkey('ctrl', 'command', 'f'); "
            "print('Fullscreened current app')"
        ],
    }


# ── Compound helpers ──────────────────────────────────────────────────────────

def click_pair_round(round_idx, x1, y1, x2, y2, output_dir,
                     screenshot_prefix="round"):
    """Three-step sequence for one annotated round: Click A → Click B → Screenshot.

    Args:
        round_idx:         Round number (used in step names and the filename).
        x1, y1:            First  click — normalized 1000×1000 coords.
        x2, y2:            Second click — normalized 1000×1000 coords.
        output_dir:        Directory to save the screenshot.
        screenshot_prefix: Prefix for the screenshot filename
                           (result: <prefix><round_idx:02d>_<ts>.png).

    Returns:
        List of three workflow step dicts.
    """
    return [
        click_step(x1, y1, name=f"Round {round_idx} — Click A ({x1}, {y1})"),
        click_step(x2, y2, name=f"Round {round_idx} — Click B ({x2}, {y2})"),
        screenshot_step(
            prefix=f"{screenshot_prefix}{round_idx:02d}",
            output_dir=output_dir,
        ),
    ]
