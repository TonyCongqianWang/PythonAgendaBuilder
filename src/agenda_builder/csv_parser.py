import pandas as pd
import numpy as np
import matplotlib as mplt
import re
import colorsys
import datetime


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