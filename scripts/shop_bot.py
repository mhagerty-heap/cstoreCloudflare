#!/usr/bin/env python3
"""Generic shopping-flow script for the CStore demo (forcemultiplying.com).

Runs home -> /shop -> PDP -> add to cart -> cart -> checkout -> confirmation.

Two profiles, so Cloudflare scores some sessions as bots and others as humans:
  bot    headless Chrome, default "HeadlessChrome" UA, navigator.webdriver=true,
         instant clicks, no scrolling/mouse, form filled via JS, no pauses.
  human  also headless, but "HeadlessChrome" removed from the UA, webdriver
         flag hidden, randomized pauses, scrolling, per-keystroke typing.

Usage:
  python3 scripts/shop_bot.py --runs 20 --gap 5     # mixed bot/human (default)
"""
import argparse, random, time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://forcemultiplying.com"
PDPS = [
    "converse-x-keith-haring-chuck-70",
    "vans-ua-evdnt-ultimatewaffle",
    "adidas-originals-zx-500-rm",
    "puma-mirage-mox-eb",
]
FORM = {
    "shipping-name": "Alex Morgan",
    "shipping-email": "alex.morgan@example.com",
    "shipping-address": "123 Market Street",
    "shipping-city": "San Francisco",
    "shipping-state": "CA",
    "shipping-zip": "94103",
    "cc-name": "Alex Morgan",
    "cc-number": "4111 1111 1111 1111",
    "cc-expiry": "12/30",
    "cc-cvv": "123",
}


class Challenged(Exception):
    pass


def is_challenged(d):
    try:
        return d.title.startswith("Just a moment")
    except Exception:
        return False


def make_driver(profile):
    o = webdriver.ChromeOptions()
    o.page_load_strategy = "eager"  # don't wait for the challenge page's scripts
    o.add_argument("--window-size=1366,900")
    o.add_argument("--headless=new")  # all profiles run headless
    o.add_argument("--no-sandbox")  # required when running as root
    o.add_argument("--disable-dev-shm-usage")
    if profile == "human":
        o.add_experimental_option("excludeSwitches", ["enable-automation"])
        o.add_argument("--disable-blink-features=AutomationControlled")
    d = webdriver.Chrome(options=o)
    if profile == "human":  # drop the "HeadlessChrome" tell from the UA
        ua = d.execute_script("return navigator.userAgent").replace("HeadlessChrome", "Chrome")
        d.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": ua})
    d.set_page_load_timeout(20)
    return d


class Shopper:
    def __init__(self, d, profile):
        self.d, self.human = d, profile == "human"
        self.wait = WebDriverWait(d, 15)

    def until(self, cond):
        """Like wait.until, but aborts immediately if a challenge page appears."""
        def check(d):
            if is_challenged(d):
                raise Challenged()
            return cond(d)
        return self.wait.until(check)

    def pause(self, lo=0.6, hi=2.2):
        if self.human:
            time.sleep(random.uniform(lo, hi))

    def go(self, path):
        self.d.get(BASE + path)
        if is_challenged(self.d):
            raise Challenged()
        self.pause()
        if self.human:
            self.d.execute_script(
                "window.scrollBy(0, arguments[0])", random.randint(200, 700))
            self.pause(0.3, 1.0)

    def click(self, css):
        el = self.until(EC.presence_of_element_located((By.CSS_SELECTOR, css)))
        if self.human:
            self.d.execute_script(
                "arguments[0].scrollIntoView({block:'center'})", el)
            self.pause(0.3, 0.9)
        try:
            el.click()
        except Exception:  # hover overlays -> JS fallback
            self.d.execute_script("arguments[0].click()", el)
        self.pause()

    def fill(self, field_id, value):
        el = self.d.find_element(By.ID, field_id)
        if self.human:
            self.d.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
            el.clear()
            for ch in value:
                el.send_keys(ch)
                time.sleep(random.uniform(0.04, 0.2))
            self.pause(0.2, 0.7)
        else:
            self.d.execute_script(
                "arguments[0].value=arguments[1];"
                "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));",
                el, value)

    def run(self):
        self.go("/")
        self.click("#nav-all-products")
        self.until(EC.url_contains("/shop"))
        slug = random.choice(PDPS)
        self.click(f'a[href="/product/{slug}"]')
        self.until(EC.url_contains("/product/"))
        self.pause(1, 3)
        self.click("#pd-add-to-cart")
        self.until(EC.url_contains("/cart"))
        self.click("#proceed-to-checkout")
        self.until(EC.url_contains("/checkout"))
        for k, v in FORM.items():
            self.fill(k, v)
        self.click("#place-order-btn")
        self.until(EC.url_contains("/checkout/confirmation"))
        self.until(EC.presence_of_element_located(
            (By.ID, "confirmation-order-number")))
        self.pause(1, 3)


def one_run(profile):
    d = make_driver(profile)
    try:
        Shopper(d, profile).run()
        print(f"[{profile}] OK -> {d.current_url}")
        return "ok"
    except Challenged:
        print(f"[{profile}] CHALLENGED by Cloudflare at {d.current_url}")
        return "challenged"
    except Exception as e:
        if is_challenged(d):
            print(f"[{profile}] CHALLENGED by Cloudflare at {d.current_url}")
            return "challenged"
        print(f"[{profile}] FAILED at {d.current_url}: {type(e).__name__}")
        return "failed"
    finally:
        d.quit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["bot", "human", "mixed"], default="mixed")
    ap.add_argument("--bot-ratio", type=float, default=0.5,
                    help="fraction of bot sessions when profile=mixed")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--gap", type=float, default=5, help="avg seconds between runs")
    a = ap.parse_args()
    tally = {}
    for i in range(a.runs):
        p = a.profile
        if p == "mixed":
            p = "bot" if random.random() < a.bot_ratio else "human"
        r = one_run(p)
        key = f"{p}:{r}"
        tally[key] = tally.get(key, 0) + 1
        if i < a.runs - 1:
            time.sleep(random.uniform(0.5 * a.gap, 1.5 * a.gap))
    print("summary:", tally)


if __name__ == "__main__":
    main()
