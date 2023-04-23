import requests
import json
import re
from fake_headers import Headers

from bs4 import BeautifulSoup
from pprint import pprint
import datetime
import locale
from json import JSONEncoder

RU_MONTH_VALUES = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}


def get_headers():
    return Headers(browser="Firefox", os="win").generate()


hh_main_html = requests.get(
    "https://spb.hh.ru/search/vacancy?area=1&area=2&search_field=name&search_field=company_name&search_field=description&enable_snippets=false&text=Python+django+flask",
    headers=get_headers(),
).text

hh_main_soup = BeautifulSoup(hh_main_html, "lxml")

tag_div = hh_main_soup.find("div", id="a11y-main-content")
tag_div_vacancies = tag_div.find_all("div", class_="vacancy-serp-item-body")

parsed_data = []

# получение ссылки
for tag_div_vacancy in tag_div_vacancies:
    result = {}
    h3_tag = tag_div_vacancy.find("h3")
    a_tag = h3_tag.find("a")
    link = a_tag["href"]

    result["job"] = a_tag.text
    result["link"] = link

    # поиск зарплаты
    zp_span = tag_div_vacancy.find("span", class_="bloko-header-section-3")

    if zp_span:
        zp_text = zp_span.text.split("–")
        # анализ строки зарплаты
        # и поиск слов 'от' или 'до'
        if "до" in zp_text[0]:
            result["zp_high"] = "".join(re.findall(r"(\d)\s?", zp_text[0]))
        else:
            result["zp_low"] = "".join(re.findall(r"(\d)\s?", zp_text[0]))
        # верхняя граница (до), если есть
        if len(zp_text) > 1:
            result["zp_high"] = "".join(re.findall(r"(\d)\s?", zp_text[1])) or ""
        # валюта
        result["zp_cur"] = zp_span.text.split(" ")[-1]

    # поиск компании и города
    company = tag_div_vacancy.find("div", class_="vacancy-serp-item__info")
    company_div = company.find_all("div", class_="bloko-text")
    # это название фирмы
    company_name = company_div[0]
    company_div_a = company_name.find("a")
    result["company"] = company_div_a.text.split(",")[0]
    # а это название города
    company_city = company_div[1]
    result["city"] = company_city.text.split(",")[0]

    # анализ содержимого вакансии
    # на наличие слов Django и Flusk
    # и даты публикации
    vacancy_info = requests.get(link, headers=get_headers()).text
    vacancy_info_soup = BeautifulSoup(vacancy_info, "lxml")
    # поиск даты регистрации объявления
    vacancy_date = vacancy_info_soup.find(
        "p", class_="vacancy-creation-time-redesigned"
    )
    if vacancy_date:
        vacancy_date_span = vacancy_date.find("span") or ""
    if vacancy_date_span:
        # в дате меняем месяц на число (русское название месяца не воспринимается системой)
        ru_date_short = vacancy_date_span.text.split("\xa0")
        ru_date_short[1] = RU_MONTH_VALUES[ru_date_short[1]]
        result["date"] = datetime.datetime.strptime(" ".join(ru_date_short), "%d %m %Y")

    # поиск блоков DIV-ов с классом "bloko-columns-row"
    vacancy_info_div = vacancy_info_soup.find(
        "div", {"data-qa": "vacancy-description"}, class_="g-user-content"
    )
    if vacancy_info_div:
        vacancy_info_text = vacancy_info_div.text
        # ищем в содержимом слова DJANGO и FLASK
    if "Django" in vacancy_info_text or "Flusk" in vacancy_info_text:
        # нашли слова - добавляем результат в parsed_data
        parsed_data.append(result)
        print(result)
        # pprint(result)


# обработчик типа данных DATE и DATETIME
# чтобы в JSON-файл добавилась строка типа "YYYY-MM-DD"
class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return datetime.datetime.strftime(obj, "%Y-%m-%d")


# запись в JSON-файл
new_json = json.dumps(
    parsed_data, indent=2, ensure_ascii=False, cls=DateTimeEncoder
).encode("utf8")
with open("hh_python.json", "w", encoding="utf-8") as hh_json:
    json.dump(parsed_data, hh_json, indent=3, ensure_ascii=False, cls=DateTimeEncoder)