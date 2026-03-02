import hashlib
import re
import time
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

CAR_SENSOR_BASE = "https://www.carsensor.net"


@dataclass
class CarItem:
    brand: str
    model: str
    year: int
    price: int
    color: str
    link: str
    total_price: int | None = None
    transmission: str | None = None
    title: str | None = None
    mileage_km: int | None = None
    mileage_display: str | None = None
    body_type: str | None = None
    drive_type: str | None = None
    steering: str | None = None
    displacement: str | None = None
    seating_capacity: str | None = None
    engine_type: str | None = None
    door_count: str | None = None

    def source_id(self) -> str:
        return hashlib.sha256(self.link.encode()).hexdigest()[:64]


def fetch_cars(
    max_retries: int = 5,
    timeout: float = 30.0,
    delay_between_pages: float = 1.5,
    max_pages: int = 500,
) -> list[CarItem]:
    all_items: list[CarItem] = []
    seen_links: set[str] = set()
    first_url = f"{CAR_SENSOR_BASE}/usedcar/"

    def log(msg: str) -> None:
        print(f"[scraper] {msg}", flush=True)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        last_error = None
        log(f"Requesting first page: {first_url} (timeout={timeout}s)")
        for attempt in range(max_retries):
            try:
                r = client.get(first_url)
                r.raise_for_status()
                log(f"First page OK, status={r.status_code}, size={len(r.text)} bytes")
                break
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                log(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
        else:
            raise last_error or RuntimeError("fetch failed")

        soup = BeautifulSoup(r.text, "html.parser")
        page_urls = _collect_page_urls(soup, first_url)
        if not page_urls:
            page_urls = [first_url]
        log(f"Pagination: {len(page_urls)} page(s) to fetch (max_pages={max_pages})")

        for i, page_url in enumerate(page_urls):
            if i >= max_pages:
                log(f"Reached max_pages={max_pages}, stopping")
                break
            if i > 0:
                time.sleep(delay_between_pages)
            for attempt in range(max_retries):
                try:
                    log(f"Page {i + 1}/{len(page_urls)}: fetching...")
                    resp = client.get(page_url)
                    resp.raise_for_status()
                    items = _parse_carsensor_list(resp.text)
                    new = sum(1 for it in items if it.link not in seen_links)
                    for item in items:
                        if item.link not in seen_links:
                            seen_links.add(item.link)
                            all_items.append(item)
                    log(f"Page {i + 1}: {len(items)} items ({new} new), total unique={len(all_items)}")
                    break
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    log(f"Page {i + 1} attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)
    log(f"Done: {len(all_items)} cars total")
    return all_items


def fetch_cars_pages(
    max_retries: int = 5,
    timeout: float = 30.0,
    delay_between_pages: float = 1.5,
    max_pages: int = 500,
    stop_after_consecutive_empty: int = 5,
    fetch_details: bool = True,
    delay_between_details: float = 1.0,
):
    """Yields list[CarItem] after each page (only new items per page, deduped by link). Each item's detail page is fetched and data from 状態/基本スペック tables is merged (disable with fetch_details=False)."""
    seen_links: set[str] = set()
    first_url = f"{CAR_SENSOR_BASE}/usedcar/"
    consecutive_empty = 0

    def log(msg: str) -> None:
        print(f"[scraper] {msg}", flush=True)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        last_error = None
        log(f"Requesting first page: {first_url} (timeout={timeout}s)")
        for attempt in range(max_retries):
            try:
                r = client.get(first_url)
                r.raise_for_status()
                log(f"First page OK, status={r.status_code}, size={len(r.text)} bytes")
                break
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                last_error = e
                log(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
        else:
            raise last_error or RuntimeError("fetch failed")

        soup = BeautifulSoup(r.text, "html.parser")
        page_urls = _collect_page_urls(soup, first_url)
        if not page_urls:
            page_urls = [first_url]
        log(f"Pagination: {len(page_urls)} page(s) from site (will stop after {stop_after_consecutive_empty} pages with 0 new, or max_pages={max_pages})")

        for i, page_url in enumerate(page_urls):
            if i >= max_pages:
                log(f"Reached max_pages={max_pages}, stopping")
                break
            if i > 0:
                time.sleep(delay_between_pages)
            for attempt in range(max_retries):
                try:
                    log(f"Page {i + 1}/{len(page_urls)}: fetching...")
                    resp = client.get(page_url)
                    resp.raise_for_status()
                    items = _parse_carsensor_list(resp.text)
                    page_new: list[CarItem] = []
                    for item in items:
                        if item.link not in seen_links:
                            seen_links.add(item.link)
                            page_new.append(item)
                    if len(page_new) == 0:
                        consecutive_empty += 1
                    else:
                        consecutive_empty = 0
                    log(f"Page {i + 1}: {len(items)} items ({len(page_new)} new), total unique={len(seen_links)}")
                    if fetch_details and page_new:
                        merged: list[CarItem] = []
                        for j, item in enumerate(page_new):
                            if j > 0:
                                time.sleep(delay_between_details)
                            log(f"Detail {j + 1}/{len(page_new)}: {item.link}")
                            detail = fetch_car_detail(client, item.link, max_retries=2, delay_after=0)
                            if detail:
                                merged.append(merge_detail_into_item(item, detail))
                            else:
                                merged.append(item)
                        yield merged
                    else:
                        yield page_new
                    break
                except (httpx.HTTPError, httpx.TimeoutException) as e:
                    log(f"Page {i + 1} attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2**attempt)
    log(f"Done: {len(seen_links)} cars total")


def _collect_page_urls(soup: BeautifulSoup, first_url: str) -> list[str]:
    urls: list[str] = []
    base = f"{CAR_SENSOR_BASE}/usedcar"

    for a in soup.select("a[href*='usedcar']"):
        href = (a.get("href") or "").strip()
        if not href or href in ("#", "/") or "/usedcar/detail/" in href:
            continue
        if not href.startswith("http"):
            href = CAR_SENSOR_BASE.rstrip("/") + "/" + href.lstrip("/")
        if href not in urls and (href == first_url or _looks_like_list_page(href)):
            urls.append(href)

    for a in soup.select(".pagination a, .pager a, [class*='page'] a, nav a"):
        href = (a.get("href") or "").strip()
        if not href or href == "#" or "/usedcar/detail/" in href:
            continue
        if not href.startswith("http"):
            href = CAR_SENSOR_BASE.rstrip("/") + "/" + href.lstrip("/")
        if href not in urls and _looks_like_list_page(href):
            urls.append(href)

    if not urls:
        max_page = _detect_max_page(soup)
        if max_page and max_page > 1:
            urls = [first_url]
            for p in range(2, min(max_page + 1, 501)):
                urls.append(f"{base}/?page={p}")
        else:
            urls = [first_url]

    deduped = list(dict.fromkeys(urls))
    if first_url not in deduped:
        deduped.insert(0, first_url)
    return deduped


def _looks_like_list_page(href: str) -> bool:
    if "/usedcar/detail/" in href:
        return False
    if "/usedcar" in href and ("index" in href or "page=" in href or "/p" in href):
        return True
    if href.rstrip("/").endswith("/usedcar") or href == f"{CAR_SENSOR_BASE}/usedcar/":
        return True
    return False


def _detect_max_page(soup: BeautifulSoup) -> int | None:
    max_p = 1
    for a in soup.select("a[href*='page'], a[href*='index'], .pagination a, .pager a"):
        href = a.get("href") or ""
        for m in re.finditer(r"page=(\d+)|index(\d+)\.html|/p(\d+)/|p(?:age)?[=_]?(\d+)", href):
            for g in m.groups():
                if g and g.isdigit():
                    max_p = max(max_p, int(g))
    text = soup.get_text()
    for m in re.finditer(r"(\d+)\s*ページ|全\s*(\d+)\s*ページ|of\s*(\d+)", text):
        for g in m.groups():
            if g and g.isdigit():
                max_p = max(max_p, int(g))
    return max_p if max_p > 1 else None


def _parse_carsensor_list(html: str) -> list[CarItem]:
    items = []
    soup = BeautifulSoup(html, "html.parser")
    for block in soup.select("[data-car-id], .cassetteMain, .searchResultItem, .boxList"):
        link_el = block.select_one("a[href*='/usedcar/detail/']") or block.select_one("a[href*='usedcar']")
        if not link_el:
            continue
        link = (link_el.get("href", "") or "").strip()
        if not link:
            continue
        if not link.startswith("http"):
            link = CAR_SENSOR_BASE.rstrip("/") + "/" + link.lstrip("/")
        text = block.get_text()
        title = _extract_title(block)
        _p = "()（）"
        raw_brand = (title.split()[0][:64] if (title and title.strip()) else "") or "—"
        brand = raw_brand.lstrip("(").rstrip(")").strip() or "—"
        model = _extract_model(block, text)
        year = _extract_year_from_spec(block) or _extract_year(text) or 2020
        price = _extract_price(text) or 0
        total_price = _extract_total_price(block) or price
        if price <= 0 and total_price <= 0:
            continue
        color = _extract_color_from_block(block) or _extract_color(text) or "—"
        transmission = _extract_transmission(block)
        mileage_km = _extract_mileage_km(block)
        body_type = _extract_body_type(block)
        items.append(
            CarItem(
                brand=brand,
                model=model,
                year=year,
                price=total_price or price,
                color=color,
                link=link,
                total_price=total_price or None,
                transmission=transmission,
                title=title,
                mileage_km=mileage_km,
                mileage_display=None,
                body_type=body_type,
                drive_type=None,
                steering=None,
                displacement=None,
                seating_capacity=None,
                engine_type=None,
                door_count=None,
            )
        )
    return items


def _extract_title(block: BeautifulSoup) -> str | None:
    el = block.select_one("h3.cassetteMain__title a, .cassetteMain__title a, h3.cassetteMain__title")
    if el:
        raw = el.get_text(separator=" ", strip=True)[:1024] or ""
        if raw:
            return _strip_prefectures(raw) or None
    return None


def _extract_total_price(block: BeautifulSoup) -> int | None:
    main = block.select_one(".totalPrice__mainPriceNum")
    sub = block.select_one(".totalPrice__subPriceNum")
    if not main:
        return None
    main_t = main.get_text(strip=True).replace(",", "")
    sub_t = (sub.get_text(strip=True) if sub else "").replace(",", "").lstrip(".")
    try:
        val = float(main_t + ("." + sub_t if sub_t else ""))
        return int(val * 10_000)
    except ValueError:
        return None


def _extract_year_from_spec(block: BeautifulSoup) -> int | None:
    for box in block.select(".specList__detailBox"):
        dt = box.select_one(".specList__title")
        if dt and "年式" in (dt.get_text() or ""):
            dd = box.select_one(".specList__emphasisData, .specList__data span")
            if dd:
                m = re.search(r"20[12][0-9]|19[89][0-9]", dd.get_text() or "")
                if m:
                    return int(m.group())
    return None


def _extract_transmission(block: BeautifulSoup) -> str | None:
    for box in block.select(".specList__detailBox"):
        dt = box.select_one(".specList__title")
        if dt and "ミッション" in (dt.get_text() or ""):
            dd = box.select_one(".specList__data")
            if dd:
                return (dd.get_text(strip=True) or None)[:64] or None
    return None


def _extract_mileage_km(block: BeautifulSoup) -> int | None:
    for box in block.select(".specWrap__box"):
        title_el = box.select_one(".specWrap__box__title")
        if not title_el or "走行距離" not in (title_el.get_text() or ""):
            continue
        num_el = box.select_one(".specWrap__box__num")
        unit_el = box.select_one(".specWrap__boxUnit")
        if num_el:
            try:
                val = float((num_el.get_text(strip=True) or "").replace(",", "."))
                unit_txt = (unit_el.get_text(strip=True) or "") if unit_el else ""
                if "万" in unit_txt:
                    return int(val * 10_000)
                return int(val)
            except ValueError:
                pass
    for box in block.select(".specList__detailBox"):
        dt = box.select_one(".specList__title")
        if dt and "走行距離" in (dt.get_text() or ""):
            dd = box.select_one(".specList__data")
            if dd:
                t = dd.get_text(strip=True) or ""
                m = re.search(r"([\d.,]+)\s*(万)?\s*km", t, re.I)
                if m:
                    try:
                        val = float(m.group(1).replace(",", "."))
                        if m.group(2):
                            return int(val * 10_000)
                        return int(val)
                    except ValueError:
                        pass
    return None


def _extract_body_type(block: BeautifulSoup) -> str | None:
    for item in block.select(".carBodyInfoList__item"):
        t = (item.get_text(strip=True) or "").strip()[:64]
        if t and _extract_color(t) is None:
            return t
    return None


def _extract_color_from_block(block: BeautifulSoup) -> str | None:
    for item in block.select(".carBodyInfoList__item"):
        t = item.get_text(strip=True) or ""
        if _extract_color(t):
            return _extract_color(t)
    return None


def _extract_model(block: BeautifulSoup, text: str) -> str:
    model_el = block.select_one(".modelName, .nameModel, [class*='model']")
    if model_el:
        return model_el.get_text(strip=True)[:64] or "—"
    return "—"


def _extract_year(text: str) -> int | None:
    m = re.search(r"20[12][0-9]|19[89][0-9]", text)
    return int(m.group()) if m else None


def _extract_price(text: str) -> int | None:
    m = re.search(r"(\d{1,3}(?:,\d{3})*)\s*万円", text) or re.search(r"(\d+)\s*万", text)
    if m:
        return int(m.group(1).replace(",", "")) * 10_000
    m = re.search(r"(\d[\d,]*)\s*円", text)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def _extract_color(text: str) -> str | None:
    colors_ja = ["白", "黒", "赤", "銀", "青", "グレー", "ベージュ", "緑", "黄", "金", "シルバー", "ブラック", "レッド", "ブルー", "ホワイト"]
    for c in colors_ja:
        if c in text:
            return c
    return None


def _parse_detail_tables(soup: BeautifulSoup) -> dict[str, str]:
    spec: dict[str, str] = {}
    for section_id in ("sec-joutai", "sec-kihon"):
        h2 = soup.find("h2", id=section_id)
        if not h2:
            continue
        section = h2.find_parent("section") or h2.find_parent("div")
        if not section:
            continue
        table = section.select_one("table.defaultTable__table")
        if not table:
            continue
        for tr in table.select("tbody tr"):
            cells = tr.find_all(["th", "td"])
            i = 0
            while i < len(cells):
                c = cells[i]
                if c.name == "th":
                    head = (c.get_text(strip=True) or "").strip()
                    head_clean = re.sub(r"\([^)]*\)$", "", head).strip()
                    if i + 1 < len(cells) and cells[i + 1].name == "td":
                        val = (cells[i + 1].get_text(strip=True) or "").strip().replace("\u00a0", " ")
                        if head_clean:
                            spec[head_clean] = val
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
    return spec


def _parse_detail_spec(spec: dict[str, str]) -> dict:
    out: dict = {}
    for k, v in spec.items():
        if not v or v in ("－", "—", "-"):
            continue
        if "年式" in k:
            m = re.search(r"20[12][0-9]|19[89][0-9]", v)
            if m:
                out["year"] = int(m.group())
        elif "走行距離" in k:
            out["mileage_display"] = v.strip()[:32]
            m = re.search(r"([\d.,]+)\s*(万)?\s*km", v, re.I)
            if m:
                try:
                    val = float(m.group(1).replace(",", "."))
                    out["mileage_km"] = int(val * 10_000) if m.group(2) else int(val)
                except ValueError:
                    pass
        elif "ボディタイプ" in k:
            out["body_type"] = v[:64]
        elif "色" in k and "ボディ" not in k:
            out["color"] = v[:64]
        elif "ミッション" in k:
            out["transmission"] = v[:64]
        elif "駆動方式" in k:
            out["drive_type"] = v[:32]
        elif "ハンドル" in k:
            out["steering"] = v[:16]
        elif "排気量" in k:
            out["displacement"] = v[:32]
        elif "乗車定員" in k:
            out["seating_capacity"] = v[:16]
        elif "エンジン種別" in k:
            out["engine_type"] = v[:32]
        elif "ドア数" in k:
            out["door_count"] = v[:8]
    return out


def _strip_prefectures(s: str) -> str:
    if not s or not s.strip():
        return s
    s = s.strip()
    parts = s.split()
    suffix_re = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3000-\u303fー・]{2,6}[都道府県]$")
    cleaned = []
    for i, p in enumerate(parts):
        if (p.endswith(")") or p.endswith("）")) and len(p) >= 2 and p[-2] in "都道府県":
            p = p[:-1].rstrip()
        if len(p) < 2 or p[-1] not in "都道府県":
            cleaned.append(p)
            continue
        suffix = suffix_re.search(p)
        if suffix:
            rest = p[: suffix.start()].rstrip()
            if rest:
                cleaned.append(rest)
        elif len(p) > 6:
            cleaned.append(p)
    while cleaned and len(cleaned[-1]) >= 2 and cleaned[-1][-1] in "都道府県":
        cleaned.pop()
    return " ".join(cleaned).strip()


def _parse_detail_h2_span_text(soup: BeautifulSoup) -> str | None:
    for h2 in soup.select("h2.title3[id^='sec-'] span"):
        t = (h2.get_text(strip=True) or "").replace("\u00a0", " ").strip()
        t = _strip_prefectures(t)
        _parens = "()（）"
        t = t.lstrip(_parens).rstrip(_parens).strip()
        if 2 <= len(t) <= 120:
            return t
    return None


def _parse_detail_model_from_h2(soup: BeautifulSoup) -> str | None:
    t = _parse_detail_h2_span_text(soup)
    return t[:64] if t else None


def _parse_detail_brand_from_h2(soup: BeautifulSoup) -> str | None:
    t = _parse_detail_h2_span_text(soup)
    if not t:
        return None
    _p = "()（）"
    first = (t.split()[0].lstrip(_p).rstrip(_p).strip() if t.split() else "") or ""
    return first[:64] if first else None


def fetch_car_detail(
    client: httpx.Client,
    url: str,
    max_retries: int = 2,
    delay_after: float = 0.8,
) -> dict | None:
    for attempt in range(max_retries):
        try:
            r = client.get(url)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            spec = _parse_detail_tables(soup)
            detail = _parse_detail_spec(spec) or {}
            model = _parse_detail_model_from_h2(soup)
            if model:
                detail["model"] = model
            brand = _parse_detail_brand_from_h2(soup)
            if brand:
                detail["brand"] = brand
            if not detail:
                return None
            return detail
        except (httpx.HTTPError, httpx.TimeoutException):
            if attempt < max_retries - 1:
                time.sleep(1.0 * (attempt + 1))
    return None


def merge_detail_into_item(item: CarItem, detail: dict) -> CarItem:
    def _get(key: str, default=None):
        v = detail.get(key)
        return v if v is not None else default
    return CarItem(
        brand=_get("brand") or item.brand,
        model=_get("model") or item.model,
        year=detail.get("year") if detail.get("year") is not None else item.year,
        price=item.price,
        color=_get("color") or item.color,
        link=item.link,
        total_price=item.total_price,
        transmission=_get("transmission") if detail.get("transmission") is not None else item.transmission,
        title=item.title,
        mileage_km=detail.get("mileage_km") if detail.get("mileage_km") is not None else item.mileage_km,
        mileage_display=_get("mileage_display") if detail.get("mileage_display") is not None else item.mileage_display,
        body_type=_get("body_type") if detail.get("body_type") is not None else item.body_type,
        drive_type=_get("drive_type") if detail.get("drive_type") is not None else item.drive_type,
        steering=_get("steering") if detail.get("steering") is not None else item.steering,
        displacement=_get("displacement") if detail.get("displacement") is not None else item.displacement,
        seating_capacity=_get("seating_capacity") if detail.get("seating_capacity") is not None else item.seating_capacity,
        engine_type=_get("engine_type") if detail.get("engine_type") is not None else item.engine_type,
        door_count=_get("door_count") if detail.get("door_count") is not None else item.door_count,
    )
