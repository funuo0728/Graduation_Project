import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests


@dataclass(frozen=True)
class Anchor:
    href: str
    text: str


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_a = False
        self._cur_href: str | None = None
        self._cur_text: list[str] = []
        self.anchors: list[Anchor] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        d = dict(attrs)
        href = d.get("href")
        if not href:
            return
        self._in_a = True
        self._cur_href = href
        self._cur_text = []

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._cur_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._in_a:
            return
        href = self._cur_href or ""
        text = "".join(self._cur_text).strip()
        self.anchors.append(Anchor(href=href, text=text))
        self._in_a = False
        self._cur_href = None
        self._cur_text = []


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://iee.zjgsu.edu.cn/?Gsgg_12.html="
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    p = AnchorParser()
    p.feed(r.text)

    anchors = []
    for a in p.anchors:
        full = urljoin(url, a.href)
        anchors.append((full, a.text))

    # Print the most "content-like" links first
    def score(item: tuple[str, str]) -> tuple[int, int, int]:
        href, text = item
        return (
            int("?" in href or ".html" in href),
            int(len(text) > 0),
            len(text),
        )

    anchors_sorted = sorted(anchors, key=score, reverse=True)
    for href, text in anchors_sorted[:120]:
        print(href)
        if text:
            print("  ", text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
