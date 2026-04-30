from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    category: str
    list_url_template: str
    # list pages: page=1 uses base url; page>=2 uses template formatting
    # detail urls are absolute on site


SOURCES: list[Source] = [
    # Notifications / announcements
    Source(category="notices", list_url_template="https://iee.zjgsu.edu.cn/?Gsgg{page_suffix}"),
    # Teacher notices
    Source(category="teacher_notices", list_url_template="https://iee.zjgsu.edu.cn/?Jstz{page_suffix}"),
    # Student notices
    Source(category="student_notices", list_url_template="https://iee.zjgsu.edu.cn/?Xstz{page_suffix}"),
    # General news (homepage contains latest news feed)
    Source(category="news", list_url_template="https://iee.zjgsu.edu.cn/"),
]

