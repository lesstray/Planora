import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
import locale
import dateparser

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')


def get_teacher_id(teacher_fullname: str) -> str:
    link = 'https://ruz.spbstu.ru/search/teacher?q=' + teacher_fullname
    r = requests.get(link)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml')
    a = soup.find('a', class_='search-result__link')
    href = a and a['href']
    return href.split('/')[-1] if href else ''


def fetch_week_data(teacher_id: str, date: datetime) -> list:
    url = f'https://ruz.spbstu.ru/teachers/{teacher_id}?date={date.year}-{date.month}-{date.day}'
    r = requests.get(url)
    r.raise_for_status()
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*</script>', r.text, flags=re.S)
    if not m:
        return []
    state = json.loads(m.group(1))
    #print(state)
    return state["teacherSchedule"]["data"].get(str(teacher_id), [])


def parse_teacher_schedule(raw_schedule: list) -> dict:
    schedule = {}

    for day in raw_schedule:
        date_str = day['date']
        try:
            date_obj = datetime.fromisoformat(date_str)
            day_key = date_obj.strftime('%Y-%m-%d')
        except ValueError:
            day_key = date_str

        lessons = []
        for lesson in day['lessons']:
            # Извлекаем названия групп
            groups = [group['name'] for group in lesson.get('groups', [])]
            
            # Основная информация о занятии
            subject = lesson.get('subject', '').strip()
            start = lesson.get('time_start')
            end = lesson.get('time_end')
            type_ = lesson.get('lesson_type', '')
            place = lesson.get('auditories', [{}])[0].get('name', '')
            teacher = ', '.join(t['full_name'] for t in lesson.get('teachers', []))

            lessons.append({
                "start_time": start,
                "end_time": end,
                "subject": subject,
                "type": type_,
                "teacher": teacher or None,
                "place": place,
                "groups": groups  # Добавляем список групп
            })

        schedule[day_key] = lessons
    print(schedule)
    return schedule


def get_teacher_schedule(teacher_fullname: str, date: str) -> dict:
    teacher_id = get_teacher_id(teacher_fullname)
    if not teacher_id:
        return {"error": "Преподаватель не найден"}

    dt = datetime.fromisoformat(date)
    dt -= timedelta(days=dt.weekday())  # начало недели (понедельник)
    raw_schedule = fetch_week_data(teacher_id, dt)
    parsed = parse_teacher_schedule(raw_schedule)

    if parsed:
        week_start = min(parsed).strip()
        week_end = max(parsed).strip()
    else:
        week_start = week_end = date

    return {
        "week_start": week_start,
        "week_end": week_end,
        "schedule": parsed
    }

# if __name__ == '__main__':
#     teacher = "Платонов Владимир Владимирович"
#     date = datetime.today().strftime('%Y-%m-%d')
#     result = get_teacher_schedule(teacher, date)
#     print(json.dumps(result, ensure_ascii=False, indent=2))
