import argparse
import datetime
import pandas as pd
import numpy as np
import matplotlib as mplt
import colorsys
import re
from agenda_builder import *

# --- Configuration Defaults ---
AGENDA_DEFAULTS = {
    "start_date_str": "20251201",
    "end_date_str": "20251205",
    "start_time": "09:00",
    "end_time": "16:00",
    "granularity_minutes": 15,
    "title": "My Winter School 2025"
}

RENDER_DEFAULTS = {
    "scale": 0.48,
    "width_pct": 2.2,
    "height_pct": 1.4,
    "gap_x_pct": 0.05,
    "gap_y_pct": 0.0,
    "ext_y_pct": 0.3,
    "multirow_correction_factor": 3.5,
}

# Expected columns for CSV input
CSV_COLUMNS = [
    "EVENT_TITLE", "EVENT_START", "EVENT_END", "EVENT_TEXT", "EVENT_TEXT_SIZE",
    "EVENT_ID", "EVENT_COLOR", "IS_OPEN_ENDED", "IS_SPECIAL"
]

# Map for explicit non-None defaults
DEFAULTS_MAP = {
    "IS_OPEN_ENDED": False,
    "IS_SPECIAL": False,
    "EVENT_TEXT": "",
    # Optional columns will default to np.nan (None) which is desired.
}


# --- Color Management ---

class ColorManager:
    """Manages color assignment, supporting hex, index-based palettes, and auto-assignment."""
    def __init__(self, palette_name):
        self.auto_color_index = 0
        self.palette_name = palette_name
        self.defined_colors = {}
        self.color_aliases = {}

    def _get_fixed_rgb_cycle(self, index):
        """Simple fallback cycle using HSV conversion for distinct, cycling colors."""
        h = (index * 0.6180339887) % 1.0 # Golden ratio increment for distinct colors
        r, g, b = colorsys.hsv_to_rgb(h, 0.7, 0.9)
        return r, g, b

    def get_auto_color(self):
        def scramble_float(i):
            MODULUS = 2**32
            mixed = i * 2654435761
            return ((mixed ^ (mixed >> 16)) & (MODULUS - 1)) / MODULUS

        color_key = f"auto_color_{self.auto_color_index}"
        if color_key not in self.defined_colors:
            try:
                cmap = mplt.colormaps.get_cmap(self.palette_name)
                color_float = scramble_float(self.auto_color_index)
                rgba = cmap(color_float) 
                r, g, b = rgba[0], rgba[1], rgba[2]
                self.defined_colors[color_key] = (r, g, b)
                self.auto_color_index += 1
            except ValueError:
                print(f"% Warning: Colormap '{self.palette_name}' not found. Defaulting to a fixed RGB cycle.")
                r, g, b = self._get_fixed_rgb_cycle(self.auto_color_index)
                self.defined_colors[color_key] = (r, g, b)
                self.auto_color_index += 1
        return color_key

    def get_rgb_from_color(self, color_spec):
        """
        Processes a color specification (hex string, index int, or None) 
        and returns a unique key for the AgendaBuilder.
        """
        # Handle None, NaN, or empty string -> Auto-assign
        if pd.isna(color_spec) or color_spec is None or color_spec == "":
            return self.get_auto_color()
            
        color_spec = str(color_spec).strip()

        # 1. Hex Color (e.g., #FF99AA or FF99AA)
        hex_match = re.match(r'^#?([0-9a-fA-F]{6})$', color_spec)
        if hex_match:
            hex_val = hex_match.group(1)
            r = int(hex_val[0:2], 16) / 255.0
            g = int(hex_val[2:4], 16) / 255.0
            b = int(hex_val[4:6], 16) / 255.0
            color_key = f"hex_{hex_val}"
            if color_key not in self.defined_colors:
                self.defined_colors[color_key] = (r, g, b)
            return color_key

        if color_spec in self.color_aliases:
            return self.color_aliases[color_spec]
        color_key = self.get_auto_color()
        self.color_aliases[color_spec] = color_key
        return color_key



    def define_colors_on_agenda(self, agenda):
        """Defines all collected colors (auto/indexed/hex) on the AgendaBuilder instance."""
        for key, rgb in self.defined_colors.items():
            agenda.define_color(key, rgb[0], rgb[1], rgb[2])


# --- Event Loading from CSV ---

def load_events_from_csv(filepath, granularity_minutes, color_manager):
    """
    Reads event data from a CSV file, parses columns, and prepares events 
    for the AgendaBuilder instance.
    
    This function handles datetime conversion, assigns defaults for missing optional columns,
    and calculates time slots using the global 'time_range' utility.
    """
    df = pd.read_csv(filepath, keep_default_na=False)
    
    # Normalize column names for flexible matching (uppercase, snake_case)
    df.columns = [col.upper().replace(' ', '_') for col in df.columns]

    # Validate mandatory columns
    if "EVENT_TITLE" not in df.columns or "EVENT_START" not in df.columns:
        raise ValueError("CSV must contain columns named 'EVENT_TITLE' and 'EVENT_START'.")
        
    # Add missing optional columns with specified defaults or NaN
    for col in CSV_COLUMNS:
        if col not in df.columns:
            default_val = DEFAULTS_MAP.get(col, np.nan)
            df[col] = default_val
            
    # Data Type Conversion and Cleaning
    df["EVENT_START"] = pd.to_datetime(df["EVENT_START"], errors='coerce')
    df["EVENT_END"] = pd.to_datetime(df["EVENT_END"], errors='coerce')
    
    # Robust boolean conversion
    df["IS_OPEN_ENDED"] = df["IS_OPEN_ENDED"].astype(str).str.lower().isin(['true', '1', 'yes', 't'])
    df["IS_SPECIAL"] = df["IS_SPECIAL"].astype(str).str.lower().isin(['true', '1', 'yes', 't'])

    # Drop rows where mandatory datetime parsing failed or title is missing
    df = df.dropna(subset=["EVENT_START", "EVENT_TITLE"])

    events = []
    
    for _, row in df.iterrows():
        color_key = color_manager.get_rgb_from_color(row["EVENT_COLOR"])
        time_ranges = []

        if not row["IS_SPECIAL"]:
            start_dt = row["EVENT_START"]
            end_dt = row["EVENT_END"]
            event_date = start_dt.strftime("%Y%m%d")
            
            start_time_str = start_dt.strftime("%H:%M")
            end_time_str = None
            
            if not pd.isna(end_dt):
                end_time_str = end_dt.strftime("%H:%M")

            time_ranges = (event_date, start_time_str, end_time_str)

        # Extract optional fields, ensuring None is passed for NaN/missing values
        text_size = row["EVENT_TEXT_SIZE"]
        if pd.isna(text_size):
            text_size = None
            
        event_id = row["EVENT_ID"]
        if pd.isna(event_id):
            event_id = None

        events.append({
            "title": row["EVENT_TITLE"],
            "start_dt": row["EVENT_START"],
            "end_dt": row["EVENT_END"],
            "text": row["EVENT_TEXT"],
            "text_size": text_size,
            "event_id": event_id,
            "color": color_key,
            "is_open_ended": row["IS_OPEN_ENDED"],
            "is_special": row["IS_SPECIAL"],
            "time_ranges": time_ranges,
        })
        
    return events

def add_csv_events_to_agenda(agenda, events):
    """
    Adds events parsed from the CSV to the AgendaBuilder instance.
    """
 
    for event in events:
        if event["is_special"]:
            date_str = event["start_dt"].strftime("%A, %B %d, %Y")
            time_str = event["start_dt"].strftime("%H:%M")
            agenda.add_special_event(date_str, time_str, event["title"], event["text"], event["color"])
        
        elif not event["time_ranges"]:
            print(f"% Warning: Regular event '{event['title']}' on {event['start_dt'].date()} has no time ranges generated (check start/end times or granularity). Skipping.")
            
        else:
            agenda_event_ref = agenda.add_event(
                event["color"], 
                event["title"], 
                event["text"],
                event_id=event["event_id"],
                time_ranges=event["time_ranges"],
                subtext_size=event["text_size"],
                open_ended=event["is_open_ended"],
            )
            


# --- Main Execution ---

def main():
    """Parses arguments, creates agenda, and generates LaTeX output."""
    parser = argparse.ArgumentParser(
        description="An utility for generating LaTeX calendar agendas (using TikZ) either from a structured CSV file or a hardcoded example schedule. Outputs the finished LaTeX code to standard output or a specified file."
    )

    # --- Agenda Configuration Group ---
    group_agenda = parser.add_argument_group('Agenda Configuration (Defaults to Example Settings)')
    group_agenda.add_argument(
        '--start-date', type=str, default=AGENDA_DEFAULTS["start_date_str"],
        help=f'Start date for the agenda (YYYYMMDD). Default: {AGENDA_DEFAULTS["start_date_str"]}'
    )
    group_agenda.add_argument(
        '--end-date', type=str, default=AGENDA_DEFAULTS["end_date_str"],
        help=f'End date for the agenda (YYYYMMDD). Default: {AGENDA_DEFAULTS["end_date_str"]}'
    )
    group_agenda.add_argument(
        '--start-time', type=str, default=AGENDA_DEFAULTS["start_time"],
        help=f'Start time for daily events (HH:MM). Default: {AGENDA_DEFAULTS["start_time"]}'
    )
    group_agenda.add_argument(
        '--end-time', type=str, default=AGENDA_DEFAULTS["end_time"],
        help=f'End time for daily events (HH:MM). Default: {AGENDA_DEFAULTS["end_time"]}'
    )
    group_agenda.add_argument(
        '--granularity', type=int, default=AGENDA_DEFAULTS["granularity_minutes"],
        help=f'Time granularity in minutes. Default: {AGENDA_DEFAULTS["granularity_minutes"]}'
    )
    group_agenda.add_argument(
        '--title', type=str, default=AGENDA_DEFAULTS["title"],
        help=f'Title of the agenda. Default: "{AGENDA_DEFAULTS["title"]}"'
    )
    
    # --- Input and Color Options Group ---
    group_input = parser.add_argument_group('Input and Color Options')
    group_input.add_argument(
        '--csv-file', type=str, default=None,
        help='If set, events are loaded from this CSV file instead of the example agenda.'
    )
    group_input.add_argument(
        '--palette', type=str, default='tab20',
        help="Matplotlib colormap for indexed/automatic colors (e.g., 'gist_rainbow', 'tab20', 'BuPu', 'GnBu', 'PuBu''). Default: 'tab20'"
    )

    # --- Rendering Options Group ---
    group_render = parser.add_argument_group('Rendering Options')
    group_render.add_argument(
        '--file', type=str, default=None,
        help='If set, outputs the LaTeX code to the specified file instead of stdout.'
    )
    group_render.add_argument(
        '--legacy', action='store_true',
        help='If set, enables the legacy grid rendering mode (using multirow/tabular). Otherwise, uses modern TikZ rendering.'
    )
    group_render.add_argument('--scale', type=float, default=RENDER_DEFAULTS["scale"], help=f'Render scale factor. Default: {RENDER_DEFAULTS["scale"]}')
    group_render.add_argument('--width_pct', type=float, default=RENDER_DEFAULTS["width_pct"], help=f'Width percentage for TikZ rendering. Default: {RENDER_DEFAULTS["width_pct"]}')
    group_render.add_argument('--height_pct', type=float, default=RENDER_DEFAULTS["height_pct"], help=f'Height percentage for TikZ rendering. Default: {RENDER_DEFAULTS["height_pct"]}')
    group_render.add_argument('--gap_x_pct', type=float, default=RENDER_DEFAULTS["gap_x_pct"], help=f'X-axis gap percentage for TikZ rendering. Default: {RENDER_DEFAULTS["gap_x_pct"]}')
    group_render.add_argument('--gap_y_pct', type=float, default=RENDER_DEFAULTS["gap_y_pct"], help=f'Y-axis gap percentage for TikZ rendering. Default: {RENDER_DEFAULTS["gap_y_pct"]}')
    group_render.add_argument('--ext_y_pct', type=float, default=RENDER_DEFAULTS["ext_y_pct"], help=f'Y-axis extension percentage for TikZ rendering. Default: {RENDER_DEFAULTS["ext_y_pct"]}')
    group_render.add_argument('--multirow_correction_factor', type=float, default=RENDER_DEFAULTS["multirow_correction_factor"], help=f'Correction factor for legacy multirow events. Default: {RENDER_DEFAULTS["multirow_correction_factor"]}')

    args = parser.parse_args()

    # 1. Setup AgendaBuilder
    agenda = AgendaBuilder(
        start_date_str=args.start_date,
        end_date_str=args.end_date,
        start_time=args.start_time,
        end_time=args.end_time,
    )
    agenda.set_title(args.title)

    # 2. Load Events
    if args.csv_file:
        try:
            color_manager = ColorManager(palette_name=args.palette)
            events = load_events_from_csv(args.csv_file, args.granularity, color_manager)
            
            # Define all collected colors (auto/indexed/hex) on the agenda
            color_manager.define_colors_on_agenda(agenda)
            
            # Add the events to the agenda
            add_csv_events_to_agenda(agenda, events)
            
            print(f"% Successfully loaded and added {len(events)} event rows from {args.csv_file} using palette '{args.palette}'.")

        except Exception as e:
            print(f"% Error processing CSV file: {e}")
            return
    else:
        # Load the hardcoded example
        import example_agenda
        example_agenda.create_example_agenda(agenda)
        print("% Using hardcoded example agenda.")

    # 3. Generate LaTeX
    if not args.legacy:
        # Generate using the preferred TikZ method
        latex_code = agenda.generate_latex_tikz(
            granularity_minutes=args.granularity,
            scale=args.scale,
            width_pct=args.width_pct,
            height_pct=args.height_pct,
            gap_x_pct=args.gap_x_pct,
            gap_y_pct=args.gap_y_pct,
            ext_y_pct=args.ext_y_pct
        )
    else:
        # Generate using the legacy grid method
        latex_code = agenda.generate_latex_legacygrid(
            granularity_minutes=args.granularity,
            scale=args.scale,
            width_pct=args.width_pct,
            height_pct=args.height_pct,
            multirow_correction_factor=args.multirow_correction_factor
        )

    # 4. Output
    if args.file:
        with open(args.file, 'w') as f:
            f.write(latex_code)
        print(f"% LaTeX code successfully written to {args.file}")
    else:
        print("% ////----- LaTeX Output -----////")
        print(latex_code)

if __name__ == "__main__":
    main()