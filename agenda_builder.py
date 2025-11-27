import datetime
import math

class AgendaBuilder:
    def __init__(self, start_date_str=None, end_date_str=None, start_time=None, end_time=None, granularity_minutes=15):
        self.start_date = datetime.datetime.strptime(start_date_str, "%Y%m%d").date()
        self.end_date = datetime.datetime.strptime(end_date_str, "%Y%m%d").date()
        self.start_time = datetime.datetime.strptime(start_time, "%H:%M").time()
        self.end_time = datetime.datetime.strptime(end_time, "%H:%M").time()
        self.granularity = datetime.timedelta(minutes=granularity_minutes)
        
        self.num_days = (self.end_date - self.start_date).days + 1
        
        t_start = datetime.datetime.combine(datetime.date.today(), self.start_time)
        t_end = datetime.datetime.combine(datetime.date.today(), self.end_time)
        self.num_slots = int((t_end - t_start) / self.granularity)
        
        # Logic Grid: Stores ID and Raw Data
        self.grid = [[None for _ in range(self.num_days)] for _ in range(self.num_slots)]
        self.external_eventids = {}
        self.events = {}
        
        self.colors = {}
        self.special_events = []
        self.title = "Weekly Agenda"
        self.event_counter = 0

    def set_title(self, title):
        self.title = title

    def define_color(self, name, r, g, b):
        self.colors[name] = f"{{rgb}}{{{r},{g},{b}}}"

    def add_special_event(self, date_str, time_str, title, subtext, color_name="colVisit"):
        self.special_events.append({
            'date': date_str,
            'time': time_str,
            'title': title,
            'subtext': subtext,
            'color': color_name
        })

    def _get_time_range(start_time_str, end_time_str=None, granularity_mins=15):
        s = datetime.datetime.strptime(start_time_str, "%H:%M")
        e = datetime.datetime.strptime(end_time_str, "%H:%M") if end_time_str else s
        res = [s.time()]
        curr = s + datetime.timedelta(minutes=granularity_mins)
        while curr < e:
            res.append(curr.time())
            curr += datetime.timedelta(minutes=granularity_mins)
    return res

    def _get_day_index(self, date_obj):
        delta = (date_obj - self.start_date).days
        if 0 <= delta < self.num_days:
            return delta
        return None

    def _get_time_index(self, time_obj):
        start_mins = self.start_time.hour * 60 + self.start_time.minute
        target_mins = time_obj.hour * 60 + time_obj.minute
        diff = target_mins - start_mins
        if diff < 0: return None
        # Return fractional slot index (float)
        slot = diff / (self.granularity.seconds / 60)
        return slot

    def add_event(self, event_color, event_title, list_of_time_cells=None, event_subtext=None, subtext_size=None, open_ended=False, event_id=None):
        list_of_time_cells = list_of_time_cells if list_of_time_cells is not None else []
        event_subtext = event_subtext if event_subtext is not None else ""
        subtext_size = subtext_size if subtext_size is not None else "normalsize"
        
        if event_id is not None:
            if event_id not in self.external_eventids:
                self.event_counter += 1
                self.external_eventids[event_id] = self.event_counter
            internal_event_id = self.external_eventids[event_id]   
        else:
            self.event_counter += 1
            internal_event_id = self.event_counter
        
        event_dict = {
                        'color': event_color,
                        'title': event_title,
                        'subtext': event_subtext,
                        'subtext_size': subtext_size,
                        'open_ended': open_ended
                    }
        
        self.events[internal_event_id] = event_dict
        
        for day, time in list_of_time_cells:
            d_idx = self._get_day_index(day)
            t_idx_float = self._get_time_index(time)

            if d_idx is not None and t_idx_float is not None:
                t_idx_int = int(math.floor(t_idx_float))
                
                if 0 <= t_idx_int < self.num_slots:
                    self.grid[t_idx_int][d_idx] = {
                        'id': internal_event_id,
                        'frac_start': t_idx_float, 
                    }
        return internal_event_id
    
    def extend_event(self, internal_event_id, list_of_time_cells):
        if internal_event_id not in self.events:
            raise ValueError(f"Event ID {internal_event_id} does not exist.")
        for day, time in list_of_time_cells:
            d_idx = self._get_day_index(day)
            t_idx_float = self._get_time_index(time)

            if d_idx is not None and t_idx_float is not None:
                t_idx_int = int(math.floor(t_idx_float))
                
                if 0 <= t_idx_int < self.num_slots:
                    self.grid[t_idx_int][d_idx] = {
                        'id': internal_event_id,
                        'frac_start': t_idx_float, 
                    }

    def _sanitize(self, text):
        if not text: return ""
        chars = {
            "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
            "_": r"\_", "{": r"\{", "}": r"\}",
        }
        for char, escaped in chars.items():
            text = text.replace(char, escaped)
        return text

    def _create_render_grid(self):
        """
        Generates an Intermediate Representation (IR) for rendering.
        Only populates basic info; borders are calculated in the render loop.
        """
        rows = self.num_slots
        cols = self.num_days
        render_grid = [[{} for _ in range(cols)] for _ in range(rows)]
        
        # --- PASS 1: Populate Data ---
        for r in range(rows):
            for c in range(cols):
                cell_data = self.grid[r][c]
                if cell_data is not None:
                    event_data = self.events.get(cell_data['id'])
                    cell_data = {
                        **cell_data,
                        **event_data,
                    }
                render_grid[r][c] = {
                    'id': cell_data['id'] if cell_data else None,
                    'bg_color': cell_data['color'] if cell_data else None,
                    'text': None,
                    'frac_start': cell_data['frac_start'] if cell_data else None,
                    'open_ended': cell_data['open_ended'] if cell_data else False,
                    'span': 1
                }

        # --- PASS 2: Text Placement ---
        processed_ids = set()
        for r in range(rows):
            for c in range(cols):
                cell_data = self.grid[r][c]
                if not cell_data: continue
                eid = cell_data['id']
                if eid in processed_ids: continue
                
                event_data = self.events.get(eid)  
                cell_data = {
                    **cell_data,
                    **event_data,
                }
                event_cells = []
                for rr in range(rows):
                    for cc in range(cols):
                        if render_grid[rr][cc]['id'] == eid:
                            event_cells.append((rr, cc))
                
                if not event_cells: continue
                
                all_cols = [x[1] for x in event_cells]
                min_col = min(all_cols)
                max_col = max(all_cols)
                
                center_col_float = (min_col + max_col) / 2.0
                center_col = int(center_col_float)
                x_offset_cols = center_col_float - center_col
                
                center_col_cells = [x for x in event_cells if x[1] == center_col]
                
                if not center_col_cells:
                    visual_start_row = min(x[0] for x in event_cells)
                    top_row_cols = [x[1] for x in event_cells if x[0] == visual_start_row]
                    center_col = min(top_row_cols) + (max(top_row_cols) - min(top_row_cols)) // 2
                    visual_start_row = min(x[0] for x in event_cells)
                else:
                    visual_start_row = min(x[0] for x in center_col_cells)

                bottom_row = visual_start_row
                for i in range(visual_start_row, rows):
                    if render_grid[i][center_col]['id'] == eid:
                        bottom_row = i
                    else:
                        break
                
                span = bottom_row - visual_start_row + 1
                final_span = span if span == 1 else -span
                frac_start_val = self.grid[visual_start_row][center_col]['frac_start']

                render_grid[bottom_row][center_col]['text'] = {
                    'title': self._sanitize(cell_data['title']),
                    'subtext': self._sanitize(cell_data['subtext']),
                    'subtext_size': cell_data.get('subtext_size', 'normalsize'),
                    'frac_start': frac_start_val,
                    'x_offset_cols': x_offset_cols
                }
                render_grid[bottom_row][center_col]['span'] = final_span
                
                processed_ids.add(eid)
                
        return render_grid

    def generate_latex_legacygrid(self, scale=0.4, width_pct=1.0, height_pct=1.2, multirow_correction_factor=3.5, text_vpos_bias=-0.0):
        USABLE_WIDTH_CM = 26.7
        USABLE_HEIGHT_CM = 18.0
        
        target_width = USABLE_WIDTH_CM * width_pct
        target_height = USABLE_HEIGHT_CM * height_pct
        
        time_col_width = 1.5
        remaining_width = target_width - time_col_width
        col_width = remaining_width / self.num_days
        
        header_height = 0.8
        remaining_height = target_height - header_height
        if remaining_height < 1: remaining_height = 1
        row_height_cm = remaining_height / self.num_slots

        render_grid = self._create_render_grid()
        
        # --- Calculate Borders Locally for Legacy Grid ---
        rows = self.num_slots
        cols = self.num_days
        for r in range(rows):
            for c in range(cols):
                cell = render_grid[r][c]
                curr_id = cell['id']
                
                # Left Border
                if c == 0: cell['border_l'] = 'THICK'
                elif curr_id != render_grid[r][c-1]['id']: cell['border_l'] = 'THICK'
                else: cell['border_l'] = 'THIN'

                # Right Border
                if c == cols - 1: cell['border_r'] = 'THICK'
                elif curr_id != render_grid[r][c+1]['id']: cell['border_r'] = 'THICK'
                else: cell['border_r'] = 'THIN'

                # Bottom Border
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
        
        for name, spec in self.colors.items():
            latex.append(f"\\definecolor{{{name}}}{spec}")
            
        latex.append(r"""
\begin{document}
\pagestyle{empty}
{\Huge \textbf{""" + self._sanitize(self.title) + r"""}}
\vspace{0.23cm}
""")
        
        for ev in self.special_events:
            latex.append(rf"\begin{{tcolorbox}}[colback={ev['color']}!30!white, colframe=black, boxrule=1.25pt, title=\textbf{{{self._sanitize(ev['date'])}}}]")
            latex.append(rf"\textbf{{{self._sanitize(ev['time'])}}} -- {self._sanitize(ev['title'])} \subtxt{{{self._sanitize(ev['subtext'])}}}")
            latex.append(r"\end{tcolorbox}")
            latex.append(r"\vspace{0.13cm}")

        # --- Border Definitions ---
        V_THICK = r"!{\color{black}\vrule width 1.5pt}" 
        V_THIN = r"!{\color{lightgray!60}\vrule width 0.8pt}" 
        H_THICK = r">{\arrayrulecolor{black}\setlength\arrayrulewidth{1.5pt}}-"
        H_THIN = r">{\arrayrulecolor{lightgray!60}}-" 
        H_INTER = r">{\arrayrulecolor{black}\setlength\arrayrulewidth{1.5pt}}|"

        base_col_def = f"c" + (f"m{{{col_width:.2f}cm}}" * self.num_days)

        latex.append(r"\noindent\makebox[\textwidth][c]{%")
        
        if scale != 1.0: latex.append(rf"\scalebox{{{scale}}}{{%")
        
        latex.append(r"\setlength\arrayrulewidth{0.4pt}")
        
        latex.append(r"\renewcommand{\arraystretch}{1.1}") 
        latex.append(f"\\begin{{tabular}}{{{base_col_def}}}")
        
        # Top Border
        top_hhline = [H_INTER, H_THICK, H_INTER] 
        for _ in range(self.num_days):
            top_hhline.extend([H_THICK, H_INTER])
        latex.append(r"\hhline{" + "".join(top_hhline) + "}")
        
        # Header
        header_row = f"\\multicolumn{{1}}{{{V_THICK}c{V_THICK}}}{{\\textbf{{Time}}}}"
        current_date = self.start_date
        for i in range(self.num_days):
            day_str = current_date.strftime("%a, %d.%m")
            style = f"{V_THICK}c"
            if i == self.num_days - 1: style += V_THICK
            header_row += f" & \\multicolumn{{1}}{{{style}}}{{\\textbf{{{day_str}}}}}"
            current_date += datetime.timedelta(days=1)
        latex.append(header_row + r" \\")
        latex.append(r"\hhline{" + "".join(top_hhline) + "}")
        
        # Rows
        t_current = datetime.datetime.combine(datetime.date.today(), self.start_time)
        
        for r in range(self.num_slots):
            time_str = t_current.strftime("%H:%M")
            
            row_str = f"\\multicolumn{{1}}{{{V_THICK}c{V_THICK}}}{{\\parbox[t][{row_height_cm:.3f}cm][t]{{1.4cm}}{{\\centering \\small {time_str}}}}}"
            
            for c in range(self.num_days):
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
            
            # HHLines
            h_parts = [H_INTER]
            if r == self.num_slots - 1: h_parts.append(H_THICK)
            else: h_parts.append(H_THIN)
            h_parts.append(H_INTER)
            
            for c in range(self.num_days):
                cell = render_grid[r][c]
                if cell['border_b'] == 'THICK': h_parts.append(H_THICK)
                else: h_parts.append(H_THIN)
                h_parts.append(H_INTER)
                
            latex.append(r"\hhline{" + "".join(h_parts) + "}")
            t_current += self.granularity

        latex.append(r"\end{tabular}")
        if scale != 1.0: latex.append(r"}")
        
        # Close the makebox
        latex.append(r"}")
        
        latex.append(r"\end{document}")
        
        return "\n".join(latex)

    def generate_latex_tikz(self, scale=0.46, width_pct=2.2, height_pct=1.4, stripe_interval=2, gap_x_pct=0.03, gap_y_pct=0.0, ext_y_pct=0.15):
        USABLE_WIDTH_CM = 26.7
        USABLE_HEIGHT_CM = 18.0
        
        total_width = USABLE_WIDTH_CM * width_pct
        total_height = USABLE_HEIGHT_CM * height_pct
        
        time_col_width = 1.5
        day_col_width = (total_width - time_col_width) / self.num_days
        
        header_height = 0.8
        grid_height = total_height - header_height
        slot_height = grid_height / self.num_slots
        
        # Gap Definitions
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

% TikZ Styles
\tikzset{
    eventbox/.style={line width=0.8pt}, % Style for border
    gridline/.style={draw=gray!80, line width=1.0pt},
    timeline/.style={draw=black, line width=1.5pt},
    stripe/.style={fill=gray!15} 
}
""")
        
        for name, spec in self.colors.items():
            latex.append(f"\\definecolor{{{name}}}{spec}")
            
        latex.append(r"""
\begin{document}
\pagestyle{empty}
{\Huge \textbf{""" + self._sanitize(self.title) + r"""}}
\vspace{0.23cm}
""")
        
        for ev in self.special_events:
            latex.append(rf"\begin{{tcolorbox}}[colback={ev['color']}!30!white, colframe=black, boxrule=1.25pt, title=\textbf{{{self._sanitize(ev['date'])}}}]")
            latex.append(rf"\textbf{{{self._sanitize(ev['time'])}}} -- {self._sanitize(ev['title'])} \subtxt{{{self._sanitize(ev['subtext'])}}}")
            latex.append(r"\end{tcolorbox}")
            latex.append(r"\vspace{0.13cm}")

        latex.append(r"\noindent\makebox[\textwidth][c]{%")
        if scale != 1.0: latex.append(rf"\scalebox{{{scale}}}{{%")
        latex.append(r"\begin{tikzpicture}[x=1cm, y=-1cm]") 
        
        # --- 0. STRIPED BACKGROUND ---
        grid_start_x = 0 
        grid_end_x = time_col_width + self.num_days * day_col_width

        for r in range(0, self.num_slots, 2 * stripe_interval):
            stripe_start_row = r + stripe_interval
            stripe_end_row = min(r + 2 * stripe_interval, self.num_slots)

            if stripe_start_row < self.num_slots:
                y_top = stripe_start_row * slot_height
                y_bottom = stripe_end_row * slot_height
                latex.append(rf"\fill[stripe] ({grid_start_x}, {y_top}) rectangle ({grid_end_x}, {y_bottom});")

        # --- 1. HEADERS ---
        latex.append(rf"\draw[timeline, fill=white] (0, {-header_height}) rectangle ({time_col_width}, 0);")
        latex.append(rf"\node[anchor=center] at ({time_col_width/2}, {-header_height/2}) {{\textbf{{Time}}}};")
        
        current_date = self.start_date
        for i in range(self.num_days):
            x_start = time_col_width + i * day_col_width
            x_end = x_start + day_col_width
            day_str = current_date.strftime("%a, %d.%m")
            latex.append(rf"\draw[timeline, fill=white] ({x_start}, {-header_height}) rectangle ({x_end}, 0);")
            latex.append(rf"\node[anchor=center] at ({x_start + day_col_width/2}, {-header_height/2}) {{\textbf{{{day_str}}}}};")
            current_date += datetime.timedelta(days=1)

        # --- 2. GRID LINES ---
        for c in range(self.num_days + 1):
            x = time_col_width + c * day_col_width
            latex.append(rf"\draw[gridline] ({x}, 0) -- ({x}, {grid_height});")
        
        for r in range(self.num_slots + 1):
            y = r * slot_height
            latex.append(rf"\draw[gridline] ({time_col_width}, {y}) -- ({time_col_width + self.num_days * day_col_width}, {y});")

        # --- 3. EVENTS (Explicit Bridges with Patching) ---
        
        for c in range(self.num_days):
            r = 0
            while r < self.num_slots:
                cell = render_grid[r][c]
                
                if cell['id'] is not None:
                    start_r = r
                    current_id = cell['id']
                    is_open_ended = cell['open_ended']
                    
                    # --- CHECK NEIGHBORS AT START ---
                    has_bridge_right = False
                    if c < self.num_days - 1:
                        if render_grid[start_r][c+1]['id'] == current_id:
                            has_bridge_right = True

                    has_bridge_left = False
                    if c > 0:
                        if render_grid[start_r][c-1]['id'] == current_id:
                            has_bridge_left = True
                    
                    # --- FIND END OF STRIP ---
                    end_r = r + 1
                    while end_r < self.num_slots:
                        next_cell = render_grid[end_r][c]
                        if next_cell['id'] != current_id:
                            break
                        
                        # Consistency Check Right
                        next_has_bridge_right = False
                        if c < self.num_days - 1 and render_grid[end_r][c+1]['id'] == current_id:
                            next_has_bridge_right = True
                            
                        # Consistency Check Left
                        next_has_bridge_left = False
                        if c > 0 and render_grid[end_r][c-1]['id'] == current_id:
                            next_has_bridge_left = True
                        
                        if next_has_bridge_right != has_bridge_right or next_has_bridge_left != has_bridge_left:
                            break
                            
                        end_r += 1
                    
                    # Helper to check Top boundary
                    def is_true_top(check_r, check_c):
                        # Fix: checking < 0 for start of grid
                        if check_r < 0: return True 
                        if render_grid[check_r][check_c]['id'] != current_id: return True
                        return False

                    # Helper to check Bottom boundary
                    def is_true_bottom(check_r, check_c):
                        if check_r >= self.num_slots: return True
                        if render_grid[check_r][check_c]['id'] != current_id: return True
                        return False

                    # Check Top Status
                    main_is_top = is_true_top(start_r - 1, c)
                    right_is_top = False
                    if c < self.num_days - 1:
                        right_is_top = is_true_top(start_r - 1, c+1)
                    
                    # Check Bottom Status
                    main_is_bottom = is_true_bottom(end_r, c)
                    
                    right_is_bottom = False
                    if c < self.num_days - 1:
                        right_is_bottom = is_true_bottom(end_r, c+1)
                        
                    left_is_bottom = False
                    if c > 0:
                        left_is_bottom = is_true_bottom(end_r, c-1)
                        
                    # --- GEOMETRY ---
                    frac_start_top = render_grid[start_r][c]['frac_start']
                    y_top = frac_start_top * slot_height
                    base_y_bottom = end_r * slot_height
                    
                    x_left = time_col_width + c * day_col_width
                    x_right = x_left + day_col_width
                    
                    # Borders for Main Block
                    draw_border_l = not has_bridge_left
                    draw_border_r = not has_bridge_right
                        
                    # Top Border (Visual Top check)
                    draw_border_t = main_is_top
                    
                    # --- CALCULATE Y2 FOR MAIN BLOCK ---
                    if main_is_bottom:
                        if is_open_ended:
                            main_y2 = base_y_bottom + ext_y_bottom
                        else:
                            main_y2 = base_y_bottom - gap_y_bottom
                    else:
                        # Internal vertical split: No gap (Flush)
                        main_y2 = base_y_bottom
                    
                    # --- 1. DRAW MAIN BLOCK ---
                    main_x2 = x_right - gap_x_right
                    
                    latex.append(rf"\fill[{cell['bg_color']}] ({x_left}, {y_top}) rectangle ({main_x2}, {main_y2});")
                    
                    if draw_border_t:
                        latex.append(rf"\draw[eventbox] ({x_left}, {y_top}) -- ({main_x2}, {y_top});")
                    
                    if main_is_bottom and not is_open_ended:
                         latex.append(rf"\draw[eventbox] ({x_left}, {main_y2}) -- ({main_x2}, {main_y2});")
                         
                    if draw_border_l:
                        latex.append(rf"\draw[eventbox] ({x_left}, {y_top}) -- ({x_left}, {main_y2});")
                        
                    if draw_border_r:
                        latex.append(rf"\draw[eventbox] ({main_x2}, {y_top}) -- ({main_x2}, {main_y2});")

                    # --- 2. DRAW EXPLICIT BRIDGE (RIGHT) ---
                    if has_bridge_right:
                        bridge_x1 = main_x2
                        bridge_x2 = x_right 
                        
                        # Bridge Top/Bottom Logic: "If either one is, the bridge block also is"
                        bridge_is_top = main_is_top or right_is_top
                        bridge_is_bottom = main_is_bottom or right_is_bottom
                        
                        if bridge_is_bottom:
                            if is_open_ended:
                                bridge_y2 = base_y_bottom + ext_y_bottom
                            else:
                                bridge_y2 = base_y_bottom - gap_y_bottom
                        else:
                            bridge_y2 = base_y_bottom
                        
                        latex.append(rf"\fill[{cell['bg_color']}] ({bridge_x1}, {y_top}) rectangle ({bridge_x2}, {bridge_y2});")
                        
                        # Draw Top Border if it's a top piece
                        if bridge_is_top:
                            latex.append(rf"\draw[eventbox] ({bridge_x1}, {y_top}) -- ({bridge_x2}, {y_top});")
                        
                        # Draw Bottom Border if it's a bottom piece (unless open ended)
                        if bridge_is_bottom and not is_open_ended:
                            latex.append(rf"\draw[eventbox] ({bridge_x1}, {bridge_y2}) -- ({bridge_x2}, {bridge_y2});")
                        
                        # ** PATCH RIGHT **: Fix vertical gap if Main Block height != Bridge height
                        # We draw a vertical line on the shared edge (main_x2)
                        if abs(main_y2 - bridge_y2) > 0.001:
                            patch_ymin = min(main_y2, bridge_y2)
                            patch_ymax = max(main_y2, bridge_y2)
                            latex.append(rf"\draw[eventbox] ({main_x2}, {patch_ymin}) -- ({main_x2}, {patch_ymax});")

                    # --- 3. PATCH LEFT ---
                    if has_bridge_left:
                        # Left Bridge Logic: "If either one (Main c or Left c-1) is bottom..."
                        left_bridge_is_bottom = main_is_bottom or left_is_bottom
                        
                        if left_bridge_is_bottom:
                            if is_open_ended:
                                left_bridge_y2 = base_y_bottom + ext_y_bottom
                            else:
                                left_bridge_y2 = base_y_bottom - gap_y_bottom
                        else:
                            left_bridge_y2 = base_y_bottom
                            
                        # If Main Block height != Left Bridge height, draw patch on x_left
                        if abs(main_y2 - left_bridge_y2) > 0.001:
                            patch_ymin = min(main_y2, left_bridge_y2)
                            patch_ymax = max(main_y2, left_bridge_y2)
                            latex.append(rf"\draw[eventbox] ({x_left}, {patch_ymin}) -- ({x_left}, {patch_ymax});")
                            
                    r = end_r
                else:
                    r += 1

        # --- 4. TIME LABELS & TIME AXIS ---
        latex.append(rf"\draw[timeline] ({time_col_width}, 0) -- ({time_col_width}, {grid_height});")
        latex.append(rf"\draw[timeline] (0, 0) -- (0, {grid_height});")
        
        t_current = datetime.datetime.combine(datetime.date.today(), self.start_time)
        for r in range(self.num_slots):
            y_top = r * slot_height
            time_str = t_current.strftime("%H:%M")
            
            y_line = (r+1) * slot_height
            latex.append(rf"\draw[timeline] (0, {y_line}) -- ({time_col_width}, {y_line});")

            latex.append(rf"\node[anchor=north, font=\small] at ({time_col_width/2}, {y_top}) {{{time_str}}};")
            t_current += self.granularity

        # --- 5. CONTENT / TEXT ---
        for r in range(self.num_slots):
            for c in range(self.num_days):
                cell = render_grid[r][c]
                if cell['text']:
                    frac_start = cell['text']['frac_start']
                    span = cell['span']
                    num_rows = abs(span)
                    
                    y_top = frac_start * slot_height
                    base_y_bottom = (frac_start + num_rows) * slot_height
                    
                    is_open_ended = cell['open_ended']
                    
                    if is_open_ended:
                        y_actual_bottom = base_y_bottom + ext_y_bottom
                    else:
                        y_actual_bottom = base_y_bottom - gap_y_bottom
                        
                    y_center = (y_top + y_actual_bottom) / 2
                    
                    x_left = time_col_width + c * day_col_width
                    x_center = x_left + day_col_width / 2
                    
                    offset_cols = cell['text'].get('x_offset_cols', 0.0)
                    x_center += offset_cols * day_col_width
                    x_center -= gap_x_right / 2
                    
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

