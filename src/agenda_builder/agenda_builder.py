import datetime
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Union

# --- Intermediate Data Structures ---

@dataclass
class AgendaEventData:
    """Holds metadata for a specific event definition."""
    internal_id: int
    color: str
    title: str
    subtext: str
    subtext_size: str
    open_ended: bool

@dataclass
class CompiledAgenda:
    """
    The 'Frozen' state of an agenda, ready for rendering.
    This acts as the bridge between Logic and View.
    """
    title: str
    start_date: datetime.date
    end_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    granularity: datetime.timedelta
    num_days: int
    num_slots: int
    
    # The logical grid: grid[slot_index][day_index] -> {'id': int, 'frac_start': float}
    grid: List[List[Optional[Dict[str, Any]]]]
    
    # Metadata maps
    events: Dict[int, AgendaEventData]
    colors: Dict[str, str]
    special_events: List[Dict[str, Any]]

# --- Part 1: Logic & Construction ---

class AgendaBuilder:
    def __init__(self, start_date_str=None, end_date_str=None, start_time=None, end_time=None):
        # User Preferences
        try:
            self.pref_start_date = datetime.datetime.strptime(start_date_str, "%Y%m%d").date() if start_date_str else None
            self.pref_end_date = datetime.datetime.strptime(end_date_str, "%Y%m%d").date() if end_date_str else None
        except ValueError:
            self.pref_start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
            self.pref_end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
        self.pref_start_time = datetime.datetime.strptime(start_time, "%H:%M").time() if start_time else None
        self.pref_end_time = datetime.datetime.strptime(end_time, "%H:%M").time() if end_time else None
        
        # Internal State
        self.pending_events = [] 
        self.events: Dict[int, AgendaEventData] = {}
        self.external_eventids = {}
        self.event_counter = 0
        self.colors = {}
        self.special_events = []
        self.title = "Weekly Agenda"
        
        # Cache
        self._cached_compilation: Optional[CompiledAgenda] = None

    def set_title(self, title):
        self.title = title
        self._cached_compilation = None

    def define_color(self, name, r, g, b):
        self.colors[name] = f"{{rgb}}{{{r},{g},{b}}}"

    def add_special_event(self, date_str, time_range, title, subtext, color_name="colVisit"):
        if isinstance(time_range, str):
            time_range = (time_range,)
        self.special_events.append({
            'date': date_str,
            'time_range': time_range,
            'title': title,
            'subtext': subtext,
            'color': color_name
        })

    def add_event(self, event_color, event_title, event_subtext=None,  time_ranges=None, subtext_size=None, open_ended=False, event_id=None):
        time_ranges = time_ranges if time_ranges is not None else []
        if isinstance(time_ranges, tuple):
            time_ranges = [time_ranges]
            
        event_subtext = event_subtext if event_subtext else ""
        subtext_size = subtext_size if subtext_size else "normalsize"
        
        if not (event_id is None or event_id == "" or event_id.isspace()):
            if event_id not in self.external_eventids:
                self.event_counter += 1
                self.external_eventids[event_id] = self.event_counter
            internal_event_id = self.external_eventids[event_id]   
        else:
            self.event_counter += 1
            internal_event_id = self.event_counter
        
        event_data = AgendaEventData(
            internal_id=internal_event_id,
            color=event_color,
            title=event_title,
            subtext=event_subtext,
            subtext_size=subtext_size,
            open_ended=open_ended
        )
        
        self.events[internal_event_id] = event_data
        
        self.pending_events.append({
            'internal_id': internal_event_id,
            'ranges': time_ranges
        })
        
        self._cached_compilation = None
        return internal_event_id

    def extend_event(self, internal_event_id, time_ranges):
        if internal_event_id not in self.events:
            raise ValueError(f"Event ID {internal_event_id} does not exist.")
        
        if isinstance(time_ranges, tuple):
            time_ranges = [time_ranges]

        self.pending_events.append({
            'internal_id': internal_event_id,
            'ranges': time_ranges
        })
        self._cached_compilation = None

    def build(self, granularity_minutes=None) -> CompiledAgenda:
        """
        Compiles the agenda and returns a frozen data object ready for rendering.
        """
        if self._cached_compilation:
            return self._cached_compilation

        granularity = 15 if not granularity_minutes else granularity_minutes
        granularity = datetime.timedelta(minutes=granularity_minutes)

        # 1. Parse Ranges & Infer Bounds
        all_dates = []
        all_times = []
        parsed_pending_events = [] 

        for p_ev in self.pending_events:
            internal_id = p_ev['internal_id']
            parsed_ranges = []
            
            for entry in p_ev['ranges']:
                if len(entry) != 3: continue
                d_str, s_str, e_str = entry
                try:
                    d = datetime.datetime.strptime(d_str, "%Y%m%d").date()
                except ValueError:
                    d = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
                s = datetime.datetime.strptime(s_str, "%H:%M").time()
                e = datetime.datetime.strptime(e_str, "%H:%M").time() if e_str is not None else None
                
                parsed_ranges.append((d, s, e))
                all_dates.append(d)
                all_times.append(s)
                if e is not None:
                    all_times.append(e)
            
            parsed_pending_events.append({
                'internal_id': internal_id,
                'ranges': parsed_ranges
            })

        # Calculate Start/End Date
        start_date = self.pref_start_date or (min(all_dates) if all_dates else datetime.date.today())
        end_date = self.pref_end_date or (max(all_dates) if all_dates else start_date)
        num_days = (end_date - start_date).days + 1

        # Calculate Start/End Time
        start_time = self.pref_start_time or (min(all_times) if all_times else datetime.time(8, 0))
        # Ensure we capture the end of the last event
        end_time = self.pref_end_time or (max(all_times) if all_times else datetime.time(18, 0))

        # Calculate Slots
        t_start = datetime.datetime.combine(datetime.date.today(), start_time)
        t_end = datetime.datetime.combine(datetime.date.today(), end_time)
        if t_end <= t_start: t_end += datetime.timedelta(days=1)
            
        diff_seconds = (t_end - t_start).total_seconds()
        num_slots = int(math.ceil(diff_seconds / granularity.total_seconds()))

        # 2. Initialize Logic Grid
        grid = [[None for _ in range(num_days)] for _ in range(num_slots)]

        # 3. Populate Grid
        # Helper helpers locally since we are inside the build method
        def _get_day_index(date_obj):
            delta = (date_obj - start_date).days
            return delta if 0 <= delta < num_days else None

        def _get_time_index(time_obj):
            start_mins = start_time.hour * 60 + start_time.minute
            target_mins = time_obj.hour * 60 + time_obj.minute
            if target_mins < start_mins: target_mins += 24 * 60
            diff = target_mins - start_mins
            return diff / (granularity.seconds / 60) if diff >= 0 else None

        for item in parsed_pending_events:
            internal_id = item['internal_id']
            for d, s, e in item['ranges']:
                curr_dt = datetime.datetime.combine(d, s)
                if e is not None:
                    limit_dt = datetime.datetime.combine(d, e)
                else:
                    limit_dt = curr_dt + granularity
                
                while curr_dt < limit_dt:
                    d_idx = _get_day_index(d)
                    t_idx_float = _get_time_index(curr_dt.time())
                    
                    if d_idx is not None and t_idx_float is not None:
                        t_idx_int = int(math.floor(t_idx_float))
                        if 0 <= t_idx_int < num_slots:
                            grid[t_idx_int][d_idx] = {
                                'id': internal_id,
                                'frac_start': t_idx_float, 
                            }
                    curr_dt += granularity

        self._cached_compilation = CompiledAgenda(
            title=self.title,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            granularity=granularity,
            num_days=num_days,
            num_slots=num_slots,
            grid=grid,
            events=self.events,
            colors=self.colors,
            special_events=self.special_events
        )
        return self._cached_compilation

    def generate_latex_tikz(self, granularity_minutes=None, scale=0.46, width_pct=2.2, height_pct=1.4, stripe_interval=2, gap_x_pct=0.03, gap_y_pct=0.0, ext_y_pct=0.15):
        compiled_data = self.build(granularity_minutes)
        renderer = AgendaLatexRenderer(compiled_data)
        return renderer.render_tikz(scale, width_pct, height_pct, stripe_interval, gap_x_pct, gap_y_pct, ext_y_pct)

    def generate_latex_legacygrid(self, granularity_minutes=None, scale=0.4, width_pct=1.0, height_pct=1.2, multirow_correction_factor=3.5, text_vpos_bias=-0.0):
        compiled_data = self.build(granularity_minutes)
        renderer = AgendaLatexRenderer(compiled_data)
        return renderer.render_legacy_grid(scale, width_pct, height_pct, multirow_correction_factor, text_vpos_bias)





# --- Part 2: Rendering ---

class AgendaLatexRenderer:
    def __init__(self, data: CompiledAgenda):
        self.data = data

    @staticmethod
    def _sanitize(text):
        if not text: return ""
        chars = {
            "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
            "_": r"\_", "{": r"\{", "}": r"\}",
        }
        text = str(text)
        for char, escaped in chars.items():
            text = text.replace(char, escaped)
        return text

    def _add_special_events_to_latex(self, latex, evs):
        for ev in evs:
            self._add_special_event_to_latex(latex, ev)


    def _add_special_event_to_latex(self, latex, ev):
        start_time = self._sanitize(ev['time_range'][0])
        
        if len(ev['time_range']) > 1 and ev['time_range'][1]:
            time_content = f"{start_time} -- {self._sanitize(ev['time_range'][1])}"
        else:
            time_content = start_time
        separator = r"\quad "

        latex.append(rf"\begin{{tcolorbox}}[colback={ev['color']}!30!white, colframe=black, boxrule=1.25pt, title=\textbf{{{self._sanitize(ev['date'])}}}]")
       
        latex.append(
            rf"\textbf{{{time_content}}}"
            rf"{separator}" 
            rf"{self._sanitize(ev['title'])} \subtxt{{{self._sanitize(ev['subtext'])}}}"
        )
        
        latex.append(r"\end{tcolorbox}")
        latex.append(r"\vspace{0.13cm}")

    def _create_render_grid(self):
        """
        Transforms the Logical Grid (Data) into a Visual Grid (Layout).
        Calculates text spans, offsets, and merging of cells.
        """
        rows = self.data.num_slots
        cols = self.data.num_days
        render_grid = [[{} for _ in range(cols)] for _ in range(rows)]
        
        # --- PASS 1: Merge Grid Data with Event Metadata ---
        for r in range(rows):
            for c in range(cols):
                cell_data = self.data.grid[r][c]
                event_data = None
                
                if cell_data is not None:
                    # Look up full event details from the ID
                    evt_obj = self.data.events.get(cell_data['id'])
                    if evt_obj:
                        event_data = {
                            'id': cell_data['id'],
                            'frac_start': cell_data['frac_start'],
                            'color': evt_obj.color,
                            'title': evt_obj.title,
                            'subtext': evt_obj.subtext,
                            'subtext_size': evt_obj.subtext_size,
                            'open_ended': evt_obj.open_ended
                        }

                render_grid[r][c] = {
                    'id': event_data['id'] if event_data else None,
                    'bg_color': event_data['color'] if event_data else None,
                    'text': None,
                    'frac_start': event_data['frac_start'] if event_data else None,
                    'open_ended': event_data['open_ended'] if event_data else False,
                    'raw_data': event_data, # store for later reference
                    'span': 1
                }

        # --- PASS 2: Text Placement & Span Calculation ---
        processed_ids = set()
        for r in range(rows):
            for c in range(cols):
                cell_data = self.data.grid[r][c]
                if not cell_data: continue
                eid = cell_data['id']
                if eid in processed_ids: continue
                
                # Identify all cells belonging to this event ID
                event_cells = []
                for rr in range(rows):
                    for cc in range(cols):
                        if render_grid[rr][cc]['id'] == eid:
                            event_cells.append((rr, cc))
                
                if not event_cells: continue
                
                # Determine "Center of Gravity" for the text
                all_cols = [x[1] for x in event_cells]
                min_col, max_col = min(all_cols), max(all_cols)
                center_col = int((min_col + max_col) // 2.0)
                if (max_col - min_col) % 2 == 0:
                    x_offset_cols = 0.0
                    center_col_cells = [x for x in event_cells if x[1] == center_col]
                else:
                    x_offset_cols = 0.5
                    center_col_cells = [x for x in event_cells if x[1] == center_col]
                    center_col_cells = [x for x in center_col_cells if render_grid[x[0]][center_col + 1]['id'] == eid]
                
                
                if not center_col_cells:
                    visual_start_row = min(x[0] for x in event_cells)
                    # Find a column in the top row to anchor to
                    top_row_cols = [x[1] for x in event_cells if x[0] == visual_start_row]
                    center_col = min(top_row_cols) + (max(top_row_cols) - min(top_row_cols)) // 2
                else:
                    visual_start_row = min(x[0] for x in center_col_cells)

                # Calculate Vertical Span
                bottom_row = visual_start_row
                for i in range(visual_start_row, rows):
                    if render_grid[i][center_col]['id'] == eid:
                        bottom_row = i
                    else:
                        break
                
                span = bottom_row - visual_start_row + 1
                final_span = span if span == 1 else -span
                
                # Retrieve metadata to write text
                evt_obj = self.data.events.get(eid)
                frac_start_val = self.data.grid[visual_start_row][center_col]['frac_start']

                render_grid[bottom_row][center_col]['text'] = {
                    'title': self._sanitize(evt_obj.title),
                    'subtext': self._sanitize(evt_obj.subtext),
                    'subtext_size': evt_obj.subtext_size,
                    'frac_start': frac_start_val,
                    'x_offset_cols': x_offset_cols
                }
                render_grid[bottom_row][center_col]['span'] = final_span
                processed_ids.add(eid)
                
        return render_grid

    def render_legacy_grid(self, scale=0.4, width_pct=1.0, height_pct=1.2, multirow_correction_factor=3.5, text_vpos_bias=-0.0):
        USABLE_WIDTH_CM = 26.7
        USABLE_HEIGHT_CM = 18.0
        
        target_width = USABLE_WIDTH_CM * width_pct
        target_height = USABLE_HEIGHT_CM * height_pct
        
        time_col_width = 1.5
        remaining_width = target_width - time_col_width
        col_width = remaining_width / self.data.num_days
        
        header_height = 0.8
        remaining_height = target_height - header_height
        if remaining_height < 1: remaining_height = 1
        row_height_cm = remaining_height / self.data.num_slots

        render_grid = self._create_render_grid()
        
        # Calculate Borders
        rows, cols = self.data.num_slots, self.data.num_days
        for r in range(rows):
            for c in range(cols):
                cell = render_grid[r][c]
                curr_id = cell['id']
                
                # Left
                if c == 0: cell['border_l'] = 'THICK'
                elif curr_id != render_grid[r][c-1]['id']: cell['border_l'] = 'THICK'
                else: cell['border_l'] = 'THIN'
                # Right
                if c == cols - 1: cell['border_r'] = 'THICK'
                elif curr_id != render_grid[r][c+1]['id']: cell['border_r'] = 'THICK'
                else: cell['border_r'] = 'THIN'
                # Bottom
                if r == rows - 1: cell['border_b'] = 'THICK'
                elif r < rows - 1 and curr_id != render_grid[r+1][c]['id']: cell['border_b'] = 'THICK'
                else: cell['border_b'] = 'THIN'
        
        latex = []
        latex.append(r"""\documentclass[a4paper, landscape]{article}
\usepackage[left=1.5cm, right=1.5cm, top=1.5cm, bottom=1.5cm]{geometry}
\usepackage{tcolorbox}
\usepackage[table]{xcolor} 
\usepackage{array}
\usepackage{hhline}
\usepackage{graphicx} 
\usepackage{multirow}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\renewcommand{\familydefault}{\sfdefault}
\newcommand{\subtxt}[1]{{\small \itshape #1}}
""")
        
        for name, spec in self.data.colors.items():
            latex.append(f"\\definecolor{{{name}}}{spec}")
            
        latex.append(r"""
\begin{document}
\pagestyle{empty}
{\Huge \textbf{""" + self._sanitize(self.data.title) + r"""}}
\vspace{0.23cm}
""")
        
        self._add_special_events_to_latex(latex, self.data.special_events)

        V_THICK = r"!{\color{black}\vrule width 1.5pt}" 
        V_THIN = r"!{\color{lightgray!60}\vrule width 0.8pt}" 
        H_THICK = r">{\arrayrulecolor{black}\setlength\arrayrulewidth{1.5pt}}-"
        H_THIN = r">{\arrayrulecolor{lightgray!60}}-" 
        H_INTER = r">{\arrayrulecolor{black}\setlength\arrayrulewidth{1.5pt}}|"

        base_col_def = f"c" + (f"m{{{col_width:.2f}cm}}" * self.data.num_days)

        latex.append(r"\noindent\makebox[\textwidth][c]{%")
        if scale != 1.0: latex.append(rf"\scalebox{{{scale}}}{{%")
        latex.append(r"\setlength\arrayrulewidth{0.4pt}")
        latex.append(r"\renewcommand{\arraystretch}{1.1}") 
        latex.append(f"\\begin{{tabular}}{{{base_col_def}}}")
        
        # Header
        top_hhline = [H_INTER, H_THICK, H_INTER] 
        for _ in range(self.data.num_days):
            top_hhline.extend([H_THICK, H_INTER])
        latex.append(r"\hhline{" + "".join(top_hhline) + "}")
        
        header_row = f"\\multicolumn{{1}}{{{V_THICK}c{V_THICK}}}{{\\textbf{{Time}}}}"
        current_date = self.data.start_date
        for i in range(self.data.num_days):
            day_str = current_date.strftime("%a, %d.%m")
            style = f"{V_THICK}c"
            if i == self.data.num_days - 1: style += V_THICK
            header_row += f" & \\multicolumn{{1}}{{{style}}}{{\\textbf{{{day_str}}}}}"
            current_date += datetime.timedelta(days=1)
        latex.append(header_row + r" \\")
        latex.append(r"\hhline{" + "".join(top_hhline) + "}")
        
        # Rows
        t_current = datetime.datetime.combine(datetime.date.today(), self.data.start_time)
        for r in range(self.data.num_slots):
            time_str = t_current.strftime("%H:%M")
            row_str = f"\\multicolumn{{1}}{{{V_THICK}c{V_THICK}}}{{\\parbox[t][{row_height_cm:.3f}cm][t]{{1.4cm}}{{\\centering \\small {time_str}}}}}"
            
            for c in range(self.data.num_days):
                cell = render_grid[r][c]
                left_style = V_THICK if cell['border_l'] == 'THICK' else V_THIN
                right_style = V_THICK if cell['border_r'] == 'THICK' else V_THIN
                style = f"{left_style}m{{{col_width:.2f}cm}}{right_style}"
                bg = f"\\cellcolor{{{cell['bg_color']}}}" if cell['bg_color'] else ""
                
                content = ""
                if cell['text']:
                    title_part = f"{{\\Large \\textbf{{{cell['text']['title']}}}}}"
                    sub_part = f"{{\\small {cell['text']['subtext']}}}"
                    text_data = f"{title_part} \\newline {sub_part}"
                    span = cell['span']
                    vmove = multirow_correction_factor * (abs(span) - 2) + text_vpos_bias
                    content = rf"\multirow[t]{{{span}}}{{=}}[{vmove}ex]{{{text_data}}}"
                row_str += f" & \\multicolumn{{1}}{{{style}}}{{{bg}{content}}}"
            
            latex.append(row_str + r" \\")
            
            h_parts = [H_INTER]
            if r == self.data.num_slots - 1: h_parts.append(H_THICK)
            else: h_parts.append(H_THIN)
            h_parts.append(H_INTER)
            
            for c in range(self.data.num_days):
                cell = render_grid[r][c]
                if cell['border_b'] == 'THICK': h_parts.append(H_THICK)
                else: h_parts.append(H_THIN)
                h_parts.append(H_INTER)
            latex.append(r"\hhline{" + "".join(h_parts) + "}")
            t_current += self.data.granularity

        latex.append(r"\end{tabular}")
        if scale != 1.0: latex.append(r"}")
        latex.append(r"}")
        latex.append(r"\end{document}")
        return "\n".join(latex)

    def render_tikz(self, scale=0.46, width_pct=2.2, height_pct=1.4, stripe_interval=2, gap_x_pct=0.03, gap_y_pct=0.0, ext_y_pct=0.15):
        USABLE_WIDTH_CM = 26.7
        USABLE_HEIGHT_CM = 18.0
        total_width = USABLE_WIDTH_CM * width_pct
        total_height = USABLE_HEIGHT_CM * height_pct
        
        time_col_width = 1.5
        day_col_width = (total_width - time_col_width) / self.data.num_days
        
        header_height = 0.8
        grid_height = total_height - header_height
        slot_height = grid_height / self.data.num_slots
        
        gap_x_right = day_col_width * gap_x_pct
        gap_y_bottom = slot_height * gap_y_pct
        ext_y_bottom = slot_height * ext_y_pct
        
        render_grid = self._create_render_grid()
        
        latex = []
        latex.append(r"""\documentclass[a4paper, landscape]{article}
\usepackage[left=1.5cm, right=1.5cm, top=1.5cm, bottom=1.5cm]{geometry}
\usepackage{tcolorbox}
\usepackage{tikz}
\usetikzlibrary{calc, positioning}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\renewcommand{\familydefault}{\sfdefault}
\newcommand{\subtxt}[1]{{\small \itshape #1}}

\tikzset{
    eventbox/.style={line width=0.8pt},
    gridline/.style={draw=gray!80, line width=1.0pt},
    timeline/.style={draw=black, line width=1.5pt},
    stripe/.style={fill=gray!15} 
}
""")
        for name, spec in self.data.colors.items():
            latex.append(f"\\definecolor{{{name}}}{spec}")
            
        latex.append(r"""
\begin{document}
\pagestyle{empty}
{\Huge \textbf{""" + self._sanitize(self.data.title) + r"""}}
\vspace{0.23cm}
""")

        self._add_special_events_to_latex(latex, self.data.special_events)

        latex.append(r"\noindent\makebox[\textwidth][c]{%")
        if scale != 1.0: latex.append(rf"\scalebox{{{scale}}}{{%")
        latex.append(r"\begin{tikzpicture}[x=1cm, y=-1cm]") 
        
        # 0. Striped Background
        grid_start_x = 0 
        grid_end_x = time_col_width + self.data.num_days * day_col_width
        for r in range(0, self.data.num_slots, 2 * stripe_interval):
            stripe_start_row = r + stripe_interval
            stripe_end_row = min(r + 2 * stripe_interval, self.data.num_slots)
            if stripe_start_row < self.data.num_slots:
                y_top = stripe_start_row * slot_height
                y_bottom = stripe_end_row * slot_height
                latex.append(rf"\fill[stripe] ({grid_start_x}, {y_top}) rectangle ({grid_end_x}, {y_bottom});")

        # 1. Headers
        latex.append(rf"\draw[timeline, fill=white] (0, {-header_height}) rectangle ({time_col_width}, 0);")
        latex.append(rf"\node[anchor=center] at ({time_col_width/2}, {-header_height/2}) {{\textbf{{Time}}}};")
        
        current_date = self.data.start_date
        for i in range(self.data.num_days):
            x_start = time_col_width + i * day_col_width
            x_end = x_start + day_col_width
            day_str = current_date.strftime("%a, %d.%m")
            latex.append(rf"\draw[timeline, fill=white] ({x_start}, {-header_height}) rectangle ({x_end}, 0);")
            latex.append(rf"\node[anchor=center] at ({x_start + day_col_width/2}, {-header_height/2}) {{\textbf{{{day_str}}}}};")
            current_date += datetime.timedelta(days=1)

        # 2. Grid Lines
        for c in range(self.data.num_days + 1):
            x = time_col_width + c * day_col_width
            latex.append(rf"\draw[gridline] ({x}, 0) -- ({x}, {grid_height});")
        for r in range(self.data.num_slots + 1):
            y = r * slot_height
            latex.append(rf"\draw[gridline] ({time_col_width}, {y}) -- ({time_col_width + self.data.num_days * day_col_width}, {y});")

        # 3. Events
        for c in range(self.data.num_days):
            r = 0
            while r < self.data.num_slots:
                cell = render_grid[r][c]
                if cell['id'] is not None:
                    start_r = r
                    current_id = cell['id']
                    is_open_ended = cell['open_ended']
                    
                    # Check Bridges
                    has_bridge_right = (c < self.data.num_days - 1 and render_grid[start_r][c+1]['id'] == current_id)
                    has_bridge_left = (c > 0 and render_grid[start_r][c-1]['id'] == current_id)
                    
                    # Find End
                    end_r = r + 1
                    while end_r < self.data.num_slots:
                        next_cell = render_grid[end_r][c]
                        if next_cell['id'] != current_id: break
                        
                        next_has_bridge_right = (c < self.data.num_days - 1 and render_grid[end_r][c+1]['id'] == current_id)
                        next_has_bridge_left = (c > 0 and render_grid[end_r][c-1]['id'] == current_id)
                        
                        if next_has_bridge_right != has_bridge_right or next_has_bridge_left != has_bridge_left: break
                        end_r += 1
                    
                    # Boundary Helpers
                    def is_true_top(check_r, check_c):
                        if check_r < 0: return True 
                        if render_grid[check_r][check_c]['id'] != current_id: return True
                        return False
                    def is_true_bottom(check_r, check_c):
                        if check_r >= self.data.num_slots: return True
                        if render_grid[check_r][check_c]['id'] != current_id: return True
                        return False

                    main_is_top = is_true_top(start_r - 1, c)
                    right_is_top = is_true_top(start_r - 1, c+1) if c < self.data.num_days - 1 else False
                    main_is_bottom = is_true_bottom(end_r, c)
                    right_is_bottom = is_true_bottom(end_r, c+1) if c < self.data.num_days - 1 else False
                    left_is_bottom = is_true_bottom(end_r, c-1) if c > 0 else False
                        
                    frac_start_top = render_grid[start_r][c]['frac_start']
                    y_top = frac_start_top * slot_height
                    base_y_bottom = end_r * slot_height
                    
                    x_left = time_col_width + c * day_col_width
                    x_right = x_left + day_col_width
                    
                    draw_border_l = not has_bridge_left
                    draw_border_r = not has_bridge_right
                    draw_border_t = main_is_top
                    
                    if main_is_bottom:
                        main_y2 = base_y_bottom + ext_y_bottom if is_open_ended else base_y_bottom - gap_y_bottom
                    else:
                        main_y2 = base_y_bottom
                    
                    main_x2 = x_right - gap_x_right
                    
                    fill_eps = 0.03
                    # Draw Main
                    latex.append(rf"\fill[{cell['bg_color']}] ({x_left}, {y_top}) rectangle ({main_x2 + fill_eps}, {main_y2 + fill_eps});")
                    if draw_border_t: latex.append(rf"\draw[eventbox] ({x_left}, {y_top}) -- ({main_x2}, {y_top});")
                    if main_is_bottom and not is_open_ended: latex.append(rf"\draw[eventbox] ({x_left}, {main_y2}) -- ({main_x2}, {main_y2});")
                    if draw_border_l: latex.append(rf"\draw[eventbox] ({x_left}, {y_top}) -- ({x_left}, {main_y2});")
                    if draw_border_r: latex.append(rf"\draw[eventbox] ({main_x2}, {y_top}) -- ({main_x2}, {main_y2});")

                    # Draw Bridge Right
                    if has_bridge_right:
                        bridge_x1, bridge_x2 = main_x2, x_right 
                        bridge_is_top = main_is_top or right_is_top
                        bridge_is_bottom = main_is_bottom or right_is_bottom
                        
                        if bridge_is_bottom:
                            bridge_y2 = base_y_bottom + ext_y_bottom if is_open_ended else base_y_bottom - gap_y_bottom
                        else:
                            bridge_y2 = base_y_bottom
                        
                        latex.append(rf"\fill[{cell['bg_color']}] ({bridge_x1}, {y_top}) rectangle ({bridge_x2 + fill_eps}, {bridge_y2 + fill_eps});")
                        if bridge_is_top: latex.append(rf"\draw[eventbox] ({bridge_x1}, {y_top}) -- ({bridge_x2}, {y_top});")
                        if bridge_is_bottom and not is_open_ended: latex.append(rf"\draw[eventbox] ({bridge_x1}, {bridge_y2}) -- ({bridge_x2}, {bridge_y2});")
                        
                        if abs(main_y2 - bridge_y2) > 0.001:
                            latex.append(rf"\draw[eventbox] ({main_x2}, {min(main_y2, bridge_y2)}) -- ({main_x2}, {max(main_y2, bridge_y2)});")

                    # Patch Left
                    if has_bridge_left:
                        left_bridge_is_bottom = main_is_bottom or left_is_bottom
                        if left_bridge_is_bottom:
                            left_bridge_y2 = base_y_bottom + ext_y_bottom if is_open_ended else base_y_bottom - gap_y_bottom
                        else:
                            left_bridge_y2 = base_y_bottom
                        if abs(main_y2 - left_bridge_y2) > 0.001:
                            latex.append(rf"\draw[eventbox] ({x_left}, {min(main_y2, left_bridge_y2)}) -- ({x_left}, {max(main_y2, left_bridge_y2)});")
                            
                    r = end_r
                else:
                    r += 1

        # 4. Time Axis
        latex.append(rf"\draw[timeline] ({time_col_width}, 0) -- ({time_col_width}, {grid_height});")
        latex.append(rf"\draw[timeline] (0, 0) -- (0, {grid_height});")
        t_current = datetime.datetime.combine(datetime.date.today(), self.data.start_time)
        for r in range(self.data.num_slots):
            y_top = r * slot_height
            time_str = t_current.strftime("%H:%M")
            y_line = (r+1) * slot_height
            latex.append(rf"\draw[timeline] (0, {y_line}) -- ({time_col_width}, {y_line});")
            latex.append(rf"\node[anchor=north, font=\small] at ({time_col_width/2}, {y_top}) {{{time_str}}};")
            t_current += self.data.granularity

        # 5. Content
        for r in range(self.data.num_slots):
            for c in range(self.data.num_days):
                cell = render_grid[r][c]
                if cell['text']:
                    frac_start = cell['text']['frac_start']
                    span = cell['span']
                    num_rows = abs(span)
                    y_top = frac_start * slot_height
                    base_y_bottom = (frac_start + num_rows) * slot_height
                    is_open_ended = cell.get('open_ended', False)
                    y_actual_bottom = base_y_bottom + ext_y_bottom if is_open_ended else base_y_bottom - gap_y_bottom
                    y_center = (y_top + y_actual_bottom) / 2
                    x_left = time_col_width + c * day_col_width
                    x_center = x_left + day_col_width / 2 + cell['text'].get('x_offset_cols', 0.0) * day_col_width - gap_x_right / 2
                    
                    title_part = f"{{\\Large \\textbf{{{cell['text']['title']}}}}}"
                    sz = cell['text'].get('subtext_size', 'normalsize')
                    sub_part = f"{{\\{sz} {cell['text']['subtext']}}}"
                    text_data = f"{title_part} \\\\ {sub_part}" 
                    txt_w = day_col_width - 0.2 
                    latex.append(rf"\node[anchor=center, align=center, text width={txt_w}cm] at ({x_center}, {y_center}) {{{text_data}}};")

        latex.append(r"\end{tikzpicture}")
        if scale != 1.0: latex.append(r"}")
        latex.append(r"}")
        latex.append(r"\end{document}")
        return "\n".join(latex)