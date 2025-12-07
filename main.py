import argparse
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'src/agenda_builder'))
from agenda_builder import *
from example_agenda import *
from csv_parser import *

# --- Configuration Defaults ---
AGENDA_DEFAULTS = {
    "start_date_str": None,
    "end_date_str": None,
    "start_time": None,
    "end_time": None,
    "granularity_minutes": 15,
    "title": "My Winter School 2025",
    "day_str_format": "%a, %d.%m",
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
        '--day-str-format', type=str, default=None,
        help=f'Format for day string in header row. Default: {AGENDA_DEFAULTS["day_str_format"]}'
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
        create_example_agenda(agenda)
        print("% Using hardcoded example agenda.")

    # 3. Generate LaTeX
    if not args.legacy:
        # Generate using the preferred TikZ method
        latex_code = agenda.generate_latex_tikz(
            granularity_minutes=args.granularity,
            day_str_format=args.day_str_format,
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
            day_str_format=args.day_str_format,
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