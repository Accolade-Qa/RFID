from pathlib import Path
from PIL import Image, ImageTk
import ttkbootstrap as ttkb


def build_header_frame(parent_frame, base_dir: Path) -> ttkb.Frame:
    """Build and return the application header frame with logo, updated title, and version label."""
    header_frame = ttkb.Frame(parent_frame, style="Header.TFrame")
    header_frame.pack(fill="x", pady=(0, 15), padx=15)

    # Added height and padding to section
    inner_container = ttkb.Frame(header_frame)
    inner_container.pack(fill="x", pady=12, padx=10)

    logo_path = base_dir / "assets" / "Acc_logo.png"
    photo = None
    if logo_path.exists():
        try:
            image = Image.open(logo_path)
            image = image.resize((130, 85))
            photo = ImageTk.PhotoImage(image)
        except Exception:
            photo = None

    if photo:
        logo_label = ttkb.Label(inner_container, image=photo, bootstyle="light")
        logo_label.image = photo  # Keep reference
        logo_label.pack(side="left", padx=(0, 24), pady=(5, 5))

    header_text = ttkb.Label(
        inner_container,
        text="RFID Tag Reader & Writer - DVP",
        style="Title.TLabel",
    )
    header_text.pack(side="left", pady=10)

    version_label = ttkb.Label(
        inner_container,
        text="Version: 1.0.0",
        style="Field.TLabel",
    )
    version_label.pack(side="right", pady=10)

    return header_frame
