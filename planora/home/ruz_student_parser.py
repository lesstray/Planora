import requests
from bs4 import BeautifulSoup
import re, json
from datetime import datetime, timedelta


def get_group_id(group_number: str) -> str:
    """
    Ищет ID группы на RUZ по её номеру, сравнивая текст ссылки
    внутри <ul class="groups-list">.
    """
    link = 'https://ruz.spbstu.ru/search/groups?q=' + group_number
    r = requests.get(link)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'lxml')

    # На странице поиска групп есть <ul class="groups-list">
    ul = soup.find('ul', class_='groups-list')
    if not ul:
        return ''

    # Ищем именно ту ссылку, где текст == group_number
    for a in ul.find_all('a', class_='groups-list__link'):
        if a.text.strip() == group_number:
            href = a.get('href', '')
            # href вида "/faculty/125/groups/40565"
            parts = href.rstrip('/').split('/')
            return parts[-1] if parts else ''

    return ''


def fetch_group_week_data(group_id: str, date: datetime) -> list:
    """
    Забирает расписание группы за неделю, как JSON из __INITIAL_STATE__.
    """
    url = f'https://ruz.spbstu.ru/faculty/125/groups/{group_id}?date={date.year}-{date.month}-{date.day}'
    r = requests.get(url)
    r.raise_for_status()
    m = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});\s*</script>', r.text, flags=re.S)
    if not m:
        return []
    state = json.loads(m.group(1))
    return state["lessons"]["data"].get(str(group_id), [])


def collect_student_month_schedule(group_number: str, start_date: str, weeks: int = 4):
    """
    Собирает расписание группы на несколько недель,
    возвращает два списка:
      - subjects — названия предметов
      - teachers — ФИО преподавателей
    """
    group_id = get_group_id(group_number)
    if not group_id:
        print(f"Группа {group_number} не найдена")
        return [], []

    # Выравниваем дату на начало недели (понедельник)
    dt = datetime.fromisoformat(start_date)
    dt -= timedelta(days=dt.weekday())

    subjects = []
    teachers = []

    for i in range(weeks):
        week_date = dt + timedelta(weeks=i)
        week_data = fetch_group_week_data(group_id, week_date)
        for day in week_data:
            for lesson in day.get('lessons', []):
                # название предмета
                subj = lesson.get('subject')
                if subj:
                    subjects.append(subj)
                # список преподавателей для этого занятия
                for t in lesson.get('teachers') or []:
                    fio = t.get('full_name')
                    if fio:
                        teachers.append(fio)

    # Убираем дубликаты
    return list(set(subjects)), list(set(teachers))


# if __name__ == "__main__":
#     subs, profs = collect_student_month_schedule("5151004/10101", "2025-03-15", weeks=4)
#     print("Предметы:", subs)
#     print("Преподаватели:", profs)
