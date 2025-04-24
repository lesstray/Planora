import requests
from bs4 import BeautifulSoup
import sys
import json
import re 
from datetime import datetime, timedelta


def check_bad_subjects(place: str) -> bool:
    return any(x in place for x in ("Спорткомплекс", "Не определено", "Военная"))


def get_schedule_link(group_num: str) -> str:
    url = 'http://ruz.spbstu.ru/search/groups'
    r = requests.get(url, params={'q': group_num})
    if r.status_code != 200:
        sys.exit("[-] Could not connect to server")
    soup = BeautifulSoup(r.text, 'lxml')
    li = soup.find('ul').find('li')
    href = li.find('a')['href']
    return 'https://ruz.spbstu.ru' + href


def count_subjects(day_text: str) -> int:
    return day_text.count("Группы")


def parse_schedule(days, names, types, teachers, places, counts) -> dict:
    schedule = {}
    ptr_name = 0
    ptr_lesson = 0
    ptr_teacher = 0
    time_pattern = re.compile(r'^(\d{2}:\d{2})-(\d{2}:\d{2})\s+(.+)$')

    for i, day in enumerate(days):
        day_key = day.text.strip()
        lessons = []
        for _ in range(counts[i]):
            raw = names[ptr_name].text.strip()
            m = time_pattern.match(raw)
            if m:
                start, end, subj = m.groups()
            else:
                start = end = None
                subj = raw

            typ   = types[ptr_lesson].text.strip()
            place = places[ptr_lesson].text.strip()
            if not check_bad_subjects(place):
                teacher = teachers[ptr_teacher].text.strip()
                ptr_teacher += 1
            else:
                teacher = None

            lessons.append({
                "start_time": start,
                "end_time":   end,
                "subject":    subj,
                "type":       typ,
                "teacher":    teacher,
                "place":      place
            })

            ptr_name    += 1
            ptr_lesson  += 1

        schedule[day_key] = lessons

    return schedule


def get_schedule(group: str, date: str) -> dict:
    link = get_schedule_link(group)
    r = requests.get(link, params={'date': date})
    if r.status_code != 200:
        sys.exit("[-] Could not fetch schedule")
    soup = BeautifulSoup(r.text, 'lxml')

    days     = soup.find_all('div', class_='schedule__date')
    names    = soup.find_all('div', class_='lesson__subject')
    types    = soup.find_all('div', class_='lesson__type')
    places   = soup.find_all('div', class_='lesson__places')
    teachers = soup.find_all('div', class_='lesson__teachers')
    sdays    = soup.find_all('li', class_='schedule__day')

    counts = [ count_subjects(li.text) for li in sdays ]
    sch   = parse_schedule(days, names, types, teachers, places, counts)
    #print(sch)
    return {
    "week_start": days[0].text.strip(),
    "week_end":   days[-1].text.strip(),
    "schedule": sch
    }

