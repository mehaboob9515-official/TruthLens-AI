from urllib.parse import urlparse

trusted_sources = {
    "bbc.com": "⭐⭐⭐⭐⭐ Highly Trusted",
    "bbc.co.uk": "⭐⭐⭐⭐⭐ Highly Trusted",
    "reuters.com": "⭐⭐⭐⭐⭐ Highly Trusted",
    "apnews.com": "⭐⭐⭐⭐⭐ Highly Trusted",
    "nasa.gov": "⭐⭐⭐⭐⭐ Government Source",
    "who.int": "⭐⭐⭐⭐⭐ Official Organization",
    "un.org": "⭐⭐⭐⭐⭐ Official Organization",
    "nytimes.com": "⭐⭐⭐⭐ Trusted",
    "theguardian.com": "⭐⭐⭐⭐ Trusted",
    "cnn.com": "⭐⭐⭐⭐ Trusted",
    "cbsnews.com": "⭐⭐⭐⭐ Trusted",
    "abcnews.go.com": "⭐⭐⭐⭐ Trusted",
    "foxnews.com": "⭐⭐⭐ Mixed Reputation",
    "dailymail.co.uk": "⭐⭐ Mixed Reputation"
}


def check_source(url):
    domain = urlparse(url).netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    for site, rating in trusted_sources.items():
        if site in domain:
            return site, rating

    return domain, "❓ Unknown Source"