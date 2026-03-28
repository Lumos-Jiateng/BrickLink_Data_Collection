"""Workflow: minimize Cursor, fullscreen the next app, then capture all views."""

from workflows.workflow_utils import (
    click_step,
    fullscreen_app_step,
    minimize_app_step,
    screenshot_step,
    sleep_step,
)

OUTPUT_DIR = "/Users/jiateng5/research/Mac_Cua_Framework/interactive_position_workflow"

def capture_views(output_dir):
    """Steps that capture all 7 named views into output_dir.

    Sequence per round:
        click anchor  →  click target  →  save <view_name>.png

    Args:
        output_dir: Directory to write all screenshots into.

    Returns:
        Flat list of workflow step dicts.
    """
    anchor = (232, 161)

    # Second-click targets — from annotation_20260316_152647.json
    second_clicks = [
        (264, 161),
        (279, 159),
        (310, 161),
        (325, 161),
        (341, 160),
        (295, 158),
    ]

    # index 0 → baseline, index 1–6 → one per round
    view_names = [
        "free_view_left",
        "front_view",
        "back_view",
        "right_view",
        "bottom_view",
        "top_view",
        "left_view",
    ]

    steps = []

    # Baseline screenshot (no click — just the current screen state)
    steps.append(screenshot_step(prefix=view_names[0], output_dir=output_dir))

    # One round per (second_click, view_name) pair
    for i, ((x2, y2), view_name) in enumerate(
        zip(second_clicks, view_names[1:]), start=1
    ):
        steps.append(click_step(*anchor, name=f"Round {i} — Click anchor {anchor}"))
        steps.append(click_step(x2, y2,  name=f"Round {i} — Click target ({x2}, {y2})"))
        steps.append(screenshot_step(prefix=view_name, output_dir=output_dir))

    # Return to anchor
    steps.append(click_step(*anchor, name="Final — Return to anchor"))

    return steps


WORKFLOW = [
    # ── Prepare desktop ────────────────────────────────────────────────────────
    minimize_app_step(),
    fullscreen_app_step(),

    # ── Open target file ───────────────────────────────────────────────────────
    sleep_step(1),
    {
        "name": "Open File dialog",
        "instruction": (
            "Click on the 'Open File' menu item or button to open the file picker dialog."
        ),
        "max_steps": 1,
        "sleep": 2,
    },
    sleep_step(1),
    {
        "name": "Select file starting with 3028",
        "instruction": (
            "You are in a file picker dialog. "
            "The target file is located inside a folder called 'model_files' which is already opened — "
            "The files in the folder are listed in ascending numeric order by their name. "
            "First, move the mouse cursor into the file list area (the right most column)so that scrolling "
            "affects the file list and not any other panel. "
            "Then scroll down repeatedly — the file you are looking for starts with index '3028' "
            "You should make small and slow scrolls (at most 5 pixels at a time), so that you can do not miss the file."
            "Once the file starting with '3028_...' is visible, stop scrolling and click on it to select it, "
            "then click the 'Open' button to confirm. "
            "Output 'done' when the file has been successfully opened."
        ),
        "max_steps": 100,
        "sleep": 0.3,
    },

    # ── Capture all views ──────────────────────────────────────────────────────
    *capture_views(OUTPUT_DIR),
]
