from agenda_builder import *


# --- Hardcoded Example Agenda (Used as Default) ---

def add_example_colors(agenda):
    """Defines the colors used in the hardcoded example agenda."""
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

def create_example_agenda(agenda):
    """Generates the hardcoded example agenda events."""
    add_example_colors(agenda)

    d_mon = "20251201"
    d_tue = "20251202"
    d_wed = "20251203"
    d_thu = "20251204"
    d_fri = "20251205"

    # 3. Special Events
    agenda.add_special_event("Saturday, November 29, 2025", "19:00", "Welcome Dinner", 
                              "Historic City Center Restaurant", "cSpec")

    # 4. Monday
    # Single time range (day, start, end)
    agenda.add_event("cArr", "Registration", time_ranges=(d_mon, "09:00", "09:30")) 

    agenda.add_event("cWelc", "Opening Ceremony", 
                      "Chair: Ada Lovelace\\\\ Keynote: Alan Turing -- ``On Computable Numbers''",
                      time_ranges=(d_mon, "09:30", "10:30"),
                      subtext_size="small")

    agenda.add_event("cWork", "Workshop: Compiler Optimization", 
                      "Grace Hopper, John von Neumann",
                      time_ranges=(d_mon, "10:45", "12:30"))
    
    # Multiple time ranges, now just a list of (day, start, end) tuples
    agenda.add_event("cWork", "Workshop: Complexity Theory", 
                      "Stephen Cook, Richard Karp",
                      time_ranges=[(d_mon, "13:30", "15:30")]) 

    # 5. Tuesday
    agenda.add_event("cArr", "Morning Coffee", time_ranges=(d_tue, "09:00", "09:30"))
    agenda.add_event("cLect", "Session I: Algorithms", 
                      "Donald Knuth: The Art of Programming\\\\ Edsger Dijkstra: Shortest Paths",
                      time_ranges=[(d_tue, "09:30", "11:00")])
    agenda.add_event("cWork", "Poster Session I", 
                      "Topics: Algorithms & Data Structures",
                      time_ranges=[(d_tue, "11:15", "12:45")])
    agenda.add_event("cWork", "Group Work: Operating Systems", 
                      "Ken Thompson, Dennis Ritchie",
                      time_ranges=[(d_tue, "13:45", "15:30")])

    # 6. Wednesday
    agenda.add_event("cArr", "Morning Coffee", time_ranges=(d_wed, "09:00", "09:30"))
    agenda.add_event("cLect", "Session II: Information Theory", 
                      "Claude Shannon: A Mathematical Theory\\\\ Richard Hamming: Error Correcting Codes",
                      time_ranges=[(d_wed, "09:30", "11:00")])
    agenda.add_event("cWork", "Poster Session II", 
                      "Topics: Networking & Security",
                      time_ranges=[(d_wed, "11:15", "12:45")])

    agenda.add_event("cPrep", "Hackathon Preparation", 
                      "Margaret Hamilton, Katherine Johnson",
                      time_ranges=[(d_wed, "13:45", "15:30")])

    # 7. Thursday
    agenda.add_event("cArr", "Morning Coffee", time_ranges=(d_thu, "09:00", "09:30"))
    agenda.add_event("cVisit", "Excursion: Tech Museum", 
                      "Guided tour by Tim Berners-Lee",
                      time_ranges=[(d_thu, "09:30", "11:30")])

    agenda.add_event("cArr", "Surprise Challenge", "",
                      time_ranges=[(d_thu, "13:15", None)])

    agenda.add_event("cPres", "Hackathon Presentations", 
                      "Jury: Linus Torvalds, Guido van Rossum",
                      time_ranges=[(d_thu, "13:30", "15:30")])

    # MERGED LUNCH (Mon - Fri)
    # This list is now ONLY composed of (day, start, end) tuples.
    lunch_times = [
        (d_mon, "12:30", "13:30"),
        (d_tue, "12:45", "13:45"),
        (d_wed, "12:45", "13:45"),
        (d_thu, "12:00", "13:00"), 
        (d_fri, "11:30", "12:30")
    ]

    agenda.add_event("cLunch", "Lunch Break", "Cafeteria", time_ranges=lunch_times)

    # 8. Friday
    agenda.add_event("cArr", "Morning Coffee", time_ranges=[(d_fri, "09:30", "10:00")])
    agenda.add_event("cVisit", "Lab Tour: AI & Robotics", 
                      "Marvin Minsky, John McCarthy",
                      time_ranges=[(d_fri, "10:00", "11:30")])
    agenda.add_event("cBye", "Farewell & Awards", "Closing Remarks",
                      time_ranges=[(d_fri, "12:30", "13:30")])

    # 9. Leisure (Open Ended)
    leisure_event = agenda.add_event("cLeis", "Networking & Social", open_ended=True)
    
    # Each extend_event call now passes the specific (day, start, end) tuple directly.
    agenda.extend_event(leisure_event, time_ranges=(d_mon, "15:30", "16:00"))
    agenda.extend_event(leisure_event, time_ranges=[(d_tue, "15:30", "16:00")])
    agenda.extend_event(leisure_event, time_ranges=[(d_wed, "15:30", "16:00"), (d_thu, "15:30", "16:00"), (d_fri, "13:30", "16:00")])