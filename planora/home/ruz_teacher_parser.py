import requests
from bs4 import BeautifulSoup
import re, json
from datetime import datetime, timedelta


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
    return state["teacherSchedule"]["data"].get(str(teacher_id), [])


def collect_teacher_month_schedule(teacher_fullname: str, start_date: str, weeks: int = 4):
    teacher_id = get_teacher_id(teacher_fullname)
    if not teacher_id:
        print("Преподаватель не найден")
        return [], set()

    #  получаем расписание на месяц вперед, начиная с 15 марта
    dt = datetime.fromisoformat(start_date)  # '2025-03-15'
    dt -= timedelta(days=dt.weekday())

    all_lessons = []
    all_groups = []

    for i in range(weeks):
        week_date = dt + timedelta(weeks=i)
        lessons = fetch_week_data(teacher_id, week_date)
        for ls in lessons:
        	for l in ls['lessons']:
        		for g in l['groups']:
        			all_groups.append(g['name'])
        		all_lessons.append(l['subject'])
    return all_lessons, all_groups


# if __name__ == "__main__":
#     teacher = "Павленко Евгений Юрьевич"
#     lessons, groups = collect_teacher_month_schedule(teacher, "2025-03-15", weeks=5)
#     lessons = list(set(lessons))
#     groups = list(set(groups))
#     print(f"Пары: {lessons}")
#     print(f"Группы: {groups}")
