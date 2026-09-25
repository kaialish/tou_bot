from bs4 import BeautifulSoup

def parse_schedule_items(html_content: str, day: str = "today") -> list[dict]:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    panel = soup.find('div', attrs={'data-schedule-panel': day})
    if not panel:
        panel = soup.find('div', class_='student-schedule-panel is-active')

    schedule_list = []
    if not panel:
        return schedule_list

    raw_lines = [line.strip() for line in panel.get_text(separator='\n').splitlines() if line.strip()]
    
    i = 0
    while i < len(raw_lines):
        line = raw_lines[i]
        if ":" in line and len(line) <= 13:
            time_str = line
            subject_str = raw_lines[i+1] if i+1 < len(raw_lines) else "Предмет"
            type_str = raw_lines[i+2] if i+2 < len(raw_lines) else ""
            room_str = raw_lines[i+3] if i+3 < len(raw_lines) else ""
            
            if subject_str in ["Сейчас идёт", "Следующая"]:
                subject_str = raw_lines[i+2] if i+2 < len(raw_lines) else "Предмет"
                type_str = raw_lines[i+3] if i+3 < len(raw_lines) else ""
                room_str = raw_lines[i+4] if i+4 < len(raw_lines) else ""
                i += 1
                
            schedule_list.append({
                "time": time_str,
                "subject": subject_str,
                "type": type_str,
                "room": room_str
            })
            i += 4
        else:
            i += 1

    return schedule_list