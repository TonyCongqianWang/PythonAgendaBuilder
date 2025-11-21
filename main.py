from agenda_builder import *
import argparse


parser = argparse.ArgumentParser(
    description="A example main file to showcase agenda builder."
)
parser.add_argument(
    '--file',
    type=str,
    default=None,
    help='If set, outputs the LaTeX code to the specified file instead of stdout.'
)
parser.add_argument(
    '--legacy',
    action='store_true',
    help='If set, enables the legacy rendering mode.'
)

args = parser.parse_args()
use_legacy_render = args.legacy    

# 1. Setup
agenda = AgendaBuilder(
    start_date_str="20251201", end_date_str="20251205", 
    start_time="09:00", end_time="16:00", granularity_minutes=15
)
agenda.set_title("My Winter School 2025")

# 2. Colors 
agenda.define_color("cArr", 0.9, 0.96, 0.9)
agenda.define_color("cWelc", 0.7, 0.9, 0.7)
agenda.define_color("cBye", 0.6, 0.8, 0.6)
agenda.define_color("cLect", 0.75, 0.95, 0.95) 
agenda.define_color("cWork", 1.0, 0.95, 0.8)
agenda.define_color("cPrep", 1.0, 0.85, 0.65)
agenda.define_color("cPres", 1.0, 0.7, 0.7)
agenda.define_color("cLunch", 0.85, 0.9, 0.95)
agenda.define_color("cLeis", 0.75, 0.85, 1.0)
agenda.define_color("cVisit", 0.9, 0.85, 1.0)
agenda.define_color("cSpec", 1.0, 0.8, 0.8)

base = agenda.start_date
d_mon = base
d_tue = base + datetime.timedelta(days=1)
d_wed = base + datetime.timedelta(days=2)
d_thu = base + datetime.timedelta(days=3)
d_fri = base + datetime.timedelta(days=4)

# 3. Special Events
agenda.add_special_event("Saturday, November 29, 2025", "19:00", "Welcome Dinner", 
                            "Historic City Center Restaurant", "cSpec")

# 4. Monday
agenda.add_event([(d_mon, t) for t in time_range("09:00", "09:30")], "cArr", "Registration")

agenda.add_event([(d_mon, t) for t in time_range("09:30", "10:30")], "cWelc", "Opening Ceremony", 
                    "Chair: Ada Lovelace\\\\ Keynote: Alan Turing -- ``On Computable Numbers\"", 
                    subtext_size="small")

agenda.add_event([(d_mon, t) for t in time_range("10:45", "12:30")], "cWork", "Workshop: Compiler Optimization", 
                    "Grace Hopper, John von Neumann")
agenda.add_event([(d_mon, t) for t in time_range("13:30", "15:30")], "cWork", "Workshop: Complexity Theory", 
                    "Stephen Cook, Richard Karp")

# 5. Tuesday
agenda.add_event([(d_tue, t) for t in time_range("09:00", "09:30")], "cArr", "Morning Coffee")
agenda.add_event([(d_tue, t) for t in time_range("09:30", "11:00")], "cLect", "Session I: Algorithms", 
                    "Donald Knuth: The Art of Programming\\\\ Edsger Dijkstra: Shortest Paths")
agenda.add_event([(d_tue, t) for t in time_range("11:15", "12:45")], "cWork", "Poster Session I", 
                    "Topics: Algorithms & Data Structures")
agenda.add_event([(d_tue, t) for t in time_range("13:45", "15:30")], "cWork", "Group Work: Operating Systems", 
                    "Ken Thompson, Dennis Ritchie")

# 6. Wednesday
agenda.add_event([(d_wed, t) for t in time_range("09:00", "09:30")], "cArr", "Morning Coffee")
agenda.add_event([(d_wed, t) for t in time_range("09:30", "11:00")], "cLect", "Session II: Information Theory", 
                    "Claude Shannon: A Mathematical Theory\\\\ Richard Hamming: Error Correcting Codes")
agenda.add_event([(d_wed, t) for t in time_range("11:15", "12:45")], "cWork", "Poster Session II", 
                    "Topics: Networking & Security")

agenda.add_event([(d_wed, t) for t in time_range("13:45", "15:30")], "cPrep", "Hackathon Preparation", 
                    "Margaret Hamilton, Katherine Johnson")

# 7. Thursday
agenda.add_event([(d_thu, t) for t in time_range("09:00", "09:30")], "cArr", "Morning Coffee")
agenda.add_event([(d_thu, t) for t in time_range("09:30", "11:30")], "cVisit", "Excursion: Tech Museum", 
                    "Guided tour by Tim Berners-Lee")
agenda.add_event([(d_thu, t) for t in time_range("13:15", "14:30")], "cArr", "Surprise Challenge", 
                    "")
agenda.add_event([(d_thu, t) for t in time_range("13:30", "15:30")], "cPres", "Hackathon Presentations", 
                    "Jury: Linus Torvalds, Guido van Rossum")

# MERGED LUNCH (Mon - Fri)
lunch_times = []
lunch_times.extend([(d_mon, t) for t in time_range("12:30", "13:30")])
lunch_times.extend([(d_tue, t) for t in time_range("12:45", "13:45")])
lunch_times.extend([(d_wed, t) for t in time_range("12:45", "13:45")])
lunch_times.extend([(d_thu, t) for t in time_range("12:00", "13:00")]) 
lunch_times.extend([(d_fri, t) for t in time_range("11:30", "12:30")])

agenda.add_event(lunch_times, "cLunch", "Lunch Break", "Cafeteria")

# 8. Friday
agenda.add_event([(d_fri, t) for t in time_range("09:30", "10:00")], "cArr", "Morning Coffee")
agenda.add_event([(d_fri, t) for t in time_range("10:00", "11:30")], "cVisit", "Lab Tour: AI & Robotics", 
                    "Marvin Minsky, John McCarthy")
agenda.add_event([(d_fri, t) for t in time_range("12:30", "13:30")], "cBye", "Farewell & Awards", "Closing Remarks")

# 9. Leisure (Open Ended)
leisure_event = agenda.add_event([], "cLeis", "Networking & Social", open_ended=True)
agenda.extend_event(leisure_event, [(d_mon, t) for t in time_range("15:30", "16:00")])
agenda.extend_event(leisure_event, [(d_tue, t) for t in time_range("15:30", "16:00")])
agenda.extend_event(leisure_event, [(d_wed, t) for t in time_range("15:30", "16:00")])
agenda.extend_event(leisure_event, [(d_thu, t) for t in time_range("15:30", "16:00")])
agenda.extend_event(leisure_event, [(d_fri, t) for t in time_range("13:30", "16:00")])

if not use_legacy_render:
    latex_code = agenda.generate_latex_tikz(scale=0.48, width_pct=2.2, height_pct=1.4, gap_x_pct=0.05, gap_y_pct=0.0, ext_y_pct=0.3)
else:
    latex_code = agenda.generate_latex_legacygrid(scale=0.48, width_pct=2.2, height_pct=1.4, multirow_correction_factor=3.5)

if args.file:
    with open(args.file, 'w') as f:
        f.write(latex_code)
else:
    print(latex_code)