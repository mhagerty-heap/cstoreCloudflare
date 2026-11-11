#!/usr/bin/env python3
"""AI-crawler traffic generator for the CStore demo (forcemultiplying.com).

Plain HTTP GETs only (no browser, no JS, no assets), like real AI crawlers.
Each run picks one crawler identity and behaves according to its category:

  training crawler   fetches robots.txt, obeys it, crawls many pages
  search crawler     fetches robots.txt, obeys it, fetches a few pages
  supporting crawler fetches robots.txt, obeys it, fetches a few pages
  user-triggered     skips robots.txt, fetches 1-2 pages (may hit /cart, /checkout)

robots.txt (public/robots.txt) disallows /cart and /checkout for everyone and the
whole site for CCBot and Bytespider, so those URLs are only reached by
user-triggered agents ("not reached" vs. "reached despite policy" demo).

Usage:
  python3 scripts/ai_crawler_bot.py --runs 20 --gap 3
  python3 scripts/ai_crawler_bot.py --agent GPTBot --runs 3
  python3 scripts/ai_crawler_bot.py --list
"""
import argparse, random, time, urllib.robotparser
import requests

BASE = "https://forcemultiplying.com"
PRODUCTS = [
    "/product/converse-x-keith-haring-chuck-70",
    "/product/vans-ua-evdnt-ultimatewaffle",
    "/product/adidas-originals-zx-500-rm",
    "/product/puma-mirage-mox-eb",
]
BROWSABLE = ["/", "/shop"] + PRODUCTS
RESTRICTED = ["/cart", "/checkout", "/checkout/confirmation/ORD-1794240459025"]

MOZ = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; "
CHR = "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; {}) Chrome/130.0.0.0 Safari/537.36"

TRAIN, SEARCH, USER, SUPPORT = "training", "search", "user", "supporting"

# (token, operator, category, weight, full user-agent string)
AGENTS = [
    ("GPTBot", "OpenAI", TRAIN, 10, MOZ + "GPTBot/1.4; +https://openai.com/gptbot"),
    ("OAI-SearchBot", "OpenAI", SEARCH, 6, MOZ + "OAI-SearchBot/1.4; +https://openai.com/searchbot"),
    ("ChatGPT-User", "OpenAI", USER, 8, MOZ + "ChatGPT-User/1.0; +https://openai.com/bot"),
    ("OAI-AdsBot", "OpenAI", SUPPORT, 2, MOZ + "OAI-AdsBot/1.0; +https://openai.com/adsbot"),
    ("ClaudeBot", "Anthropic", TRAIN, 9, "ClaudeBot/1.0; +claudebot@anthropic.com"),
    ("Claude-SearchBot", "Anthropic", SEARCH, 4, "Claude-SearchBot/1.0"),
    ("Claude-User", "Anthropic", USER, 5, "Claude-User/1.0"),
    ("PerplexityBot", "Perplexity", SEARCH, 5, "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)"),
    ("Perplexity-User", "Perplexity", USER, 4, "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)"),
    ("Google-CloudVertexBot", "Google", SUPPORT, 2, "Google-CloudVertexBot"),
    ("Google-Agent", "Google", USER, 3, MOZ + "Google-Agent;"),
    ("Google-GeminiNotebook", "Google", USER, 2, "Google-GeminiNotebook"),
    ("meta-externalagent", "Meta", TRAIN, 6, "meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)"),
    ("meta-webindexer", "Meta", SEARCH, 3, "meta-webindexer/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)"),
    ("meta-externalfetcher", "Meta", USER, 3, "meta-externalfetcher/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)"),
    ("Amazonbot", "Amazon", TRAIN, 5, CHR.format("Amazonbot/0.1")),
    ("Amzn-SearchBot", "Amazon", SEARCH, 3, CHR.format("Amzn-SearchBot/0.1")),
    ("Amzn-User", "Amazon", USER, 3, CHR.format("Amzn-User/0.1")),
    ("MistralAI-Training", "Mistral", TRAIN, 2, MOZ + "MistralAI-Training/1.0; +https://docs.mistral.ai/robots"),
    ("MistralAI-Index", "Mistral", SEARCH, 2, MOZ + "MistralAI-Index/1.0; +https://docs.mistral.ai/robots"),
    ("MistralAI-User", "Mistral", USER, 2, MOZ + "MistralAI-User/1.0; +https://docs.mistral.ai/robots"),
    ("DuckAssistBot", "DuckDuckGo", SEARCH, 3, "DuckAssistBot/1.2; (+http://duckduckgo.com/duckassistbot.html)"),
    ("AI2Bot", "Ai2", TRAIN, 2, "Mozilla/5.0 (compatible) AI2Bot (+https://www.allenai.org/crawler)"),
    ("CCBot", "Common Crawl", SUPPORT, 4, "CCBot/2.0 (https://commoncrawl.org/faq/)"),
    ("Applebot", "Apple", SUPPORT, 5, "Mozilla/5.0 (Applebot/0.1; +http://www.apple.com/go/applebot)"),
    ("Bytespider", "ByteDance", SUPPORT, 3, "Mozilla/5.0 (compatible; Bytespider; https://zhanzhang.toutiao.com/)"),
]


# Relative popularity: home and listing are crawled most, products less,
# cart/checkout rarely (user-triggered agents only).
PAGE_WEIGHT = {"/": 10, "/shop": 6, "/cart": 1, "/checkout": 1}
DEFAULT_WEIGHT = 3  # product pages


def weighted_sample(pool, n):
    """n distinct paths, drawn without replacement by PAGE_WEIGHT."""
    pool, out = list(pool), []
    for _ in range(min(n, len(pool))):
        p = random.choices(pool, weights=[PAGE_WEIGHT.get(x, DEFAULT_WEIGHT) for x in pool])[0]
        pool.remove(p)
        out.append(p)
    return out


def plan_paths(category, rp, token):
    """Pick the URLs this identity would request."""
    if category == USER:  # ignores robots.txt, targeted fetches
        return weighted_sample(BROWSABLE + RESTRICTED[:2], random.randint(1, 2))
    allowed = [p for p in BROWSABLE if rp.can_fetch(token, BASE + p)]
    if not allowed:
        return []
    n = {TRAIN: random.randint(4, len(allowed)),
         SEARCH: random.randint(2, 4),
         SUPPORT: random.randint(1, 3)}[category]
    return weighted_sample(allowed, n)


def one_run(agent, sess, gap):
    token, operator, category, _, ua = agent
    sess.headers["User-Agent"] = ua
    rp = urllib.robotparser.RobotFileParser()
    if category == USER:
        rp.parse([])
    else:
        r = sess.get(BASE + "/robots.txt", timeout=20)
        print(f"[{token}] GET /robots.txt -> {r.status_code}")
        rp.parse(r.text.splitlines() if r.ok else [])
    paths = plan_paths(category, rp, token)
    if not paths:
        print(f"[{token}] robots.txt disallows everything; nothing fetched")
    for p in paths:
        r = sess.get(BASE + p, timeout=20)
        print(f"[{token}] ({operator}/{category}) GET {p} -> {r.status_code}")
        time.sleep(random.uniform(0.3, 1.5) if gap else 0)
    return token, len(paths)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", help="crawler token to use (default: weighted random)")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--gap", type=float, default=3, help="avg seconds between runs")
    ap.add_argument("--list", action="store_true", help="list known agents and exit")
    a = ap.parse_args()
    if a.list:
        for t, o, c, w, ua in AGENTS:
            print(f"{t:24} {o:13} {c:11} w={w:<3} {ua}")
        return
    pool = AGENTS
    if a.agent:
        pool = [x for x in AGENTS if x[0].lower() == a.agent.lower()]
        if not pool:
            raise SystemExit(f"unknown agent {a.agent!r}; use --list")
    tally = {}
    sess = requests.Session()
    for i in range(a.runs):
        agent = random.choices(pool, weights=[x[3] for x in pool])[0]
        sess.cookies.clear()
        try:
            token, n = one_run(agent, sess, a.gap)
            tally[token] = tally.get(token, 0) + n
        except requests.RequestException as e:
            print(f"[{agent[0]}] FAILED: {type(e).__name__}")
        if i < a.runs - 1:
            time.sleep(random.uniform(0.5 * a.gap, 1.5 * a.gap))
    print("summary (page requests by agent):", tally)


if __name__ == "__main__":
    main()
