import base64
import html as html_lib
import os
import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
import pandas as pd
import time, random, hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional, Dict, Tuple, List
from difflib import SequenceMatcher
import json
import os

try:
    from wordfreq import zipf_frequency
    WORDFREQ_OK = True
except Exception:
    WORDFREQ_OK = False

def _env_or_secret(key: str, default=None):
    v = os.getenv(key)
    if v is not None and str(v).strip() != "":
        return v
    return _secrets_get(key, default)

def _first_secret(keys: List[str], default=None):
    for key in keys:
        v = _env_or_secret(key, None)
        if v is not None and str(v).strip() != "":
            return v
    return default

# Optional (recommended): JS rendering tool
# pip install playwright
# playwright install chromium
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except Exception:
    PLAYWRIGHT_OK = False


# =====================================================
# PAGE CONFIG (MUST BE FIRST STREAMLIT CALL)
# =====================================================
st.set_page_config(page_title="Bayut Competitor Gap Analysis", layout="wide")
BAYUT_GREEN = "#0E8A6D"
BAYUT_GREEN_2 = "#26B89F"
INK = "#111827"
MUTED = "#6B7280"
PAGE_BG = "#F3FBF7"

# =====================================================
# NEW DESIGN (Tailwind/shadcn-inspired theme from your React CSS)
# =====================================================
st.markdown(
    """
<style>
/* ------------------------------
   Theme tokens (same spirit as src/index.css)
--------------------------------*/
:root{
  --bayut-primary: 163 82% 30%;
  --bayut-primary-light: 163 72% 40%;
  --bayut-primary-dark: 163 90% 22%;
  --bayut-glow: 163 60% 50%;

  --background: 150 55% 96%;
  --foreground: 220 25% 12%;

  --card: 0 0% 100%;
  --border: 150 20% 88%;
  --muted: 150 15% 92%;
  --muted-foreground: 220 10% 45%;

  --secondary: 150 30% 94%;
  --accent: 163 60% 92%;

  --primary: 163 82% 30%;
  --primary-foreground: 0 0% 100%;

  --radius: 0.75rem;

  --gradient-hero: linear-gradient(135deg, hsl(163 82% 30%) 0%, hsl(163 60% 45%) 50%, hsl(175 70% 40%) 100%);
  --gradient-card: linear-gradient(180deg, hsl(0 0% 100%) 0%, hsl(150 45% 96%) 100%);
  --gradient-surface: linear-gradient(135deg, hsl(150 55% 96%) 0%, hsl(163 40% 95%) 100%);

  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.03);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.03);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.06), 0 4px 6px -4px rgb(0 0 0 / 0.04);
  --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.07), 0 8px 10px -6px rgb(0 0 0 / 0.04);
  --shadow-glow: 0 0 30px -5px hsl(163 82% 30% / 0.25);
}

/* ------------------------------
   App background + layout
--------------------------------*/
html, body { background: hsl(var(--background)) !important; }
[data-testid="stAppViewContainer"]{
  background: var(--gradient-surface) !important;
}
[data-testid="stHeader"] { background: transparent !important; }
section.main > div.block-container{
  max-width: 1040px !important;
  padding-top: 1.6rem !important;
  padding-bottom: 2.8rem !important;
}

/* Decorative background "blobs" like Index.tsx */
.bg-decor {
  position: fixed;
  inset: 0;
  z-index: -10;
  overflow: hidden;
}
.bg-decor .blob{
  position: absolute;
  border-radius: 9999px;
  filter: blur(60px);
  opacity: 0.35;
  animation: float 6s ease-in-out infinite;
}
.bg-decor .b1{ top:-90px; left:18%; width:520px; height:520px; background: hsl(var(--primary) / 0.28); }
.bg-decor .b2{ bottom:-120px; right:18%; width:460px; height:460px; background: hsl(var(--primary) / 0.2); animation-delay:-3s; }
.bg-decor .b3{ top:40%; left:-120px; width:420px; height:420px; background: hsl(163 60% 92% / 0.55); animation-delay:-1.5s; }
@keyframes float { 0%,100%{ transform: translateY(0);} 50%{ transform: translateY(-10px);} }

/* subtle grid overlay */
.grid-overlay{
  position:absolute; inset:0; opacity:0.035;
  background-image:
    linear-gradient(hsl(var(--foreground)) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--foreground)) 1px, transparent 1px);
  background-size: 64px 64px;
}

/* ------------------------------
   Reusable classes (from your Tailwind components)
--------------------------------*/
.gradient-text{
  background: var(--gradient-hero);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.card-elevated{
  background: var(--gradient-card);
  box-shadow: var(--shadow-lg);
  border: 1px solid hsl(var(--border));
  border-radius: 1.25rem;
}
.glow-hover{ transition: box-shadow 0.25s ease; }
.glow-hover:hover{ box-shadow: var(--shadow-glow); }
.pill{
  display:inline-flex; align-items:center; gap:.5rem;
  padding:.45rem .9rem;
  border-radius: 9999px;
  font-weight: 800;
  font-size: 13px;
  background: hsl(163 45% 95%);
  color: hsl(var(--primary));
  border: 1px solid hsl(var(--border));
}
.section-title{
  font-weight: 800;
  font-size: 18px;
  position: relative;
  display:inline-block;
  margin: 20px 0 10px 0;
}
.section-title:after{
  content:"";
  position:absolute;
  left:0; bottom:-6px;
  width:32px; height:3px;
  border-radius:9999px;
  background: hsl(var(--primary));
}

.footer-note{
  text-align: center;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
  margin: 26px 0 8px 0;
}

/* ------------------------------
   Hero styling
--------------------------------*/
.hero-wrap{
  padding: 1.4rem 0 0.6rem 0;
  text-align:center;
  display:flex;
  flex-direction:column;
  align-items:center;
  position: relative;
}
.hero-wrap:before{
  content:"";
  position:absolute;
  top:-200px;
  left:50%;
  transform: translateX(-50%);
  width: 1020px;
  height: 560px;
  background: radial-gradient(circle at center, hsl(163 70% 82% / 0.6), transparent 60%);
  z-index: -1;
}
.hero-wrap:after{
  content:"";
  position:absolute;
  top:-120px;
  left:50%;
  transform: translateX(-50%);
  width: 820px;
  height: 460px;
  background: radial-gradient(circle at center, hsl(163 75% 85% / 0.5), transparent 62%);
  z-index: -1;
}
.hero-icon{
  width:76px; height:76px; margin:0 auto 18px auto;
  border-radius: 22px;
  background: linear-gradient(135deg, hsl(150 75% 44%) 0%, hsl(163 82% 30%) 100%);
  box-shadow: 0 16px 32px -18px hsl(163 82% 30% / 0.7), var(--shadow-md);
  border: 1px solid hsl(var(--primary) / 0.15);
  display:flex; align-items:center; justify-content:center;
}
.hero-icon svg{
  width: 38px;
  height: 38px;
  color: white;
}
.hero-h1{
  font-size: 70px !important;
  line-height: 1.06;
  margin: 0;
  color: hsl(var(--foreground));
  font-weight: 900;
  letter-spacing: -0.02em;
}
.hero-sub{
  margin: 10px auto 0 auto;
  max-width: 560px;
  width: 100%;
  color: hsl(var(--muted-foreground));
  font-size: 16px;
  line-height: 1.6;
  text-align: center !important;
  margin-left: auto;
  margin-right: auto;
}
.hero-badges{ margin-top: 14px; display:flex; justify-content:center; gap:10px; flex-wrap:wrap; }
.hero-badge{
  display:inline-flex; align-items:center; gap:8px;
  padding: 8px 12px;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border));
  background: hsl(var(--card));
  box-shadow: var(--shadow-sm);
  font-weight: 800;
  font-size: 13px;
  color: hsl(var(--foreground));
}
.hero-badge .icon{
  display:inline-flex;
  align-items:center;
  justify-content:center;
}
.hero-badge svg{
  width: 20px;
  height: 20px;
  color: hsl(var(--primary));
}

/* ------------------------------
   Streamlit widgets styling
--------------------------------*/
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea{
  background: hsl(var(--secondary) / 0.6) !important;
  border: 1px solid hsl(var(--border)) !important;
  border-radius: 16px !important;
  padding: 12px 14px !important;
  font-size: 15px !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus{
  box-shadow: 0 0 0 4px hsl(var(--primary) / 0.18) !important;
  border-color: hsl(var(--primary)) !important;
}

/* Buttons (best-effort across Streamlit versions) */
div[data-testid="stButton"] > button,
div[data-testid="stFormSubmitButton"] > button{
  border-radius: 16px !important;
  padding: 0.85rem 1rem !important;
  font-weight: 900 !important;
  border: 1px solid hsl(var(--border)) !important;
  background: hsl(var(--secondary)) !important;
  color: hsl(var(--foreground)) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: transform .1s ease, box-shadow .25s ease, background .2s ease !important;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover{
  transform: translateY(-1px);
  box-shadow: var(--shadow-md), var(--shadow-glow) !important;
  background: hsl(var(--accent)) !important;
}
/* Primary */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button[kind="primary"]{
  background: hsl(var(--primary)) !important;
  color: hsl(var(--primary-foreground)) !important;
  border-color: hsl(var(--primary)) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover{
  background: hsl(var(--primary-dark)) !important;
}
/* Ensure form submit stays primary */
div[data-testid="stFormSubmitButton"] > button{
  background: hsl(var(--primary)) !important;
  color: hsl(var(--primary-foreground)) !important;
  border-color: hsl(var(--primary)) !important;
}
div[data-testid="stFormSubmitButton"] > button:hover{
  background: hsl(var(--primary-dark)) !important;
}

/* Mode toggle */
.mode-toggle{
  display:flex;
  justify-content:center;
  margin: 8px 0 2px 0;
}
.mode-hint{
  text-align:center;
  color: hsl(var(--muted-foreground));
  font-size: 14px;
  margin: 6px 0 24px 0;
}

/* Form card */
div[data-testid="stForm"]{
  background: hsl(var(--card)) !important;
  border: 1px solid hsl(var(--border)) !important;
  border-radius: 20px !important;
  padding: 22px 22px 6px 22px !important;
  box-shadow: var(--shadow-lg) !important;
  margin: 0 auto 24px auto !important;
  max-width: 860px !important;
  width: 100% !important;
}
div[data-testid="stForm"] form{
  padding: 0 !important;
}

/* Field labels */
.field-label{
  display:flex; align-items:center; gap:8px;
  font-size: 14px; font-weight: 800;
  color: hsl(var(--foreground));
  margin: 2px 0 6px 0;
}
.field-label .label-meta{
  font-size: 12px;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  margin-left: 6px;
}
.field-label .label-icon{
  display:inline-flex; align-items:center; justify-content:center;
  width: 20px; height: 20px;
  color: hsl(var(--primary));
}
.field-label .label-icon svg{
  width: 18px; height: 18px;
}

/* Empty state card */
.empty-card{
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 20px;
  box-shadow: var(--shadow-lg);
  padding: 34px 20px;
  text-align: center;
  margin: 24px auto 0 auto;
  max-width: 860px;
}
.empty-icon{
  width: 58px;
  height: 58px;
  margin: 0 auto 14px auto;
  border-radius: 18px;
  background: hsl(var(--secondary));
  display:flex;
  align-items:center;
  justify-content:center;
  color: hsl(var(--muted-foreground));
}
.empty-icon svg{
  width: 26px;
  height: 26px;
}
.empty-title{
  font-weight: 900;
  font-size: 20px;
  color: hsl(var(--foreground));
}
.empty-body{
  margin-top: 6px;
  color: hsl(var(--muted-foreground));
  font-size: 14px;
}

/* Details tips */
.details-link{
  margin-top: 4px;
}
.details-link.inline{
  display: inline-block;
  margin: 0 0 0 6px;
  vertical-align: middle;
}
.details-link.inline summary{
  font-weight: 700;
}
.rule-toggle{
  display: none;
}
.rule-trigger{
  cursor: pointer;
  color: hsl(var(--primary));
  font-weight: 800;
  text-decoration: underline;
  margin-left: 6px;
}
.rule-modal{
  display: none;
  position: fixed;
  inset: 0;
  z-index: 10000;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.rule-backdrop{
  position: absolute;
  inset: 0;
  background: rgba(17, 24, 39, 0.38);
}
.rule-card{
  position: relative;
  z-index: 1;
  max-width: 520px;
  width: 100%;
  background: white;
  border: 1px solid hsl(var(--border));
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: var(--shadow-lg);
}
.rule-card h4{
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 900;
  color: hsl(var(--foreground));
}
.rule-card ul{
  margin: 8px 0 0 18px;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}
.rule-close{
  position: absolute;
  top: 10px;
  right: 12px;
  cursor: pointer;
  font-size: 18px;
  color: hsl(var(--muted-foreground));
}
.rule-toggle:checked + label + .rule-modal{
  display: flex;
}
.details-link summary{
  cursor: pointer;
  color: hsl(var(--primary));
  font-weight: 800;
  list-style: none;
}
.details-link summary .link-like{
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.link-like{
  color: hsl(var(--primary));
  text-decoration: underline;
}
.details-link summary::-webkit-details-marker{
  display:none;
}
.details-box{
  margin-top: 6px;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}


/* ------------------------------
   Tables (we'll render with df.to_html(classes="data-table"))
--------------------------------*/
table.data-table{
  width:100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  overflow: hidden !important;
  border-radius: 16px !important;
  border: 1px solid hsl(var(--border)) !important;
  background: hsl(var(--card)) !important;
}
table.data-table thead th{
  background: hsl(var(--primary)) !important;
  color: hsl(var(--primary-foreground)) !important;
  font-weight: 900 !important;
  padding: 10px 12px !important;
  text-align: left !important;
  border-bottom: 1px solid hsl(var(--border)) !important;
  white-space: nowrap;
}
table.data-table tbody td{
  padding: 10px 12px !important;
  border-top: 1px solid hsl(var(--border)) !important;
  color: hsl(var(--foreground)) !important;
  font-size: 13px !important;
  vertical-align: top !important;
}
table.data-table tbody tr:hover{
  background: hsl(var(--muted) / 0.5) !important;
}
a{
  color: hsl(var(--primary)) !important;
  font-weight: 900 !important;
  text-decoration: underline !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# Background decor layer (like your React Index.tsx)
st.markdown(
    """
<div class="bg-decor">
  <div class="blob b1"></div>
  <div class="blob b2"></div>
  <div class="blob b3"></div>
  <div class="grid-overlay"></div>
</div>
""",
    unsafe_allow_html=True,
)

# Hero (like HeroSection.tsx)
st.markdown(
    """
<div class="hero-wrap">
  <div class="hero-icon">
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M4 20V10M10 20V4M16 20V14M3 20H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
  </div>
  <h1 class="hero-h1">
    <span class="gradient-text">Bayut</span> <span>Competitor Gap Analysis</span>
  </h1>
  <p class="hero-sub">
    Identifies missing sections and incomplete coverage against competitor articles.
  </p>
  <div class="hero-badges">
    <span class="hero-badge">
      <span class="icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <circle cx="11" cy="11" r="6" stroke="currentColor" stroke-width="2"/>
          <path d="M20 20l-3.6-3.6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          <path d="M8 12l2-2 2 2 3-3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span class="label">SEO Analysis</span>
    </span>
    <span class="hero-badge">
      <span class="icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          <path d="M14 2v6h6" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
          <path d="M9 13l2 2 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span class="label">Content Quality</span>
    </span>
    <span class="hero-badge">
      <span class="icon">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="3" y="5" width="10" height="10" rx="2" stroke="currentColor" stroke-width="2"/>
          <rect x="11" y="9" width="10" height="10" rx="2" stroke="currentColor" stroke-width="2"/>
          <path d="M17.5 16.5L21 20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </span>
      <span class="label">Topic Gaps</span>
    </span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# =====================================================
# FETCH (BEST-EFFORT; SKIP PROTECTED/UNFETCHABLE URLS)
# =====================================================
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

IGNORE_TAGS = {"nav", "footer", "header", "aside", "script", "style", "noscript"}
LIST_TAGS = {"ul", "ol", "li", "dl", "dt", "dd"}
NONCONTENT_TOKENS = {
    "toc",
    "table-of-contents",
    "breadcrumb",
    "breadcrumbs",
    "post_meta",
    "meta",
    "related",
    "recommend",
    "recommended",
    "share",
    "social",
    "newsletter",
    "subscribe",
    "signup",
    "form",
    "sidebar",
    "widget",
    "author",
    "comments",
    "listing",
    "listings",
    "property-slider",
    "carousel",
    "swiper",
    "gallery",
    "slider",
    "sponsored",
    "promo",
    "advert",
}

CONTENT_CLASS_HINTS = {
    "entry-content",
    "post-content",
    "article-content",
    "article-body",
    "post-body",
    "blog-content",
    "content-body",
    "blog_post_container",
}


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def looks_blocked(text: str) -> bool:
    t = (text or "").lower()
    return any(x in t for x in [
        "just a moment", "checking your browser", "verify you are human",
        "cloudflare", "access denied", "captcha", "forbidden", "service unavailable"
    ])


@dataclass
class FetchResult:
    ok: bool
    source: Optional[str]
    status: Optional[int]
    html: str
    text: str
    reason: Optional[str]


class FetchAgent:
    """
    Deterministic resolver:
    - direct HTML
    - optional JS render (Playwright)
    - Jina reader
    - Textise
    If all fail => app forces manual paste (hard gate).
    """

    def __init__(self, default_headers: dict, ignore_tags: set, clean_fn, looks_blocked_fn):
        self.default_headers = default_headers
        self.ignore_tags = ignore_tags
        self.clean = clean_fn
        self.looks_blocked = looks_blocked_fn

        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
        ]

    def _http_get(self, url: str, timeout: int = 25, tries: int = 3) -> Tuple[int, str]:
        last_code, last_text = 0, ""
        for i in range(tries):
            headers = dict(self.default_headers)
            headers["User-Agent"] = random.choice(self.user_agents)
            try:
                r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                last_code, last_text = r.status_code, (r.text or "")

                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(1.2 * (i + 1))
                    continue

                return last_code, last_text
            except Exception as e:
                last_code, last_text = 0, str(e)
                time.sleep(1.2 * (i + 1))
        return last_code, last_text

    def _jina_url(self, url: str) -> str:
        if url.startswith("https://"):
            return "https://r.jina.ai/https://" + url[len("https://"):]
        if url.startswith("http://"):
            return "https://r.jina.ai/http://" + url[len("http://"):]
        return "https://r.jina.ai/https://" + url

    def _textise_url(self, url: str) -> str:
        return f"https://textise.org/showtext.aspx?strURL={quote_plus(url)}"

    def _validate_text(self, text: str, min_len: int) -> bool:
        t = self.clean(text)
        if len(t) < min_len:
            return False
        if self.looks_blocked(t):
            return False
        return True

    def _extract_article_text_from_html(self, html: str) -> str:
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        for t in soup.find_all(list(self.ignore_tags)):
            t.decompose()

        # Remove recurring non-content wrappers before extracting text.
        for el in list(soup.find_all(True)):
            attrs = getattr(el, "attrs", None)
            if not isinstance(attrs, dict):
                continue
            cls_raw = attrs.get("class", [])
            if isinstance(cls_raw, (list, tuple, set)):
                cls = " ".join(str(x) for x in cls_raw if x is not None).lower()
            else:
                cls = str(cls_raw or "").lower()
            el_id = str(attrs.get("id", "") or "").lower()
            if any(tok in cls or tok in el_id for tok in NONCONTENT_TOKENS):
                el.decompose()

        candidate_roots = [
            soup.find(attrs={"itemprop": re.compile(r"articleBody", re.I)}),
            soup.find("article"),
            soup.find("main"),
            soup.body,
            soup,
        ]
        candidates: List[Tuple[int, str]] = []
        seen_roots = set()

        for root in candidate_roots:
            if root is None:
                continue
            rid = id(root)
            if rid in seen_roots:
                continue
            seen_roots.add(rid)

            chunks = []
            seen_chunks = set()
            for tag in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "dt", "dd"]):
                txt = self.clean(tag.get_text(" "))
                if not txt or len(txt) < 4:
                    continue
                nk = norm_header(txt)
                if not nk or nk in seen_chunks:
                    continue
                seen_chunks.add(nk)
                chunks.append(txt)

            text = self.clean(" ".join(chunks)) if chunks else self.clean(root.get_text(" "))
            if not text:
                continue
            word_count = len(re.findall(r"\b\w+\b", text))
            heading_count = len(root.find_all(["h2", "h3", "h4"]))
            score = word_count + (14 * heading_count)
            candidates.append((score, text))

        if not candidates:
            return ""
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _fetch_playwright_html(self, url: str, timeout_ms: int = 25000) -> Tuple[bool, str]:
        if not PLAYWRIGHT_OK:
            return False, ""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
                ctx = browser.new_context(user_agent=random.choice(self.user_agents))
                page = ctx.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(1400)
                html = page.content()
                browser.close()
            return True, html
        except Exception:
            return False, ""

    def resolve(self, url: str) -> FetchResult:
        url = (url or "").strip()
        if not url:
            return FetchResult(False, None, None, "", "", "empty_url")

        html_fallback = ""
        last_status = None
        candidates = []

        def add_candidate(source: str, status: int, html_doc: str, text_doc: str, min_len: int):
            txt = self.clean(text_doc or "")
            if not txt:
                return
            if self.looks_blocked(txt):
                return
            if len(txt) < min_len:
                return
            candidates.append({
                "source": source,
                "status": status,
                "html": html_doc or "",
                "text": txt,
            })

        # 1) direct HTML
        code, html = self._http_get(url)
        last_status = code or last_status
        if code == 200 and html:
            text = self._extract_article_text_from_html(html)
            add_candidate("direct", code, html, text, min_len=320)
            html_fallback = html or html_fallback

        # 2) JS-rendered HTML
        ok, html2 = self._fetch_playwright_html(url)
        if ok and html2:
            text2 = self._extract_article_text_from_html(html2)
            add_candidate("playwright", 200, html2, text2, min_len=320)
            html_fallback = html2 or html_fallback

        # 3) Jina reader
        jurl = self._jina_url(url)
        code3, txt3 = self._http_get(jurl)
        last_status = code3 or last_status
        if code3 == 200 and txt3:
            text3 = self.clean(txt3)
            add_candidate("jina", code3, html_fallback, text3, min_len=300)

        # 4) Textise
        turl = self._textise_url(url)
        code4, html4 = self._http_get(turl)
        last_status = code4 or last_status
        if code4 == 200 and html4:
            soup = BeautifulSoup(html4, "html.parser")
            text4 = self.clean(soup.get_text(" "))
            html_out = html4 or html_fallback
            add_candidate("textise", code4, html_out, text4, min_len=260)

        if candidates:
            source_priority = {"playwright": 4, "direct": 3, "jina": 2, "textise": 1}
            best = max(
                candidates,
                key=lambda c: (len(c.get("text", "")), source_priority.get(c.get("source", ""), 0)),
            )
            return FetchResult(
                True,
                best.get("source"),
                best.get("status"),
                best.get("html", ""),
                best.get("text", ""),
                None,
            )

        return FetchResult(False, None, last_status, "", "", "blocked_or_no_content")


agent = FetchAgent(
    default_headers=DEFAULT_HEADERS,
    ignore_tags=IGNORE_TAGS,
    clean_fn=clean,
    looks_blocked_fn=looks_blocked,
)


def _safe_key(prefix: str, url: str) -> str:
    h = hashlib.md5((url or "").encode("utf-8")).hexdigest()
    return f"{prefix}__{h}"


def resolve_all_or_require_manual(agent: FetchAgent, urls: List[str], st_key_prefix: str) -> Dict[str, FetchResult]:
    _ = st_key_prefix  # kept for backward compatibility with existing call sites
    results: Dict[str, FetchResult] = {}

    for u in urls:
        r = agent.resolve(u)
        results[u] = r
        time.sleep(0.25)
    return results

def split_fetch_results(urls: List[str], fr_map: Dict[str, FetchResult]) -> Tuple[List[str], List[str]]:
    ok_urls: List[str] = []
    failed_urls: List[str] = []
    for u in urls:
        fr = fr_map.get(u)
        if fr and fr.ok:
            ok_urls.append(u)
        else:
            failed_urls.append(u)
    return ok_urls, failed_urls

def fetch_failure_label(fr: Optional[FetchResult]) -> str:
    if fr is None:
        return "unfetchable"
    reason = (fr.reason or "unfetchable").replace("_", " ")
    if fr.status:
        return f"{reason} (HTTP {fr.status})"
    return reason
# =====================================================
# HEADING TREE + FILTERS
# =====================================================
NOISE_PATTERNS = [
    r"\blooking to rent\b", r"\blooking to buy\b", r"\bexplore all available\b", r"\bview all\b",
    r"\bfind (a|an) (home|property|apartment|villa)\b", r"\bbrowse\b", r"\bsearch\b",
    r"\bproperties for (rent|sale)\b", r"\bavailable (rental|properties)\b", r"\bget in touch\b",
    r"\bcontact (us|agent)\b", r"\bcall (us|now)\b", r"\bwhatsapp\b", r"\benquire\b",
    r"\binquire\b", r"\bbook a viewing\b",
    r"\bshare\b", r"\bshare this\b", r"\bfollow us\b", r"\blike\b", r"\bsubscribe\b",
    r"\bnewsletter\b", r"\bmailing list\b", r"\bjoin (our|the) (email )?list\b",
    r"\bemail updates\b", r"\bstay updated\b", r"\bsign up\b", r"\blogin\b", r"\bregister\b",
    r"\brelated (posts|articles)\b", r"\byou may also like\b", r"\brecommended\b",
    r"\bpopular posts\b", r"\bmore articles\b", r"\blatest (blogs|blog|podcasts|podcast|insights)\b",
    r"\breal estate insights\b",
    r"\btable of contents\b", r"\bcontents\b", r"\bback to top\b", r"\bread more\b",
    r"\bnext\b", r"\bprevious\b", r"\bcomments\b",
    r"\bplease stand by\b", r"\bloading\b", r"\bjust a moment\b",
]

GENERIC_SECTION_HEADERS = {"introduction", "overview"}

STOP = {
    "the","and","for","with","that","this","from","you","your","are","was","were","will","have","has","had",
    "but","not","can","may","more","most","into","than","then","they","them","their","our","out","about",
    "also","over","under","between","within","near","where","when","what","why","how","who","which",
    "a","an","to","of","in","on","at","as","is","it","be","or","by","we","i","us"
}

GENERIC_STOP = {
    "dubai","uae","business","bay","community","area","living","pros","cons",
    "property","properties","rent","sale","apartments","villas","guide"
}

# Balanced defaults: catch more genuine gaps while still filtering obvious noise.
HIGH_PRECISION_MODE = True
MISSING_HEADER_MIN_TEXT_COVERAGE = 0.66
MISSING_SUBTOPIC_MIN_TEXT_COVERAGE = 0.62
MISSING_FAQ_MIN_TEXT_COVERAGE = 0.58
SINGLE_FAQ_SHOW_MAX_TOPIC_COVERAGE = 0.50
HEADER_MATCH_MIN_SCORE = 0.69
SIMILAR_HEADER_MATCH_FALLBACK = 0.62
MAX_CONTENT_GAP_ITEMS = 4

def norm_header(h: str) -> str:
    h = clean(h).lower()
    h = re.sub(r"[^a-z0-9\s]", "", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h

def _stem_token(tok: str) -> str:
    t = clean(tok).lower()
    if len(t) > 5 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 3 and t.endswith("s"):
        return t[:-1]
    return t

def _tokenize_norm_words(text: str) -> List[str]:
    return [_stem_token(t) for t in re.findall(r"[a-z0-9]+", norm_header(text))]

HEADER_GENERIC_TOKENS = {
    "section", "topic", "topics", "detail", "details", "overview",
    "introduction", "intro", "guide", "key", "takeaway", "takeaways",
    "information", "info", "top", "best", "popular", "main", "latest",
}

SUBTOPIC_TOKEN_ALIASES = {
    "ticket": {"ticket", "tickets", "entry", "entries", "admission", "price", "pricing", "cost", "fee", "fees"},
    "timing": {"timing", "timings", "time", "times", "hour", "hours", "schedule", "opening", "closing"},
    "location": {"location", "locations", "locat", "address", "where", "venue", "map"},
}

TOPIC_TOKEN_ALIASES = {
    "place": {"place", "places", "venue", "venues", "spot", "spots", "destination", "destinations", "location", "locations"},
    "event": {"event", "events", "celebrate", "celebration", "festival", "festivals", "activity", "activities", "entertainment", "happening", "happenings"},
    "tip": {"tip", "tips", "practical", "advice", "suggestion", "suggestions"},
    "pros": {"pro", "pros", "advantage", "advantages", "benefit", "benefits", "positive", "positives"},
    "cons": {"con", "cons", "disadvantage", "disadvantages", "challenge", "challenges", "drawback", "drawbacks", "consider", "considerations"},
}

LOW_SIGNAL_SUBTOPICS = {
    "location", "contact", "contacts", "phone", "telephone", "website", "web site",
    "address", "map", "directions",
}

FAQ_FILLER_TOKENS = {
    "faq", "faqs", "question", "questions", "attend", "attendance", "visitor", "visitors",
    "visit", "visiting",
}

HEADER_OPPOSITE_GROUPS = [
    (
        {"pro", "pros", "advantage", "advantages", "benefit", "benefits", "positive", "positives"},
        {"con", "cons", "disadvantage", "disadvantages", "challenge", "challenges", "drawback", "drawbacks", "negative", "negatives"},
    )
]

def _canonical_topic_token(tok: str) -> str:
    stem = _stem_token(tok)
    for key, vals in TOPIC_TOKEN_ALIASES.items():
        bucket = {_stem_token(key)} | {_stem_token(v) for v in vals}
        if stem in bucket:
            return _stem_token(key)
    return stem

def _token_aliases(tok: str) -> set:
    stem = _stem_token(tok)
    aliases = {stem}
    for key, vals in TOPIC_TOKEN_ALIASES.items():
        bucket = {_stem_token(key)} | {_stem_token(v) for v in vals}
        if stem in bucket:
            aliases |= bucket
            break
    for key, vals in SUBTOPIC_TOKEN_ALIASES.items():
        bucket = {_stem_token(key)} | {_stem_token(v) for v in vals}
        if stem in bucket:
            aliases |= bucket
            break
    return aliases

def _header_has_any_marker(text: str, words: set) -> bool:
    toks = set(_tokenize_norm_words(text or ""))
    if not toks:
        return False
    word_stems = {_stem_token(w) for w in words}
    return bool(toks & word_stems)

def _header_core_tokens(text: str) -> List[str]:
    out = []
    for tok in _tokenize_norm_words(text):
        canon = _canonical_topic_token(tok)
        if not canon or len(canon) < 3:
            continue
        if canon in STOP or canon in HEADER_GENERIC_TOKENS:
            continue
        out.append(canon)
    return out

def _faq_core_tokens(text: str) -> List[str]:
    out = []
    for tok in _tokenize_norm_words(normalize_question(text)):
        if not tok or len(tok) < 3:
            continue
        if tok in STOP or tok in FAQ_FILLER_TOKENS:
            continue
        out.append(tok)
    return out

def _subtopic_covered_in_text(subtopic: str, bayut_text: str) -> bool:
    b_text = clean(bayut_text or "")
    if not b_text:
        return False

    sub_n = norm_header(subtopic)
    text_n = norm_header(b_text)
    if sub_n and sub_n in text_n:
        return True

    sub_tokens = _header_core_tokens(subtopic)
    if not sub_tokens:
        return False

    text_tokens = set(_tokenize_norm_words(b_text))
    if not text_tokens:
        return False

    def token_hit(tok: str) -> bool:
        return bool(text_tokens & _token_aliases(tok))

    hits = sum(1 for tok in sub_tokens if token_hit(tok))
    if len(sub_tokens) <= 2:
        return hits >= 1
    return hits >= 2

def _topic_coverage_ratio(topic: str, text: str) -> float:
    topic_tokens = _header_core_tokens(topic)
    if not topic_tokens:
        return 0.0
    text_tokens = set(_tokenize_norm_words(text or ""))
    if not text_tokens:
        return 0.0
    hits = 0
    for tok in topic_tokens:
        if text_tokens & _token_aliases(tok):
            hits += 1
    return hits / max(len(topic_tokens), 1)

def _is_low_signal_subtopic(header: str) -> bool:
    hn = norm_header(header or "")
    if not hn:
        return True
    if hn in LOW_SIGNAL_SUBTOPICS:
        return True
    words = hn.split()
    if len(words) == 1 and words[0] in {"location", "contact", "address", "map", "website", "phone"}:
        return True
    return False

def _topic_is_covered(
    topic: str,
    bayut_sections: List[dict],
    bayut_text: str,
    min_header_score: float = 0.73,
    min_text_coverage: float = 0.90,
) -> bool:
    t = clean(topic or "")
    if not t:
        return True

    best_header = 0.0
    for sec in bayut_sections or []:
        h = clean(sec.get("header", ""))
        if not h:
            continue
        best_header = max(best_header, header_similarity(t, h))
    if best_header >= min_header_score:
        return True

    text_n = norm_header(bayut_text or "")
    topic_n = norm_header(t)
    if topic_n and len(topic_n) >= 14 and topic_n in text_n:
        return True

    coverage = _topic_coverage_ratio(t, bayut_text)
    toks = _header_core_tokens(t)
    if not toks:
        return False
    if len(toks) <= 2:
        return coverage >= 1.0
    return coverage >= min_text_coverage

def _coverage_corpus(fr: FetchResult, nodes: List[dict]) -> str:
    parts = []
    if fr and fr.text:
        parts.append(fr.text)
    for x in flatten(nodes or []):
        h = clean(x.get("header", ""))
        c = clean(x.get("content", ""))
        if h:
            parts.append(h)
        if c:
            parts.append(c)
    return clean(" ".join(parts))

def header_is_faq(header: str) -> bool:
    nh = norm_header(header)
    if not nh:
        return False
    if nh in {"faq","faqs","frequently asked questions","frequently asked question"}:
        return True
    if "faq" in nh:
        return True
    if "frequently asked" in nh:
        return True
    return False

def is_noise_header(h: str) -> bool:
    s = clean(h)
    if not s:
        return True
    if header_is_faq(s):
        return False
    hn = norm_header(s)
    if hn in GENERIC_SECTION_HEADERS:
        return True
    if len(hn) < 4:
        return True
    if len(s) > 95:
        return True
    if sum(1 for c in s if c.isalnum()) / max(len(s), 1) < 0.6:
        return True
    for pat in NOISE_PATTERNS:
        if re.search(pat, hn):
            return True
    return False

def level_of(tag_name: str) -> int:
    try:
        return int(tag_name[1])
    except Exception:
        return 9

def build_tree_from_html(html: str) -> List[dict]:
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()

    root = soup.find("article") or soup
    headings = root.find_all(["h1", "h2", "h3", "h4"])

    nodes: List[dict] = []
    stack: List[dict] = []

    def pop_to_level(lvl: int):
        while stack and stack[-1]["level"] >= lvl:
            stack.pop()

    def add_node(node: dict):
        if stack:
            stack[-1]["children"].append(node)
        else:
            nodes.append(node)
        stack.append(node)

    for h in headings:
        header = clean(h.get_text(" "))
        if not header or len(header) < 3:
            continue
        if is_noise_header(header):
            continue

        lvl = level_of(h.name)
        pop_to_level(lvl)

        node = {"level": lvl, "header": header, "content": "", "children": []}
        add_node(node)

        content_parts = []
        for sib in h.find_all_next():
            if sib == h:
                continue
            if getattr(sib, "name", None) in ["h1", "h2", "h3", "h4"]:
                break
            if getattr(sib, "name", None) in ["p", "li"]:
                txt = clean(sib.get_text(" "))
                if txt:
                    content_parts.append(txt)

        node["content"] = clean(" ".join(content_parts))

    return nodes

def build_tree_from_reader_text(text: str) -> List[dict]:
    lines = [l.rstrip() for l in (text or "").splitlines()]
    nodes: List[dict] = []
    stack: List[dict] = []

    def md_level(line: str):
        m = re.match(r"^(#{1,4})\s+(.*)$", line.strip())
        if not m:
            return None
        lvl = len(m.group(1))
        header = clean(m.group(2))
        return lvl, header

    def pop_to_level(lvl: int):
        while stack and stack[-1]["level"] >= lvl:
            stack.pop()

    def add_node(node: dict):
        if stack:
            stack[-1]["children"].append(node)
        else:
            nodes.append(node)
        stack.append(node)

    current = None
    for line in lines:
        s = line.strip()
        if not s:
            continue

        ml = md_level(s)
        if ml:
            lvl, header = ml
            if is_noise_header(header):
                current = None
                continue

            pop_to_level(lvl)
            node = {"level": lvl, "header": header, "content": "", "children": []}
            add_node(node)
            current = node
        else:
            if current:
                current["content"] += " " + s

    def walk(n: dict) -> dict:
        n["content"] = clean(n["content"])
        n["children"] = [walk(c) for c in n["children"]]
        return n

    return [walk(n) for n in nodes]

def build_tree_from_plain_text_heuristic(text: str) -> List[dict]:
    raw = (text or "").replace("\r", "")
    lines = [clean(l) for l in raw.split("\n")]
    lines = [l for l in lines if l]

    def looks_like_heading(line: str) -> bool:
        if len(line) < 5 or len(line) > 80:
            return False
        if line.endswith("."):
            return False
        if is_noise_header(line):
            return False
        words = line.split()
        if len(words) < 2 or len(words) > 12:
            return False
        caps_ratio = sum(1 for w in words if w[:1].isupper()) / max(len(words), 1)
        allcaps_ratio = sum(1 for c in line if c.isupper()) / max(sum(1 for c in line if c.isalpha()), 1)
        return (caps_ratio >= 0.6) or (allcaps_ratio >= 0.5)

    nodes: List[dict] = []
    current = None

    for line in lines:
        if looks_like_heading(line):
            current = {"level": 2, "header": line, "content": "", "children": []}
            nodes.append(current)
        else:
            if current is None:
                current = {"level": 2, "header": "Overview", "content": "", "children": []}
                nodes.append(current)
            current["content"] = clean(current["content"] + " " + line)

    return nodes

def get_tree_from_fetchresult(fr: FetchResult) -> dict:
    if not fr.ok:
        return {"ok": False, "source": None, "nodes": [], "status": fr.status}

    txt = fr.text or ""
    maybe_html = ("<html" in txt.lower()) or ("<article" in txt.lower()) or ("<h1" in txt.lower()) or ("<h2" in txt.lower())

    if fr.html:
        nodes = build_tree_from_html(fr.html)
    elif fr.source == "manual" and maybe_html:
        nodes = build_tree_from_html(txt)
    else:
        nodes = build_tree_from_reader_text(txt)
        if not nodes:
            nodes = build_tree_from_plain_text_heuristic(txt)

    return {"ok": True, "source": fr.source, "nodes": nodes, "status": fr.status}

def ensure_headings_or_require_repaste(urls: List[str], fr_map: Dict[str, FetchResult], st_key_prefix: str) -> Dict[str, dict]:
    tree_map: Dict[str, dict] = {}
    bad: List[str] = []

    for u in urls:
        tr = get_tree_from_fetchresult(fr_map[u])
        tree_map[u] = tr
        if not tr.get("nodes"):
            bad.append(u)

    if not bad:
        return tree_map

    st.error("Some URLs were fetched, but headings could not be extracted. Paste readable HTML (preferred) or clearly structured text for EACH URL below to continue.")

    for u in bad:
        with st.expander(f"Headings extraction required: {u}", expanded=True):
            repaste = st.text_area(
                "Paste readable HTML (preferred) OR structured text with headings:",
                key=_safe_key(st_key_prefix + "__repaste", u),
                height=240,
            )
            if repaste and len(repaste.strip()) > 400:
                fr_map[u] = FetchResult(True, "manual", 200, repaste.strip(), repaste.strip(), None)

    still_bad = []
    for u in bad:
        tr = get_tree_from_fetchresult(fr_map[u])
        tree_map[u] = tr
        if not tr.get("nodes"):
            still_bad.append(u)

    if still_bad:
        st.stop()

    return tree_map


# =====================================================
# HELPERS
# =====================================================
def site_name(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        base = host.split(":")[0]
        name = base.split(".")[0]
        return name[:1].upper() + name[1:]
    except Exception:
        return "Source"

def source_link(url: str) -> str:
    n = site_name(url)
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{n}</a>'

def flatten(nodes: List[dict]) -> List[dict]:
    out = []
    def walk(n: dict, parent=None):
        out.append({
            "level": n["level"],
            "header": n.get("header",""),
            "content": n.get("content", ""),
            "parent": parent,
            "children": n.get("children", [])
        })
        for c in n.get("children", []):
            walk(c, n)
    for n in nodes:
        walk(n, None)
    return out

def strip_label(h: str) -> str:
    return clean(re.sub(r"\s*:\s*$", "", (h or "").strip()))

def format_gap_list(items: List[str], limit: int = 6) -> str:
    cleaned = []
    seen = set()
    skip = {"other","other topics","other faq topics","faq topics","other faq topic","other faq","general","misc","miscellaneous"}
    for item in items or []:
        it = clean(item)
        if not it:
            continue
        k = norm_header(it)
        if k in skip:
            continue
        if k in seen:
            continue
        seen.add(k)
        cleaned.append(it)
    if not cleaned:
        return ""
    if limit <= 0 or len(cleaned) <= limit:
        return ", ".join(cleaned)
    return ", ".join(cleaned[:limit]) + f", and {len(cleaned) - limit} more"

def headings_blob(nodes: List[dict]) -> str:
    hs = []
    for x in flatten(nodes):
        h = clean(x.get("header", ""))
        if h and not is_noise_header(h):
            hs.append(h)
    return clean(" | ".join(hs))

def get_first_h1(nodes: List[dict]) -> str:
    for x in flatten(nodes):
        if x.get("level") == 1:
            h = clean(x.get("header", ""))
            if h:
                return h
    for x in flatten(nodes):
        if x.get("level") == 2:
            h = clean(x.get("header", ""))
            if h:
                return h
    return "Not available"
# =====================================================
# STRICT FAQ DETECTION (REAL FAQ ONLY)
# =====================================================
FAQ_TITLES = {"faq","faqs","frequently asked questions","frequently asked question"}
MONTH_NAME_TO_NUM = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

def _looks_like_question(s: str) -> bool:
    s = clean(s)
    if not s or len(s) < 6:
        return False
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = clean(s)
    if not s:
        return False
    s_low = s.lower()
    if re.search(r"\b(looking to (rent|buy)|request a call|contact us|get in touch|subscribe|newsletter)\b", s_low):
        return False
    if "?" in s:
        return True
    if re.match(r"^(what|where|when|why|how|who|which|can|is|are|do|does|did|should)\b", s_low):
        return True
    if any(p in s_low for p in ["what is", "how to", "is it", "are there", "can i", "should i"]):
        return True
    return False

def normalize_question(q: str) -> str:
    q = clean(q or "")
    q = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", q)
    q = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", q)
    q = re.sub(r"^\s*\d+[\.\)]\s*", "", q)
    q = re.sub(r"^\s*[-•]\s*", "", q)
    return q.strip()

def _has_faq_schema(html: str) -> bool:
    if not html:
        return False
    try:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
        for s in scripts:
            raw = (s.string or s.get_text(" ") or "").strip()
            if not raw:
                continue
            try:
                j = json.loads(raw)
            except Exception:
                continue

            def walk(x):
                if isinstance(x, dict):
                    t = x.get("@type") or x.get("type")
                    if isinstance(t, str) and t.lower() == "faqpage":
                        return True
                    if isinstance(t, list) and any(str(z).lower() == "faqpage" for z in t):
                        return True
                    for v in x.values():
                        if walk(v):
                            return True
                elif isinstance(x, list):
                    for v in x:
                        if walk(v):
                            return True
                return False

            if walk(j):
                return True
    except Exception:
        return False
    return False

def _faq_questions_from_schema(html: str) -> List[str]:
    if not html:
        return []
    qs: List[str] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
        for s in scripts:
            raw = (s.string or s.get_text(" ") or "").strip()
            if not raw:
                continue
            try:
                j = json.loads(raw)
            except Exception:
                continue

            def add_q(q: str):
                qn = normalize_question(q)
                if not qn or len(qn) < 6 or len(qn) > 180:
                    return
                qs.append(qn)

            def walk(x):
                if isinstance(x, dict):
                    t = x.get("@type") or x.get("type")
                    t_list = []
                    if isinstance(t, list):
                        t_list = [str(z).lower() for z in t]
                    elif isinstance(t, str):
                        t_list = [t.lower()]

                    if any("question" == z or z.endswith("question") for z in t_list):
                        name = x.get("name") or x.get("text") or ""
                        if name:
                            add_q(name)

                    for v in x.values():
                        walk(v)
                elif isinstance(x, list):
                    for v in x:
                        walk(v)

            walk(j)
    except Exception:
        return []

    seen = set()
    out = []
    for q in qs:
        k = norm_header(q)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out

def _faq_questions_from_html(html: str) -> List[str]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()

    qs: List[str] = []
    qs.extend(_faq_questions_from_schema(html))

    candidates = []
    for tag in soup.find_all(True):
        attrs = getattr(tag, "attrs", None)
        if not isinstance(attrs, dict):
            continue
        cls_raw = attrs.get("class", [])
        if isinstance(cls_raw, (list, tuple, set)):
            cls_attr = " ".join(str(x) for x in cls_raw if x is not None).lower()
        else:
            cls_attr = str(cls_raw or "").lower()
        id_attr = str(attrs.get("id", "") or "").lower()
        if re.search(r"\bfaq\b|\bfaqs\b|\baccordion\b|\bquestions\b", id_attr + " " + cls_attr):
            candidates.append(tag)

    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if header_is_faq(h.get_text(" ")):
            candidates.append(h.parent or h)

    for c in candidates[:10]:
        for el in c.find_all(["summary", "button", "h3", "h4", "h5", "strong", "p", "li", "dt"]):
            txt = clean(el.get_text(" "))
            if not txt or len(txt) < 6 or len(txt) > 180:
                continue
            if _looks_like_question(txt):
                qs.append(normalize_question(txt))

    seen = set()
    out = []
    for q in qs:
        k = norm_header(q)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out

def _faq_pairs_from_schema(html: str) -> List[dict]:
    if not html:
        return []
    out: List[dict] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
        for s in scripts:
            raw = (s.string or s.get_text(" ") or "").strip()
            if not raw:
                continue
            try:
                j = json.loads(raw)
            except Exception:
                continue

            def _add_pair(q: str, a: str = ""):
                qn = normalize_question(q)
                an = clean(re.sub(r"<[^>]+>", " ", str(a or "")))
                if not qn or len(qn) < 6 or len(qn) > 180:
                    return
                out.append({"question": qn, "answer": an})

            def _walk(x):
                if isinstance(x, dict):
                    t = x.get("@type") or x.get("type")
                    t_list = []
                    if isinstance(t, list):
                        t_list = [str(z).lower() for z in t]
                    elif isinstance(t, str):
                        t_list = [t.lower()]

                    if any("question" == z or z.endswith("question") for z in t_list):
                        q = x.get("name") or x.get("text") or ""
                        a = ""
                        ans_obj = x.get("acceptedAnswer") or x.get("answer") or {}
                        if isinstance(ans_obj, dict):
                            a = ans_obj.get("text") or ans_obj.get("name") or ""
                        elif isinstance(ans_obj, str):
                            a = ans_obj
                        if q:
                            _add_pair(q, a)
                    for v in x.values():
                        _walk(v)
                elif isinstance(x, list):
                    for v in x:
                        _walk(v)

            _walk(j)
    except Exception:
        return []

    dedup: Dict[str, dict] = {}
    for p in out:
        k = norm_header(p.get("question", ""))
        if not k:
            continue
        if k not in dedup:
            dedup[k] = p
            continue
        # Prefer richer answer text when duplicate questions appear.
        if len(clean(p.get("answer", ""))) > len(clean(dedup[k].get("answer", ""))):
            dedup[k] = p
    return list(dedup.values())

def _faq_pairs_from_html(html: str) -> List[dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()

    pairs: List[dict] = []
    pairs.extend(_faq_pairs_from_schema(html))

    candidates = []
    for tag in soup.find_all(True):
        attrs = getattr(tag, "attrs", None)
        if not isinstance(attrs, dict):
            continue
        cls_raw = attrs.get("class", [])
        if isinstance(cls_raw, (list, tuple, set)):
            cls_attr = " ".join(str(x) for x in cls_raw if x is not None).lower()
        else:
            cls_attr = str(cls_raw or "").lower()
        id_attr = str(attrs.get("id", "") or "").lower()
        if re.search(r"\bfaq\b|\bfaqs\b|\baccordion\b|\bquestions\b", id_attr + " " + cls_attr):
            candidates.append(tag)

    for h in soup.find_all(["h1", "h2", "h3", "h4"]):
        if header_is_faq(h.get_text(" ")):
            candidates.append(h.parent or h)

    for c in candidates[:10]:
        pending_q = ""
        pending_idx = -1
        for el in c.find_all(["summary", "button", "h3", "h4", "h5", "strong", "p", "li", "dt", "dd"]):
            txt = clean(el.get_text(" "))
            if not txt or len(txt) < 6:
                continue
            if len(txt) > 320:
                continue
            if _looks_like_question(txt):
                qn = normalize_question(txt)
                if qn:
                    pairs.append({"question": qn, "answer": ""})
                    pending_q = qn
                    pending_idx = len(pairs) - 1
                continue
            if pending_q and pending_idx >= 0 and pending_idx < len(pairs):
                # First nearby non-question block after question acts as answer.
                if not pairs[pending_idx].get("answer", ""):
                    pairs[pending_idx]["answer"] = txt

    dedup: Dict[str, dict] = {}
    for p in pairs:
        q = clean(p.get("question", ""))
        if not q:
            continue
        k = norm_header(q)
        if not k:
            continue
        a = clean(p.get("answer", ""))
        if k not in dedup:
            dedup[k] = {"question": q, "answer": a}
            continue
        if len(a) > len(clean(dedup[k].get("answer", ""))):
            dedup[k]["answer"] = a
    return list(dedup.values())

def _faq_heading_nodes(nodes: List[dict]) -> List[dict]:
    out = []
    for x in flatten(nodes):
        if x.get("level") in (2, 3, 4) and header_is_faq(x.get("header", "")):
            out.append(x)
    return out

def _question_heading_children(node: dict) -> List[str]:
    qs = []
    for c in node.get("children", []) or []:
        hdr = clean(c.get("header", ""))
        if hdr and _looks_like_question(hdr):
            qs.append(normalize_question(hdr))
    return qs

def extract_questions_from_node(node: dict) -> List[str]:
    qs: List[str] = []
    qs.extend(_question_heading_children(node))

    def add_from_text_block(txt: str):
        txt = clean(txt or "")
        if not txt:
            return
        chunks = re.split(r"[\n\r]+|(?<=[\.\?\!])\s+", txt)
        for ch in chunks[:80]:
            ch = clean(ch)
            if not ch or len(ch) > 160:
                continue
            if _looks_like_question(ch):
                qs.append(normalize_question(ch))

    if len(qs) < 3:
        add_from_text_block(node.get("content", ""))

    seen = set()
    out = []
    for q in qs:
        k = norm_header(q)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out[:25]

def page_has_real_faq(fr: FetchResult, nodes: List[dict]) -> bool:
    if fr and fr.html:
        if _has_faq_schema(fr.html):
            return True
        if len(_faq_questions_from_html(fr.html)) >= 2:
            return True

    faq_nodes = _faq_heading_nodes(nodes)
    if not faq_nodes:
        return False

    for fn in faq_nodes:
        if len(extract_questions_from_node(fn)) >= 2:
            return True
        txt = clean(fn.get("content", ""))
        if txt and txt.count("?") >= 2:
            return True

    return True

def extract_faq_questions(fr: FetchResult, nodes: List[dict]) -> List[str]:
    qs: List[str] = []
    if fr and fr.html:
        qs.extend(_faq_questions_from_html(fr.html))
    for fn in _faq_heading_nodes(nodes):
        qs.extend(extract_questions_from_node(fn))

    seen = set()
    out = []
    for q in qs:
        k = norm_header(q)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out

def _faq_pairs_from_nodes(nodes: List[dict]) -> List[dict]:
    pairs: List[dict] = []
    for fn in _faq_heading_nodes(nodes):
        for c in fn.get("children", []) or []:
            q = clean(c.get("header", ""))
            if not q or not _looks_like_question(q):
                continue
            a = clean(c.get("content", ""))
            pairs.append({"question": normalize_question(q), "answer": a})
    return pairs

def extract_faq_pairs(fr: FetchResult, nodes: List[dict]) -> List[dict]:
    pairs: List[dict] = []
    if fr and fr.html:
        pairs.extend(_faq_pairs_from_html(fr.html))
    pairs.extend(_faq_pairs_from_nodes(nodes))

    # Backfill questions without answers from question-only extraction.
    q_only = extract_faq_questions(fr, nodes)
    for q in q_only:
        pairs.append({"question": normalize_question(q), "answer": ""})

    dedup: Dict[str, dict] = {}
    for p in pairs:
        q = clean(p.get("question", ""))
        if not q:
            continue
        k = norm_header(q)
        if not k:
            continue
        a = clean(p.get("answer", ""))
        if k not in dedup:
            dedup[k] = {"question": q, "answer": a}
            continue
        if len(a) > len(clean(dedup[k].get("answer", ""))):
            dedup[k]["answer"] = a
    return list(dedup.values())

def faq_topic_from_question(q: str) -> str:
    raw = normalize_question(q)
    if not raw:
        return ""
    topic = re.sub(
        r"^(what|where|when|why|how|who|which|can|is|are|do|does|did|should|could|would|will)\b",
        "",
        raw,
        flags=re.I,
    )
    topic = re.sub(
        r"^(is|are|do|does|did|can|should|could|would|will|has|have|had|there|it|this|that)\b",
        "",
        topic,
        flags=re.I,
    )
    topic = re.sub(r"^\s*(the|a|an)\b", "", topic, flags=re.I).strip()
    topic = re.sub(r"\?$", "", topic).strip()
    if len(topic) < 4:
        topic = raw.strip("?").strip()
    if len(topic) > 140:
        topic = topic[:140].rstrip()
    if not topic:
        return ""
    return topic[:1].upper() + topic[1:]

def faq_topic_covered_in_text(q: str, bayut_text: str) -> bool:
    topic = faq_topic_from_question(q)
    if not topic:
        return False
    cov = _topic_coverage_ratio(topic, bayut_text)
    toks = _header_core_tokens(topic)
    if not toks:
        return False
    if len(toks) <= 2:
        return cov >= 1.0
    return cov >= MISSING_FAQ_MIN_TEXT_COVERAGE

def faq_question_covered_in_text(q: str, bayut_text: str) -> bool:
    qn = normalize_question(q)
    if not qn:
        return False
    qn_norm = norm_header(qn)
    b_norm = norm_header(bayut_text or "")
    if qn_norm and len(qn_norm) >= 16 and qn_norm in b_norm:
        return True

    q_tokens = set(_faq_core_tokens(qn))
    if not q_tokens:
        return False
    b_tokens = set(_tokenize_norm_words(bayut_text or ""))
    if not b_tokens:
        return False

    overlap = len(q_tokens & b_tokens)
    ratio = overlap / max(len(q_tokens), 1)
    if len(q_tokens) <= 2:
        return ratio >= 1.0
    if len(q_tokens) == 3:
        return ratio >= 0.85
    return ratio >= 0.80

def faq_topics_from_questions(questions: List[str], limit: int = 10) -> List[str]:
    out: List[str] = []
    seen = set()
    for q in questions:
        subj = faq_topic_from_question(q)
        if not subj:
            continue
        k = norm_header(subj)
        if k in seen:
            continue
        seen.add(k)
        out.append(subj)
        if len(out) >= limit:
            break
    return out

def faq_questions_equivalent(a: str, b: str) -> bool:
    a_q = normalize_question(a)
    b_q = normalize_question(b)
    if not a_q or not b_q:
        return False

    a_n = norm_header(a_q)
    b_n = norm_header(b_q)
    if a_n == b_n:
        return True

    if a_n and b_n and (a_n in b_n or b_n in a_n):
        if min(len(a_n), len(b_n)) >= 12:
            return True

    a_topic = norm_header(faq_topic_from_question(a_q))
    b_topic = norm_header(faq_topic_from_question(b_q))
    if a_topic and b_topic:
        if a_topic == b_topic:
            return True
        if (a_topic in b_topic or b_topic in a_topic) and min(len(a_topic), len(b_topic)) >= 10:
            return True
        if header_similarity(a_topic, b_topic) >= 0.82:
            return True

    a_tokens = set(_faq_core_tokens(a_q))
    b_tokens = set(_faq_core_tokens(b_q))
    if a_tokens and b_tokens:
        overlap = len(a_tokens & b_tokens)
        small = min(len(a_tokens), len(b_tokens))
        if small >= 2 and overlap / max(small, 1) >= 0.8:
            return True
        jacc = overlap / max(len(a_tokens | b_tokens), 1)
        if overlap >= 2 and jacc >= 0.67:
            return True

    return SequenceMatcher(None, a_n, b_n).ratio() >= 0.90

def faq_questions_related(a: str, b: str) -> bool:
    if faq_questions_equivalent(a, b):
        return True
    a_topic = faq_topic_from_question(a)
    b_topic = faq_topic_from_question(b)
    if a_topic and b_topic and header_similarity(a_topic, b_topic) >= 0.64:
        return True

    a_tokens = set(_faq_core_tokens(a))
    b_tokens = set(_faq_core_tokens(b))
    if not a_tokens or not b_tokens:
        return False

    overlap = a_tokens & b_tokens
    if len(overlap) >= 2:
        return True
    anchor = overlap & {
        "restaurant", "menu", "reservation", "book", "booking",
        "event", "festival", "ticket", "free", "location",
        "date", "time", "year", "global", "village",
    }
    if anchor:
        return True
    return False

def _question_has_date_intent(q: str) -> bool:
    qn = norm_header(normalize_question(q))
    if not qn:
        return False
    return any(tok in qn for tok in ["when", "date", "day", "month", "year", "start", "begin"])

def _extract_date_signatures(text: str) -> set:
    t = clean(text or "").lower()
    if not t:
        return set()
    out = set()
    month_rgx = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

    for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{month_rgx}\s+(\d{{4}})\b", t, flags=re.I):
        day = int(m.group(1))
        mon = MONTH_NAME_TO_NUM.get(m.group(2).lower(), 0)
        year = int(m.group(3))
        if mon and 1 <= day <= 31:
            out.add(f"{year:04d}-{mon:02d}-{day:02d}")

    for m in re.finditer(rf"\b{month_rgx}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:,)?\s+(\d{{4}})\b", t, flags=re.I):
        mon = MONTH_NAME_TO_NUM.get(m.group(1).lower(), 0)
        day = int(m.group(2))
        year = int(m.group(3))
        if mon and 1 <= day <= 31:
            out.add(f"{year:04d}-{mon:02d}-{day:02d}")
    return out

def faq_answers_conflict(question: str, comp_answer: str, bayut_answer: str) -> bool:
    if not _question_has_date_intent(question):
        return False
    c_dates = _extract_date_signatures(comp_answer)
    b_dates = _extract_date_signatures(bayut_answer)
    if c_dates and b_dates and c_dates.isdisjoint(b_dates):
        return True
    return False

def missing_faqs_row(
    bayut_nodes: List[dict],
    bayut_fr: FetchResult,
    comp_nodes: List[dict],
    comp_fr: FetchResult,
    comp_url: str
) -> Optional[dict]:
    def _valid_faq_q(q: str) -> bool:
        qn = normalize_question(q)
        if not qn or len(qn) <= 5:
            return False
        if not _looks_like_question(qn):
            return False
        qn_low = qn.lower()
        if re.search(r"\blooking to (rent|buy)\b|\brequest a call\b|\bcontact us\b", qn_low):
            return False
        return True

    if not page_has_real_faq(comp_fr, comp_nodes):
        return None

    comp_pairs = extract_faq_pairs(comp_fr, comp_nodes)
    comp_pairs = [p for p in comp_pairs if _valid_faq_q(clean(p.get("question", "")))]
    if not comp_pairs:
        return None

    bayut_pairs = extract_faq_pairs(bayut_fr, bayut_nodes) if page_has_real_faq(bayut_fr, bayut_nodes) else []
    bayut_pairs = [p for p in bayut_pairs if _valid_faq_q(clean(p.get("question", "")))]

    missing_qs = []

    for cp in comp_pairs:
        q = clean(cp.get("question", ""))
        if not q:
            continue

        matched = False
        for bp in bayut_pairs:
            bq = clean(bp.get("question", ""))
            if not bq:
                continue
            if faq_questions_equivalent(q, bq):
                matched = True
                break
        if matched:
            continue

        missing_qs.append(q)

    dedup_missing: List[str] = []
    seen = set()
    for q in missing_qs:
        k = norm_header(normalize_question(q))
        if not k or k in seen:
            continue
        seen.add(k)
        dedup_missing.append(q)
    missing_qs = dedup_missing

    if not missing_qs:
        return None

    def as_question_list(items: List[str], label: str = "") -> str:
        cleaned = [clean(i) for i in items if clean(i)]
        if not cleaned:
            return ""
        parts = [f"{idx + 1}-{html_lib.escape(q)}" for idx, q in enumerate(cleaned)]
        body = "<div>" + " ".join(parts) + "</div>"
        if label:
            return f"<div>{html_lib.escape(label)}</div>" + body
        return body

    faq_limit = 4
    shown_qs = missing_qs[:faq_limit]
    desc_parts = []
    if shown_qs:
        desc_parts.append(as_question_list(shown_qs, label="Important missing FAQ questions:"))
    if len(missing_qs) > faq_limit:
        desc_parts.append(f"<div>+{len(missing_qs) - faq_limit} more FAQ gaps</div>")

    return {
        "Headers": "FAQs",
        "Description": "".join(desc_parts).strip(),
        "Source": source_link(comp_url),
    }

def _inline_numbered_from_html_list(html_text: str) -> str:
    if html_text is None:
        return ""
    if not isinstance(html_text, str):
        html_text = str(html_text)
    if html_text.lower() == "nan":
        return ""
    items = re.findall(r"<li>(.*?)</li>", html_text, flags=re.I | re.S)
    if not items:
        return html_text
    cleaned = []
    for it in items:
        txt = clean(html_lib.unescape(re.sub(r"<[^>]+>", "", it)))
        if txt:
            cleaned.append(txt)
    if not cleaned:
        return html_text
    parts = [f"{idx + 1}-{html_lib.escape(q)}" for idx, q in enumerate(cleaned)]
    return "<div>" + " ".join(parts) + "</div>"


# =====================================================
# SECTION EXTRACTION (HEADER-FIRST COMPARISON)
# =====================================================
def section_nodes(nodes: List[dict], levels=(2,3)) -> List[dict]:
    secs = []
    current_h2 = None
    current_h2_is_faq = False
    for x in flatten(nodes):
        lvl = x["level"]
        h = strip_label(x.get("header",""))

        # Keep parent context accurate so FAQ/questions do not leak
        # under the previous non-FAQ H2 (e.g., "Conclusion").
        if lvl == 2:
            if not h or is_noise_header(h):
                current_h2 = None
                current_h2_is_faq = False
            elif header_is_faq(h):
                current_h2 = None
                current_h2_is_faq = True
            else:
                current_h2 = h
                current_h2_is_faq = False

        # Ignore FAQ descendants for section gap comparison.
        if lvl >= 3 and current_h2_is_faq:
            continue

        # Treat question headings as FAQ-like fragments, not structural subtopics.
        if lvl >= 3 and _looks_like_question(h):
            continue

        if not h or is_noise_header(h) or header_is_faq(h):
            continue
        if lvl in levels:
            c = clean(x.get("content",""))
            secs.append({"level": lvl, "header": h, "content": c, "parent_h2": current_h2})

    seen = set()
    out = []
    for s in secs:
        k = norm_header(s["header"])
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out

def header_similarity(a: str, b: str) -> float:
    a_n = norm_header(a)
    b_n = norm_header(b)
    if not a_n or not b_n:
        return 0.0

    a_set = set(a_n.split())
    b_set = set(b_n.split())
    jacc = len(a_set & b_set) / max(len(a_set | b_set), 1) if a_set and b_set else 0.0
    seq = SequenceMatcher(None, a_n, b_n).ratio()
    base = (0.55 * seq) + (0.45 * jacc)

    # Extra semantic tolerance for cosmetic variants:
    # "The Light Village" ~ "About Sharjah Light Village".
    a_core = set(_header_core_tokens(a))
    b_core = set(_header_core_tokens(b))
    if not a_core or not b_core:
        return base

    core_jacc = len(a_core & b_core) / max(len(a_core | b_core), 1)
    core_seq = SequenceMatcher(None, " ".join(sorted(a_core)), " ".join(sorted(b_core))).ratio()
    core_score = (0.60 * core_seq) + (0.40 * core_jacc)

    subset_bonus = 0.0
    smallest = min(len(a_core), len(b_core))
    if 2 <= smallest <= 3 and (a_core.issubset(b_core) or b_core.issubset(a_core)):
        subset_bonus = 0.84

    score = max(base, core_score, subset_bonus)

    # Prevent opposite-polarity headers from being treated as equivalent
    # (e.g., "Advantages" vs "Disadvantages").
    for pos_words, neg_words in HEADER_OPPOSITE_GROUPS:
        a_pos = _header_has_any_marker(a, pos_words)
        a_neg = _header_has_any_marker(a, neg_words)
        b_pos = _header_has_any_marker(b, pos_words)
        b_neg = _header_has_any_marker(b, neg_words)
        if (a_pos and b_neg) or (a_neg and b_pos):
            score *= 0.58
            break

    return score

def find_best_bayut_match(comp_header: str, bayut_sections: List[dict], min_score: float = HEADER_MATCH_MIN_SCORE) -> Optional[dict]:
    best = None
    best_score = 0.0
    for b in bayut_sections:
        sc = header_similarity(comp_header, b["header"])
        if sc > best_score:
            best_score = sc
            best = b
    if best and best_score >= min_score:
        return {"bayut_section": best, "score": best_score}
    if not best:
        return None

    # Smart fallback: allow semantic token overlap when wording differs.
    comp_core = set(_header_core_tokens(comp_header))
    best_core = set(_header_core_tokens(best.get("header", "")))
    if comp_core and best_core:
        overlap = len(comp_core & best_core) / max(min(len(comp_core), len(best_core)), 1)
        if overlap >= 0.67 and best_score >= SIMILAR_HEADER_MATCH_FALLBACK:
            return {"bayut_section": best, "score": best_score}
    return None

def dedupe_rows(rows: List[dict]) -> List[dict]:
    out = []
    seen = set()
    for r in rows:
        hk = norm_header(r.get("Headers", ""))
        sk = norm_header(re.sub(r"<[^>]+>", "", r.get("Source", "")))
        k = hk + "||" + sk
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


# =====================================================
# CONTENT GAP THEMES (NEUTRAL DESCRIPTION)
# =====================================================
def theme_flags(text: str) -> set:
    t = (text or "").lower()
    flags = set()

    def has_any(words: List[str]) -> bool:
        return any(w in t for w in words)

    if has_any(["metro", "public transport", "commute", "connectivity", "access", "highway", "roads", "bus", "train"]):
        flags.add("transport")
    if has_any(["parking", "traffic", "congestion", "rush hour", "gridlock"]):
        flags.add("traffic_parking")
    if has_any(["cost", "price", "pricing", "expensive", "afford", "budget", "rent", "fees", "charges"]):
        flags.add("cost")
    if has_any(["restaurants", "cafes", "nightlife", "vibe", "atmosphere", "social", "entertainment"]):
        flags.add("lifestyle")
    if has_any(["schools", "nursery", "kids", "family", "clinic", "hospital", "supermarket", "groceries", "pharmacy"]):
        flags.add("daily_life")
    if has_any(["safe", "safety", "security", "crime"]):
        flags.add("safety")
    if has_any(["pros", "cons", "advantages", "disadvantages", "weigh", "consider", "should you", "worth it"]):
        flags.add("decision_frame")
    if has_any(["compare", "comparison", "vs ", "versus", "alternative", "similar to"]):
        flags.add("comparison")

    return flags

IMPORTANT_POINT_SIGNAL_MAP = {
    "Location & connectivity": [
        "location", "connectivity", "access", "metro", "public transport", "bus", "road", "highway", "sheikh zayed",
    ],
    "Property types & ownership": [
        "apartment", "villa", "townhouse", "penthouse", "property type", "freehold", "leasehold", "ownership",
    ],
    "Costs & service charges": [
        "cost", "price", "pricing", "expensive", "afford", "budget", "fee", "fees", "service charge", "maintenance",
    ],
    "Amenities & facilities": [
        "amenities", "facility", "facilities", "gym", "pool", "park", "beach", "shopping", "mall", "recreational",
    ],
    "Lifestyle & entertainment": [
        "lifestyle", "restaurants", "cafes", "nightlife", "entertainment", "vibe", "atmosphere",
    ],
    "Schools & healthcare": [
        "school", "nursery", "education", "clinic", "hospital", "healthcare", "medical",
    ],
    "Investment potential": [
        "investment", "investor", "roi", "yield", "capital appreciation", "returns", "demand",
    ],
    "Pros & cons": [
        "pros", "cons", "advantages", "disadvantages", "benefits", "challenges",
    ],
    "Safety & security": [
        "safety", "security", "safe", "crime",
    ],
    "Parking & traffic": [
        "parking", "traffic", "congestion", "rush hour",
    ],
}

SECTION_POINT_SKIP = {
    "other", "general", "overview", "summary", "conclusion", "faqs", "faq",
    "introduction", "read more", "next", "previous",
}

def _contains_signal(text_norm: str, signal: str) -> bool:
    sig = norm_header(signal)
    if not sig:
        return False
    if " " in sig:
        return sig in text_norm
    return re.search(rf"\b{re.escape(sig)}\b", text_norm) is not None

def _titleish_phrase(phrase: str) -> str:
    words = clean(phrase).split()
    if not words:
        return ""
    keep_lower = {"and", "or", "of", "in", "on", "to", "for", "vs", "the", "a", "an", "with"}
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in keep_lower:
            out.append(lw)
        else:
            out.append(lw.capitalize())
    return " ".join(out)

def _clean_candidate_point(text: str) -> str:
    s = clean(text or "")
    s = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"^\s*\d+[\.\)]\s*", "", s)
    s = re.sub(r"^\s*[-•]+\s*", "", s)
    s = re.sub(r"\s*[:\-–—]\s*$", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .,-")
    return clean(s)

def _is_valid_section_point(point: str) -> bool:
    p = _clean_candidate_point(point)
    if not p:
        return False
    if len(p) < 4 or len(p) > 74:
        return False
    if _looks_like_question(p) or header_is_faq(p):
        return False
    if re.search(r"https?://|www\.|\[[^\]]+\]\([^)]+\)|\|", p, flags=re.I):
        return False
    pn = norm_header(p)
    if not pn or pn in SECTION_POINT_SKIP:
        return False
    if sum(1 for c in p if c.isalpha()) / max(len(p), 1) < 0.55:
        return False
    for pat in NOISE_PATTERNS:
        if re.search(pat, pn):
            return False
    return True

def _points_from_subheaders(subheaders: List[str], limit: int = 10) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in subheaders or []:
        p = _clean_candidate_point(raw)
        if not _is_valid_section_point(p):
            continue
        k = norm_header(p)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(p)
        if len(out) >= limit:
            break
    return out

def _points_from_content_text(content: str, section_header: str, limit: int = 10) -> List[str]:
    txt = clean(content or "")
    if len(txt) < 160:
        return []
    freq = phrase_candidates(txt, n_min=2, n_max=4)
    if not freq:
        return []

    scored = sorted(freq.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
    out: List[str] = []
    seen = set()
    for phrase, cnt in scored:
        if cnt < 2 and len(out) >= 2:
            continue
        p = _titleish_phrase(_clean_candidate_point(phrase))
        if not _is_valid_section_point(p):
            continue
        if section_header and header_similarity(section_header, p) >= 0.95:
            continue
        if not _header_core_tokens(p):
            continue
        k = norm_header(p)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(p)
        if len(out) >= limit:
            break
    return out

def _section_key_points(
    section_header: str,
    subheaders: Optional[List[str]],
    section_text: str,
    limit: int = 8,
) -> List[str]:
    out: List[str] = []
    seen = set()

    def _append(points: List[str], cap: int):
        for p in points:
            pp = _clean_candidate_point(p)
            if not _is_valid_section_point(pp):
                continue
            k = norm_header(pp)
            if not k or k in seen:
                continue
            seen.add(k)
            out.append(pp)
            if len(out) >= cap:
                break

    _append(_points_from_subheaders(subheaders or [], limit=max(limit * 2, 8)), cap=limit)
    if len(out) < limit:
        _append(_points_from_content_text(section_text, section_header, limit=max(limit * 2, 8)), cap=limit)

    if not out:
        scope = clean(" ".join([section_header or "", section_text or ""] + (subheaders or [])))
        _append(_important_points_in_text(scope, limit=limit), cap=limit)

    return out[:limit]

def _important_points_in_text(text: str, limit: int = 8) -> List[str]:
    t = norm_header(text or "")
    if not t:
        return []
    out: List[str] = []
    for label, signals in IMPORTANT_POINT_SIGNAL_MAP.items():
        if any(_contains_signal(t, sig) for sig in signals):
            out.append(label)
        if len(out) >= limit:
            break
    return out

def _important_point_covered(point_label: str, text: str) -> bool:
    t = norm_header(text or "")
    if not t:
        return False
    signals = IMPORTANT_POINT_SIGNAL_MAP.get(point_label, [])
    if not signals:
        return False
    return any(_contains_signal(t, sig) for sig in signals)

def _missing_content_points(
    comp_header: str,
    comp_text: str,
    bayut_text: str,
    bayut_global_text: str,
    comp_children: Optional[List[str]] = None,
    bayut_children: Optional[List[str]] = None,
    limit: int = MAX_CONTENT_GAP_ITEMS,
) -> List[str]:
    comp_points = _section_key_points(comp_header, comp_children or [], comp_text, limit=max(limit * 3, 10))
    if not comp_points:
        return []

    out: List[str] = []
    seen = set()
    bayut_local = clean(bayut_text or "")
    bayut_global = clean(bayut_global_text or "")
    bayut_child_objs = [{"header": h} for h in (bayut_children or []) if clean(h)]

    for point in comp_points:
        pk = norm_header(point)
        if not pk or pk in seen:
            continue

        if _topic_is_covered(
            point,
            bayut_child_objs,
            bayut_local,
            min_header_score=HEADER_MATCH_MIN_SCORE,
            min_text_coverage=MISSING_SUBTOPIC_MIN_TEXT_COVERAGE,
        ):
            continue

        if _subtopic_covered_in_text(point, bayut_local):
            continue

        if HIGH_PRECISION_MODE and bayut_global and _topic_is_covered(
            point,
            [],
            bayut_global,
            min_header_score=HEADER_MATCH_MIN_SCORE,
            min_text_coverage=max(MISSING_SUBTOPIC_MIN_TEXT_COVERAGE + 0.08, 0.78),
        ):
            continue

        seen.add(pk)
        out.append(point)
        if len(out) >= limit:
            break

    return out

def summarize_missing_section_action(header: str, subheaders: Optional[List[str]], comp_content: str) -> str:
    parts = []
    seed_points = _section_key_points(header, subheaders or [], comp_content, limit=4)
    if seed_points:
        seed_list = format_gap_list(seed_points, limit=4)
        if seed_list:
            parts.append(f"Add this header with: {seed_list}.")
    else:
        scope = clean(" ".join([header or "", comp_content or ""] + (subheaders or [])))
        themes = list(theme_flags(scope))
        human_map = {
            "transport": "commute & connectivity",
            "traffic_parking": "traffic/parking realities",
            "cost": "cost considerations",
            "lifestyle": "lifestyle & vibe",
            "daily_life": "day-to-day convenience",
            "safety": "safety angle",
            "decision_frame": "decision framing",
            "comparison": "comparison context",
        }
        picks = [human_map.get(x, x) for x in themes]
        theme_list = format_gap_list(picks, limit=3)
        if theme_list:
            parts.append(f"Add this header with: {theme_list}.")
    if not parts:
        parts.append("Add this header with key practical details.")
    return " ".join(parts)

def summarize_content_gap_action(header: str, comp_content: str, bayut_content: str) -> str:
    comp_flags = theme_flags(comp_content)
    bayut_flags = theme_flags(bayut_content)
    missing = list(comp_flags - bayut_flags)

    human_map = {
        "transport": "commute & connectivity",
        "traffic_parking": "traffic/parking realities",
        "cost": "cost considerations",
        "lifestyle": "lifestyle & vibe",
        "daily_life": "day-to-day convenience",
        "safety": "safety angle",
        "decision_frame": "decision framing",
        "comparison": "comparison context",
    }
    missing_human = [human_map.get(x, x) for x in missing]
    missing_list = format_gap_list(missing_human, limit=4)
    if missing_list:
        return "Missing depth on: " + missing_list + "."
    return "Missing depth and practical specifics in this section."


# =====================================================
# UPDATE MODE ENGINE (Headers | Description | Source)
# =====================================================
def update_mode_rows_header_first(
    bayut_nodes: List[dict],
    bayut_fr: FetchResult,
    comp_nodes: List[dict],
    comp_fr: FetchResult,
    comp_url: str,
    max_missing_headers: Optional[int] = None
) -> List[dict]:
    rows_map: Dict[str, dict] = {}
    source = source_link(comp_url)

    def add_row(header: str, parts: List[str]):
        if not header or not parts:
            return
        key = norm_header(header) + "||" + norm_header(re.sub(r"<[^>]+>", "", source))
        if key not in rows_map:
            rows_map[key] = {"Headers": header, "DescriptionParts": [], "Source": source}
        for p in parts:
            p = clean(p)
            if not p:
                continue
            if not p.endswith("."):
                p = p + "."
            if p not in rows_map[key]["DescriptionParts"]:
                rows_map[key]["DescriptionParts"].append(p)

    def children_map(child_sections: List[dict]) -> Dict[str, List[dict]]:
        cmap: Dict[str, List[dict]] = {}
        for sec in child_sections:
            parent = sec.get("parent_h2") or ""
            pk = norm_header(parent)
            if not pk:
                continue
            cmap.setdefault(pk, []).append(sec)
        return cmap

    def child_headers(cmap: Dict[str, List[dict]], parent_header: str) -> List[str]:
        pk = norm_header(parent_header)
        return [c.get("header", "") for c in cmap.get(pk, [])]

    def combined_h2_content(h2_header: str, h2_list: List[dict], cmap: Dict[str, List[dict]]) -> str:
        pk = norm_header(h2_header)
        h2_content = ""
        for h2 in h2_list:
            if norm_header(h2.get("header", "")) == pk:
                h2_content = h2.get("content", "")
                break
        child_content = " ".join(c.get("content", "") for c in cmap.get(pk, []))
        return clean(" ".join([h2_content, child_content]))

    def depth_gap_summary(comp_text: str, bayut_text: str) -> str:
        c_txt = clean(comp_text or "")
        b_txt = clean(bayut_text or "")
        if len(c_txt) < 140:
            return ""
        if len(c_txt) < (1.30 * max(len(b_txt), 1)):
            return ""
        comp_flags = theme_flags(c_txt)
        bayut_flags = theme_flags(b_txt)
        if len(comp_flags - bayut_flags) < 1 and len(c_txt) < 650:
            return ""
        return summarize_content_gap_action("", c_txt, b_txt)

    bayut_secs = section_nodes(bayut_nodes, levels=(2, 3, 4))
    comp_secs = section_nodes(comp_nodes, levels=(2, 3, 4))

    bayut_h2 = [s for s in bayut_secs if s["level"] == 2]
    bayut_child_sections = [s for s in bayut_secs if s["level"] >= 3]
    comp_h2 = [s for s in comp_secs if s["level"] == 2]
    comp_children_all = [s for s in comp_secs if s["level"] >= 3]

    bayut_children_map = children_map(bayut_child_sections)
    comp_children_map = children_map(comp_children_all)
    bayut_global_text = _coverage_corpus(bayut_fr, bayut_nodes)

    for cs in comp_h2:
        comp_header = cs.get("header", "")
        if not comp_header or header_is_faq(comp_header) or _looks_like_question(comp_header):
            continue
        comp_children = [
            h for h in child_headers(comp_children_map, comp_header)
            if clean(h) and not _looks_like_question(clean(h)) and not header_is_faq(clean(h))
        ]
        comp_text = combined_h2_content(comp_header, comp_h2, comp_children_map) or cs.get("content", "")

        m = find_best_bayut_match(comp_header, bayut_h2, min_score=HEADER_MATCH_MIN_SCORE)
        if not m:
            if HIGH_PRECISION_MODE and _topic_is_covered(
                comp_header,
                bayut_h2 + bayut_child_sections,
                bayut_global_text,
                min_header_score=HEADER_MATCH_MIN_SCORE,
                min_text_coverage=MISSING_HEADER_MIN_TEXT_COVERAGE,
            ):
                continue
            desc = summarize_missing_section_action(comp_header, comp_children, comp_text)
            add_row(comp_header, [desc])
            continue

        bayut_header = m["bayut_section"]["header"]
        bayut_child_headers = [
            h for h in child_headers(bayut_children_map, bayut_header)
            if clean(h) and not _looks_like_question(clean(h)) and not header_is_faq(clean(h))
        ]
        bayut_text = combined_h2_content(bayut_header, bayut_h2, bayut_children_map)
        missing_points = _missing_content_points(
            comp_header,
            comp_text,
            bayut_text,
            bayut_global_text,
            comp_children=comp_children,
            bayut_children=bayut_child_headers,
            limit=MAX_CONTENT_GAP_ITEMS,
        )

        parts = []
        if missing_points:
            sub_list = format_gap_list(missing_points, limit=MAX_CONTENT_GAP_ITEMS)
            if sub_list:
                parts.append(f"Important missing points: {sub_list}.")

        if not missing_points:
            depth_note = depth_gap_summary(comp_text, bayut_text)
            if depth_note:
                parts.append(depth_note)

        if parts:
            add_row(bayut_header or comp_header, parts)

    comp_h2_norms = {norm_header(h.get("header", "")) for h in comp_h2}
    for cs in comp_children_all:
        ch = clean(cs.get("header", ""))
        if not ch or _looks_like_question(ch) or header_is_faq(ch):
            continue
        parent = cs.get("parent_h2") or ""
        if parent and norm_header(parent) in comp_h2_norms:
            continue
        m = find_best_bayut_match(ch, bayut_child_sections + bayut_h2, min_score=HEADER_MATCH_MIN_SCORE)
        if m:
            continue
        if HIGH_PRECISION_MODE and _topic_is_covered(
            ch,
            bayut_child_sections + bayut_h2,
            bayut_global_text,
            min_header_score=HEADER_MATCH_MIN_SCORE,
            min_text_coverage=MISSING_SUBTOPIC_MIN_TEXT_COVERAGE,
        ):
            continue
        desc = summarize_missing_section_action(ch, None, cs.get("content", ""))
        add_row(ch, [desc])

    rows = []
    for r in rows_map.values():
        desc = " ".join(r.get("DescriptionParts", [])).strip()
        rows.append({"Headers": r.get("Headers", ""), "Description": desc, "Source": r.get("Source", "")})

    if max_missing_headers and len(rows) > max_missing_headers:
        rows = rows[:max_missing_headers]

    faq_row = missing_faqs_row(bayut_nodes, bayut_fr, comp_nodes, comp_fr, comp_url)
    if faq_row:
        rows.append(faq_row)

    return dedupe_rows(rows)


# =====================================================
# SEO ANALYSIS (YOUR SAME LOGIC)
# =====================================================
def _secrets_get(key: str, default=None):
    try:
        v = os.getenv(key)
        if v is not None and v != "":
            return v
    except Exception:
        pass
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return default

SERPAPI_API_KEY = _env_or_secret("SERPAPI_API_KEY", None)

DATAFORSEO_LOGIN = _first_secret(
    [
        "DATAFORSEO_LOGIN",
        "DATAFORSEO_EMAIL",
        "DATAFORSEO_USERNAME",
        "DATAFORSEO_API_LOGIN",
        "DATAFORSEO_API_USERNAME",
    ],
    None,
)

DATAFORSEO_PASSWORD = _first_secret(
    [
        "DATAFORSEO_PASSWORD",
        "DATAFORSEO_API_PASSWORD",
        "DATAFORSEO_API_KEY",
    ],
    None,
)

DATAFORSEO_LOCATION_CODE = _env_or_secret("DATAFORSEO_LOCATION_CODE", None)
DATAFORSEO_LOCATION_NAME = _env_or_secret("DATAFORSEO_LOCATION_NAME", "United Arab Emirates")
DATAFORSEO_LANGUAGE_CODE = _env_or_secret("DATAFORSEO_LANGUAGE_CODE", "en")
DATAFORSEO_SE_DOMAIN = _env_or_secret("DATAFORSEO_SE_DOMAIN", "google.ae")
DATAFORSEO_DEPTH = int(_env_or_secret("DATAFORSEO_DEPTH", 50))

def url_slug(url: str) -> str:
    try:
        p = urlparse(url).path.strip("/")
        return "/" + p if p else "/"
    except Exception:
        return "/"

def extract_head_seo(html: str) -> Tuple[str, str]:
    if not html:
        return ("Not available", "Not available")
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    t = soup.find("title")
    if t:
        title = clean(t.get_text(" "))

    desc = ""
    md = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if md and md.get("content"):
        desc = clean(md.get("content"))

    return (title or "Not available", desc or "Not available")

def is_mobile_friendly(html: str) -> str:
    if not html:
        return "No"
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": re.compile("^viewport$", re.I)})
    if meta and meta.get("content"):
        return "Yes"
    return "No"

def extract_media_used(html: str) -> str:
    if not html:
        return "Not available"
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()
    root = soup.find("article") or soup

    imgs = len(root.find_all("img"))
    videos = len(root.find_all("video"))
    tables = len(root.find_all("table"))

    for x in root.find_all("iframe"):
        src = (x.get("src") or "").lower()
        if any(k in src for k in ["youtube", "youtu.be", "vimeo", "dailymotion"]):
            videos += 1

    types = []
    if imgs:
        types.append("Images")
    if videos:
        types.append("Video")
    if tables:
        types.append("Tables")
    return ", ".join(types) if types else "None detected"

def tokenize(text: str) -> List[str]:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    toks = [t for t in text.split() if t and len(t) >= 3]
    return toks

def phrase_candidates(text: str, n_min=2, n_max=4) -> Dict[str, int]:
    toks = tokenize(text)
    freq: Dict[str, int] = {}
    for n in range(n_min, n_max + 1):
        for i in range(0, max(len(toks) - n + 1, 0)):
            chunk = toks[i:i+n]
            if not chunk:
                continue
            if chunk[0] in STOP or chunk[-1] in STOP:
                continue
            if all(w in STOP or w in GENERIC_STOP for w in chunk):
                continue
            phrase = " ".join(chunk)
            if len(phrase) < 8:
                continue
            freq[phrase] = freq.get(phrase, 0) + 1
    return freq

def pick_fkw_only(seo_title: str, h1: str, headings_blob_text: str, body_text: str, manual_fkw: str = "") -> str:
    manual_fkw = clean(manual_fkw)
    if manual_fkw:
        return manual_fkw.lower()

    base = " ".join([seo_title or "", h1 or "", headings_blob_text or "", body_text or ""])
    freq = phrase_candidates(base, n_min=2, n_max=4)
    if not freq:
        return "Not available"

    title_low = (seo_title or "").lower()
    h1_low = (h1 or "").lower()

    scored = []
    for ph, c in freq.items():
        boost = 1.0
        if ph in title_low:
            boost += 0.9
        if ph in h1_low:
            boost += 0.6
        scored.append((c * boost, ph))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else "Not available"

def word_count_from_text(text: str) -> int:
    t = clean(text or "")
    if not t:
        return 0
    return len(re.findall(r"\b\w+\b", t))

def _safe_tag_attr(el, key: str):
    try:
        attrs = getattr(el, "attrs", None)
        if isinstance(attrs, dict):
            return attrs.get(key)
    except Exception:
        return None
    return None

def _remove_noncontent_elements(soup: BeautifulSoup) -> None:
    for el in soup.find_all(True):
        cls = " ".join(_safe_tag_attr(el, "class") or []).lower()
        el_id = (_safe_tag_attr(el, "id") or "").lower()
        if any(tok in cls or tok in el_id for tok in NONCONTENT_TOKENS):
            el.decompose()

def _find_content_root(soup: BeautifulSoup):
    candidates = []
    for tag in soup.find_all(attrs={"itemprop": re.compile(r"articleBody", re.I)}):
        candidates.append(tag)
    for el in soup.find_all(["div", "section", "article"]):
        cls = " ".join(_safe_tag_attr(el, "class") or []).lower()
        if any(hint in cls for hint in CONTENT_CLASS_HINTS):
            candidates.append(el)
    for el in [soup.find("article"), soup.find("main")]:
        if el:
            candidates.append(el)
    if not candidates:
        return soup

    def hint_score(el) -> int:
        score = 0
        if getattr(el, "name", "") == "article":
            score += 3
        cls = " ".join(_safe_tag_attr(el, "class") or []).lower()
        if any(hint in cls for hint in CONTENT_CLASS_HINTS):
            score += 2
        if el.get("itemprop") and re.search(r"articleBody", str(el.get("itemprop")), re.I):
            score += 3
        return score

    def word_score(el) -> int:
        try:
            text = clean(el.get_text(" "))
        except Exception:
            return 0
        return len(re.findall(r"\b\w+\b", text))

    return max(candidates, key=lambda el: (hint_score(el), word_score(el)))

def _looks_like_heading_line(line: str) -> bool:
    words = re.findall(r"[A-Za-z]{2,}", line)
    if not words:
        return True
    if re.fullmatch(r"[A-Z0-9\s&':-]{6,}", line):
        return True
    if not re.search(r"[\\.?!,]", line) and len(words) <= 12:
        return True
    return False

def content_text_from_html(html: str, include_headings: bool = False) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS) + list(LIST_TAGS)):
        t.decompose()
    _remove_noncontent_elements(soup)
    root = _find_content_root(soup)
    chunks = []
    tags = ["p"]
    if include_headings:
        tags = ["h1", "h2", "h3", "h4", "h5", "h6", "p"]
    for tag in root.find_all(tags):
        text = clean(tag.get_text(" "))
        if not text:
            continue
        text_low = text.lower()
        if text_low.startswith(("updated:", "last updated:", "published", "min read")):
            continue
        if not include_headings and tag.name != "p":
            continue
        chunks.append(text)
    return clean(" ".join(chunks))

def content_text_from_plaintext(text: str, include_headings: bool = False) -> str:
    if not text:
        return ""
    keep = []
    for raw in text.splitlines():
        s = clean(raw)
        if not s:
            continue
        s_low = s.lower()
        if s_low.startswith(("title:", "url source:", "published time:", "updated:", "last updated:", "markdown content:")):
            continue
        if s_low.endswith("min read"):
            continue
        if s.startswith("!["):
            continue
        if s == "|" or re.fullmatch(r"[-_=]{3,}", s):
            continue
        if re.match(r"^\*+\s*\[", s):
            continue
        if re.match(r"^[-*•]\\s+", s):
            continue
        if re.match(r"^\\d+[\\).:-]\\s+", s):
            continue
        if not include_headings and _looks_like_heading_line(s):
            continue
        keep.append(s)
    return clean(" ".join(keep))

def content_text_from_plaintext_lenient(text: str) -> str:
    if not text:
        return ""
    keep = []
    for raw in text.splitlines():
        s = clean(raw)
        if not s:
            continue
        s_low = s.lower()
        if s_low.startswith(("title:", "url source:", "published time:", "updated:", "last updated:", "markdown content:")):
            continue
        if s_low.endswith("min read"):
            continue
        if s.startswith("!["):
            continue
        if s == "|" or re.fullmatch(r"[-_=]{3,}", s):
            continue
        keep.append(s)
    return clean(" ".join(keep))

def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z0-9]+", (text or "").lower())

def compute_kw_repetition(text: str, phrase: str) -> str:
    if not text or not phrase or phrase == "Not available":
        return "Not available"
    t_tokens = _tokenize_words(text)
    p_tokens = _tokenize_words(phrase)
    if not p_tokens:
        return "0"
    n = len(p_tokens)
    count = 0
    for i in range(0, len(t_tokens) - n + 1):
        if t_tokens[i:i + n] == p_tokens:
            count += 1
    return str(count)

def kw_usage_summary(seo_title: str, h1: str, headings_blob_text: str, body_text: str, fkw: str) -> str:
    fkw = clean(fkw or "").lower()
    if not fkw or fkw == "not available":
        return "Not available"

    text = clean(body_text or "")
    wc = word_count_from_text(text)

    rep = compute_kw_repetition(text, fkw)
    try:
        rep_i = int(rep)
    except Exception:
        rep_i = None

    per_1k = "Not available"
    if wc and rep_i is not None:
        per_1k = f"{(rep_i / max(wc,1))*1000:.1f}/1k"

    title_hit = "Yes" if fkw in (seo_title or "").lower() else "No"
    h1_hit = "Yes" if fkw in (h1 or "").lower() else "No"
    headings_hit = "Yes" if fkw in (headings_blob_text or "").lower() else "No"
    intro_raw = (body_text or "")[:1200].lower()
    intro_hit = "Yes" if fkw in intro_raw else "No"

    return f"Repeats:{rep} | {per_1k} | Title:{title_hit} H1:{h1_hit} Headings:{headings_hit} Intro:{intro_hit}"

def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return host.split(":")[0]
    except Exception:
        return ""

def _extract_canonical_and_robots(html: str) -> Tuple[str, str]:
    if not html:
        return ("Not available", "Not available")

    soup = BeautifulSoup(html, "html.parser")

    canonical = ""
    can = soup.find("link", attrs={"rel": "canonical"})
    if can and can.get("href"):
        canonical = clean(can.get("href"))

    robots = ""
    mr = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    if mr and mr.get("content"):
        robots = clean(mr.get("content"))

    return (canonical or "Not available", robots or "Not available")

def _extract_lang(html: str) -> str:
    if not html:
        return "Not available"
    soup = BeautifulSoup(html, "html.parser")
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        return clean(html_tag.get("lang"))
    meta = soup.find("meta", attrs={"http-equiv": re.compile("content-language", re.I)})
    if meta and meta.get("content"):
        return clean(meta.get("content"))
    meta = soup.find("meta", attrs={"name": re.compile("^language$", re.I)})
    if meta and meta.get("content"):
        return clean(meta.get("content"))
    meta = soup.find("meta", attrs={"property": re.compile("og:locale", re.I)})
    if meta and meta.get("content"):
        return clean(meta.get("content"))
    return "Not available"

def _jsonld_find_name(data, key: str) -> str:
    if isinstance(data, dict):
        if key in data:
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return clean(val)
            if isinstance(val, dict):
                name = val.get("name") or val.get("@id") or val.get("url")
                if isinstance(name, str) and name.strip():
                    return clean(name)
            if isinstance(val, list):
                for item in val:
                    name = _jsonld_find_name({key: item}, key)
                    if name:
                        return name
        for v in data.values():
            out = _jsonld_find_name(v, key)
            if out:
                return out
    elif isinstance(data, list):
        for v in data:
            out = _jsonld_find_name(v, key)
            if out:
                return out
    return ""

def _extract_author_publisher(html: str) -> Tuple[str, str]:
    if not html:
        return ("Not available", "Not available")
    soup = BeautifulSoup(html, "html.parser")
    author = ""
    publisher = ""
    a = soup.find("meta", attrs={"name": re.compile("^author$", re.I)})
    if a and a.get("content"):
        author = clean(a.get("content"))
    if not author:
        a = soup.find("meta", attrs={"property": re.compile("article:author", re.I)})
        if a and a.get("content"):
            author = clean(a.get("content"))
    if not author:
        a = soup.find(attrs={"itemprop": re.compile("^author$", re.I)})
        if a and a.get("content"):
            author = clean(a.get("content"))

    p = soup.find("meta", attrs={"name": re.compile("^publisher$", re.I)})
    if p and p.get("content"):
        publisher = clean(p.get("content"))
    if not publisher:
        p = soup.find("meta", attrs={"property": re.compile("article:publisher", re.I)})
        if p and p.get("content"):
            publisher = clean(p.get("content"))
    if not publisher:
        p = soup.find(attrs={"itemprop": re.compile("^publisher$", re.I)})
        if p and p.get("content"):
            publisher = clean(p.get("content"))

    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    for s in scripts:
        raw = (s.string or s.get_text(" ") or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if not author:
            author = _jsonld_find_name(data, "author")
        if not publisher:
            publisher = _jsonld_find_name(data, "publisher")
        if author and publisher:
            break

    return (author or "Not available", publisher or "Not available")

def _count_images(html: str) -> int:
    if not html:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    return len(soup.find_all("img"))

def _count_headers(html: str) -> str:
    if not html:
        return "H1:0 / H2:0 / H3:0 / Total:0"
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()
    h1 = len(soup.find_all("h1"))
    h2 = len(soup.find_all("h2"))
    h3 = len(soup.find_all("h3"))
    total = h1 + h2 + h3
    return f"H1:{h1} / H2:{h2} / H3:{h3} / Total:{total}"

def _heading_counts(nodes: List[dict], html: str) -> Dict[int, int]:
    counts = {i: 0 for i in range(1, 7)}
    used = False
    h1_exists = False
    if html and "<h1" in html.lower():
        try:
            soup_full = BeautifulSoup(html, "html.parser")
            h1_tag = soup_full.find("h1")
            if h1_tag and clean(h1_tag.get_text(" ")):
                h1_exists = True
        except Exception:
            h1_exists = False
    if html and "<h" in html.lower():
        soup = BeautifulSoup(html, "html.parser")
        for t in soup.find_all(list(IGNORE_TAGS)):
            t.decompose()
        _remove_noncontent_elements(soup)
        root = _find_content_root(soup)
        for tag in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            counts[int(tag.name[1])] += 1
        used = True
        if counts[1] == 0 and h1_exists:
            counts[1] = 1
    if not used and nodes:
        for x in flatten(nodes):
            lvl = x.get("level")
            h = clean(x.get("header", ""))
            if not h or is_noise_header(h) or header_is_faq(h):
                continue
            if isinstance(lvl, int) and 1 <= lvl <= 6:
                counts[lvl] += 1
                used = True
    has_title_line = bool(re.search(r"(?m)^Title:\s*.+$", html or ""))
    if not used and has_title_line:
        counts[1] = 1
    return counts

def _heading_structure_label(nodes: List[dict], html: str) -> str:
    levels: List[int] = []
    h1_fallback = False
    html_levels: List[int] = []
    if html and "<h" in html.lower():
        soup = BeautifulSoup(html, "html.parser")
        for t in soup.find_all(list(IGNORE_TAGS)):
            t.decompose()
        _remove_noncontent_elements(soup)
        root = _find_content_root(soup)
        for tag in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            html_levels.append(int(tag.name[1]))
        if 1 not in html_levels:
            try:
                soup_full = BeautifulSoup(html, "html.parser")
                h1_tag = soup_full.find("h1")
                if h1_tag and clean(h1_tag.get_text(" ")):
                    h1_fallback = True
            except Exception:
                h1_fallback = False
    if html_levels:
        levels = html_levels
    if not levels and nodes:
        for x in flatten(nodes):
            lvl = x.get("level")
            h = clean(x.get("header", ""))
            if not h or is_noise_header(h) or header_is_faq(h):
                continue
            if isinstance(lvl, int):
                levels.append(lvl)
            if lvl == 1 and h:
                h1_fallback = True
    has_title_line = bool(re.search(r"(?m)^Title:\s*.+$", html or ""))
    if levels and 1 not in levels and has_title_line:
        levels = [1] + levels
    if not levels and has_title_line:
        levels = [1]
    if levels and 1 not in levels and h1_fallback:
        levels = [1] + levels

    counts = _heading_counts(nodes, html)
    if sum(counts.values()) == 0 and nodes:
        for x in flatten(nodes):
            lvl = x.get("level")
            h = clean(x.get("header", ""))
            if not h or is_noise_header(h) or header_is_faq(h):
                continue
            if isinstance(lvl, int) and 1 <= lvl <= 6:
                counts[lvl] += 1
    if sum(counts.values()) == 0:
        return "Weak (no headings)"
    if counts[1] == 0:
        return "Weak (missing H1)"
    for lvl in range(2, 6):
        if counts[lvl] == 0 and any(counts[x] > 0 for x in range(lvl + 1, 7)):
            return f"Weak (missing H{lvl})"
    return "OK"

from urllib.parse import urljoin

def _count_external_links(html: str, page_url: str) -> int:
    if not html:
        return 0

    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()
    _remove_noncontent_elements(soup)
    root = _find_content_root(soup)

    external = 0
    base_dom = domain_of(page_url)

    for a in root.find_all("a", href=True):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        hlow = href.lower()
        if hlow.startswith("#") or hlow.startswith("mailto:") or hlow.startswith("tel:") or hlow.startswith("javascript:"):
            continue
        full = urljoin(page_url, href)
        try:
            p = urlparse(full)
        except Exception:
            continue
        dom = (p.netloc or "").lower().replace("www.", "")
        if not dom:
            continue
        if base_dom and (dom == base_dom or dom.endswith("." + base_dom)):
            continue
        external += 1

    return external

def _schema_present(html: str) -> str:
    if not html:
        return "None detected"
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    types = set()
    for s in scripts:
        raw = (s.string or "").strip()
        if not raw:
            continue
        try:
            j = json.loads(raw)
        except Exception:
            continue

        def walk(x):
            if isinstance(x, dict):
                t = x.get("@type") or x.get("type")
                if t:
                    if isinstance(t, list):
                        for z in t:
                            types.add(str(z))
                    else:
                        types.add(str(t))
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(j)
    return ", ".join(sorted(types)) if types else "None detected"

def seo_row_for_page_extended(label: str, url: str, fr: FetchResult, nodes: List[dict], manual_fkw: str = "") -> dict:
    seo_title, meta_desc = extract_head_seo(fr.html or "")
    slug = url_slug(url) if url and url != "Not applicable" else "Not applicable"
    h_blob = headings_blob(nodes)
    h_counts = _heading_structure_label(nodes, fr.html or fr.text or "")
    fkw = pick_fkw_only(seo_title, get_first_h1(nodes), h_blob, fr.text or "", manual_fkw=manual_fkw)
    kw_usage = kw_usage_summary(seo_title, get_first_h1(nodes), h_blob, fr.text or "", fkw)
    outbound_links_count = _count_external_links(fr.html or "", url or "")
    media = extract_media_used(fr.html or "")
    schema = _schema_present(fr.html or "")
    mobile_friendly = is_mobile_friendly(fr.html or "")

    return {
        "Page": label,
        "UAE Rank (Mobile)": "Not available",
        "SEO Title": seo_title,
        "Meta Description": meta_desc,
        "URL Slug": slug,
        "Headers": h_counts,
        "FKW Usage": kw_usage,
        "Mobile Friendly": mobile_friendly,
        "External Links": str(outbound_links_count),
        "Media (Images/Video/Tables)": media,
        "Schema Present": schema,
        "__fkw": fkw,
        "__url": url,
    }

def build_seo_analysis_update(
    bayut_url: str,
    bayut_fr: FetchResult,
    bayut_nodes: List[dict],
    competitors: List[str],
    comp_fr_map: Dict[str, FetchResult],
    comp_tree_map: Dict[str, dict],
    manual_fkw: str = ""
) -> pd.DataFrame:
    rows = []
    rows.append(seo_row_for_page_extended("Bayut", bayut_url, bayut_fr, bayut_nodes, manual_fkw=manual_fkw))
    for cu in competitors:
        fr = comp_fr_map.get(cu)
        nodes = (comp_tree_map.get(cu) or {}).get("nodes", [])
        rows.append(seo_row_for_page_extended(site_name(cu), cu, fr, nodes, manual_fkw=manual_fkw))
    df = pd.DataFrame(rows)
    cols = [
        "Page","UAE Rank (Mobile)","Mobile Friendly","SEO Title","Meta Description","URL Slug",
        "Headers","FKW Usage",
        "External Links","Media (Images/Video/Tables)",
        "Schema Present","__fkw","__url"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]

def build_seo_analysis_newpost(
    new_title: str,
    competitors: List[str],
    comp_fr_map: Dict[str, FetchResult],
    comp_tree_map: Dict[str, dict],
    manual_fkw: str = ""
) -> pd.DataFrame:
    rows = []
    for cu in competitors:
        fr = comp_fr_map.get(cu)
        nodes = (comp_tree_map.get(cu) or {}).get("nodes", [])
        rows.append(seo_row_for_page_extended(site_name(cu), cu, fr, nodes, manual_fkw=manual_fkw))
    df = pd.DataFrame(rows)
    cols = [
        "Page","UAE Rank (Mobile)","Mobile Friendly","SEO Title","Meta Description","URL Slug",
        "Headers","FKW Usage",
        "External Links","Media (Images/Video/Tables)",
        "Schema Present","__fkw","__url"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]

def _dataforseo_task_payload(query: str, device: str) -> dict:
    payload = {
        "keyword": query,
        "language_code": DATAFORSEO_LANGUAGE_CODE,
        "se_domain": DATAFORSEO_SE_DOMAIN,
        "device": device,
        "depth": int(DATAFORSEO_DEPTH) if str(DATAFORSEO_DEPTH).isdigit() else 50,
    }
    if device == "mobile":
        payload["os"] = "android"
    if DATAFORSEO_LOCATION_CODE:
        try:
            payload["location_code"] = int(DATAFORSEO_LOCATION_CODE)
        except Exception:
            payload["location_code"] = DATAFORSEO_LOCATION_CODE
    elif DATAFORSEO_LOCATION_NAME:
        payload["location_name"] = DATAFORSEO_LOCATION_NAME
    return payload

@st.cache_data(show_spinner=False, ttl=1800)
def dataforseo_serp_cached(query: str, device: str = "mobile") -> dict:
    if not query:
        return {"_error": "missing_query"}
    if not DATAFORSEO_LOGIN or not DATAFORSEO_PASSWORD:
        return {"_error": "missing_dataforseo_credentials"}
    payload = [_dataforseo_task_payload(query, device)]
    try:
        r = requests.post(
            "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
            json=payload,
            auth=(DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD),
            timeout=40,
        )
        if r.status_code != 200:
            return {"_error": f"dataforseo_http_{r.status_code}", "_text": r.text[:400]}
        data = r.json()
    except Exception as e:
        return {"_error": str(e)}

    if isinstance(data, dict) and data.get("status_code") not in (20000, None):
        return {"_error": data.get("status_message", "dataforseo_error")}
    return data

def _dataforseo_rank_map(data: dict) -> Dict[str, int]:
    rank_map: Dict[str, int] = {}
    if not isinstance(data, dict):
        return rank_map
    tasks = data.get("tasks") or []
    for task in tasks:
        if task.get("status_code") != 20000:
            continue
        for res in task.get("result") or []:
            for item in res.get("items") or []:
                if item.get("type") not in {"organic", "organic_extended"}:
                    continue
                url = item.get("url") or ""
                if not url:
                    continue
                rank = item.get("rank_absolute") or item.get("rank_group")
                if not rank:
                    continue
                norm = normalize_url_for_match(url)
                if norm and (norm not in rank_map or int(rank) < rank_map[norm]):
                    rank_map[norm] = int(rank)
    return rank_map

def enrich_seo_df_with_rank_and_ai(seo_df: pd.DataFrame, manual_query: str = "") -> Tuple[pd.DataFrame, pd.DataFrame]:
    ai_df = pd.DataFrame(columns=["Note"])
    if seo_df is None or seo_df.empty:
        return seo_df, ai_df

    query = clean(manual_query or "")
    if not query:
        for q in seo_df.get("__fkw", []):
            if clean(str(q)) and str(q).lower() != "not available":
                query = clean(str(q))
                break

    if query:
        data = dataforseo_serp_cached(query, device="mobile")
        if isinstance(data, dict) and data.get("_error"):
            seo_df = seo_df.copy()
            seo_df["UAE Rank (Mobile)"] = f"Not available ({data.get('_error')})"
        else:
            rank_map = _dataforseo_rank_map(data)
            depth = int(DATAFORSEO_DEPTH) if str(DATAFORSEO_DEPTH).isdigit() else 50
            updated = []
            for _, r in seo_df.iterrows():
                page_url = str(r.get("__url", "")).strip()
                if not page_url or page_url == "Not applicable":
                    updated.append("Not applicable")
                    continue
                norm = normalize_url_for_match(page_url)
                rank = rank_map.get(norm)
                if rank:
                    updated.append(str(rank))
                else:
                    updated.append(f"Not in top {depth}")
            seo_df = seo_df.copy()
            seo_df["UAE Rank (Mobile)"] = updated
    return seo_df, ai_df


# =====================================================
# AI VISIBILITY (AIO) TABLE
# =====================================================
AI_OVERVIEW_KEYS = {"ai_overview", "ai_overviews", "ai overview", "ai overviews"}
URL_RE = re.compile(r"https?://[^\s\"'>\)]+")

def _find_ai_overview_block(data):
    if isinstance(data, dict):
        for k, v in data.items():
            if any(key in k.lower() for key in AI_OVERVIEW_KEYS):
                return v
        for v in data.values():
            found = _find_ai_overview_block(v)
            if found is not None:
                return found
    elif isinstance(data, list):
        for v in data:
            found = _find_ai_overview_block(v)
            if found is not None:
                return found
    return None

def _collect_urls(obj) -> List[str]:
    urls: List[str] = []
    if isinstance(obj, str):
        urls.extend(URL_RE.findall(obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and k.lower() in {"link", "source", "url"}:
                urls.extend(URL_RE.findall(v) or [v])
            else:
                urls.extend(_collect_urls(v))
    elif isinstance(obj, list):
        for v in obj:
            urls.extend(_collect_urls(v))
    return urls

def _dataforseo_items(data: dict) -> List[dict]:
    items: List[dict] = []
    if not isinstance(data, dict):
        return items
    for task in data.get("tasks") or []:
        if task.get("status_code") != 20000:
            continue
        for res in task.get("result") or []:
            for item in res.get("items") or []:
                if isinstance(item, dict):
                    items.append(item)
    return items

def _dataforseo_ai_blocks(data: dict) -> List[dict]:
    ai_items = []
    for item in _dataforseo_items(data):
        t = (item.get("type") or "").lower()
        if "ai_overview" in t:
            ai_items.append(item)
    if ai_items:
        return ai_items
    fallback = _find_ai_overview_block(data)
    if fallback:
        return [fallback] if isinstance(fallback, dict) else fallback
    return []

def _dataforseo_features_present(data: dict) -> List[str]:
    features = []
    seen = set()
    feature_map = {
        "ai_overview": "AI Overview",
        "featured_snippet": "Featured snippet",
        "answer_box": "Answer box",
        "knowledge_graph": "Knowledge panel",
        "local_pack": "Local pack",
        "people_also_ask": "People also ask",
        "top_stories": "Top stories",
        "news": "News results",
        "images": "Image pack",
        "image_pack": "Image pack",
        "videos": "Video results",
        "video": "Video results",
        "shopping": "Shopping results",
        "related_questions": "People also ask",
    }
    for item in _dataforseo_items(data):
        t = (item.get("type") or "").lower()
        for key, label in feature_map.items():
            if key in t and label not in seen:
                seen.add(label)
                features.append(label)
    return features

def _dataforseo_paa_questions(data: dict) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in _dataforseo_items(data):
        t = (item.get("type") or "").lower()
        if "people_also_ask" not in t and "related_questions" not in t:
            continue
        items = item.get("items") or []
        if isinstance(items, list) and items:
            for q in items:
                if not isinstance(q, dict):
                    continue
                text = q.get("question") or q.get("title") or q.get("text") or ""
                text = clean(text)
                if not text:
                    continue
                k = norm_header(text)
                if k and k not in seen:
                    seen.add(k)
                    out.append(text)
        else:
            text = item.get("question") or item.get("title") or item.get("text") or ""
            text = clean(text)
            if text:
                k = norm_header(text)
                if k and k not in seen:
                    seen.add(k)
                    out.append(text)
    return out

def _serp_features_present(data: dict) -> List[str]:
    if not isinstance(data, dict):
        return []
    features = []
    feature_map = {
        "ai_overview": "AI Overview",
        "answer_box": "Answer box",
        "featured_snippet": "Featured snippet",
        "knowledge_graph": "Knowledge panel",
        "related_questions": "People also ask",
        "local_results": "Local pack",
        "top_stories": "Top stories",
        "news_results": "News results",
        "images_results": "Image pack",
        "image_results": "Image pack",
        "video_results": "Video results",
        "shopping_results": "Shopping results",
        "recipes_results": "Recipes",
    }
    for k, label in feature_map.items():
        if data.get(k):
            features.append(label)
    if _find_ai_overview_block(data) is not None and "AI Overview" not in features:
        features.append("AI Overview")
    return features

def _serpapi_paa_questions(data: dict) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in data.get("related_questions") or []:
        if not isinstance(item, dict):
            continue
        text = item.get("question") or item.get("title") or item.get("text") or ""
        text = clean(text)
        if not text:
            continue
        k = norm_header(text)
        if k and k not in seen:
            seen.add(k)
            out.append(text)
    return out

TIP_ICON_HTML = "<span style='font-size:12px;line-height:1;vertical-align:-1px;' aria-hidden='true'>💡</span>"

def _aio_tip_items(
    target_cited: str,
    serp_features: List[str],
    paa_questions: List[str],
    cited_domains: List[str],
    top_comp_domains: List[str],
) -> List[str]:
    if target_cited != "No":
        return []
    tips = []
    if "AI Overview" in serp_features:
        cited_txt = format_gap_list(cited_domains, limit=4) if cited_domains else "trusted sources"
        tips.append(f"AI Overview is present; add a Quick Answer and cite {cited_txt}.")
    else:
        tips.append("No AI Overview detected; focus on winning Featured Snippet + PAA.")
    if paa_questions:
        top_qs = "; ".join(paa_questions[:3])
        tips.append(f"Add a People Also Ask section with H3s answering: {top_qs}.")
    else:
        tips.append("Add a People Also Ask section with H3 questions + short answers.")
    if top_comp_domains:
        comp_txt = format_gap_list(top_comp_domains, limit=4)
        tips.append(f"Review top competitor coverage (e.g., {comp_txt}) and fill missing sections.")
    tips.append("Include a Key Facts box/table near the top.")
    tips.append("Use intent-matching headings and avoid unsupported claims.")
    return tips

def _aio_tip_cell(status: str, tips: List[str]) -> str:
    if status != "No" or not tips:
        return status
    tip_items = "".join(f"<li>{html_lib.escape(t)}</li>" for t in tips)
    tips_html = f"<ul>{tip_items}</ul>"
    return (
        "<div>No</div>"
        "<details class='details-link'>"
        f"<summary><span class='link-like'>{TIP_ICON_HTML}<span>Tips</span></span></summary>"
        f"<div class='details-box'>{tips_html}</div>"
        "</details>"
    )

@st.cache_data(show_spinner=False, ttl=1800)
def serpapi_serp_cached(query: str, device: str) -> dict:
    if not SERPAPI_API_KEY:
        return {"_error": "missing_serpapi_key"}
    params = {
        "engine": "google",
        "q": query,
        "google_domain": "google.ae",
        "gl": "ae",
        "hl": "en",
        "api_key": SERPAPI_API_KEY,
        "num": 20,
        "device": device,
    }
    try:
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=35)
        if r.status_code != 200:
            return {"_error": f"serpapi_http_{r.status_code}", "_text": r.text[:400]}
        return r.json()
    except Exception as e:
        return {"_error": str(e)}

def build_ai_visibility_table(query: str, target_url: str, competitors: List[str], device: str = "mobile") -> pd.DataFrame:
    cols = ["Target URL Cited in AIO","Cited Domains","# AIO Citations","Top Competitor Domains","SERP Features Present","People Also Ask questions"]
    if not query:
        return pd.DataFrame([{c: "Not available" for c in cols}], columns=cols)

    if DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD:
        data = dataforseo_serp_cached(query, device=device)
        if isinstance(data, dict) and data.get("_error"):
            return pd.DataFrame([{c: f"Not available ({data.get('_error')})" for c in cols}], columns=cols)

        ai_blocks = _dataforseo_ai_blocks(data)
        cited_urls = _collect_urls(ai_blocks) if ai_blocks else []
        cited_urls = list(dict.fromkeys([u for u in cited_urls if u.startswith("http")]))
        cited_domains = []
        for u in cited_urls:
            d = domain_of(u)
            if d and d not in cited_domains:
                cited_domains.append(d)

        target_dom = domain_of(target_url) if target_url and target_url != "Not applicable" else ""
        if not ai_blocks:
            target_cited = "None detected"
            cited_domains_txt = "None detected"
            cited_count = "0"
        else:
            if not target_dom:
                target_cited = "Not applicable"
            else:
                target_cited = "Yes" if target_dom in cited_domains else "No"
            cited_domains_txt = format_gap_list(cited_domains, limit=6) if cited_domains else "None detected"
            cited_count = str(len(cited_urls))

        top_comp_domains = []
        for item in _dataforseo_items(data):
            if (item.get("type") or "").lower() not in {"organic", "organic_extended"}:
                continue
            link = item.get("url") or ""
            dom = domain_of(link)
            if not dom:
                continue
            if target_dom and dom == target_dom:
                continue
            if dom not in top_comp_domains:
                top_comp_domains.append(dom)
            if len(top_comp_domains) >= 6:
                break

        serp_features = _dataforseo_features_present(data)
        serp_features_txt = format_gap_list(serp_features, limit=6) if serp_features else "None detected"
        paa_questions = _dataforseo_paa_questions(data)
        paa_txt = format_gap_list(paa_questions, limit=6) if paa_questions else "None detected"
        tips = _aio_tip_items(target_cited, serp_features, paa_questions, cited_domains, top_comp_domains)

        row = {
            "Target URL Cited in AIO": _aio_tip_cell(target_cited, tips),
            "Cited Domains": cited_domains_txt or "Not available",
            "# AIO Citations": cited_count,
            "Top Competitor Domains": format_gap_list(top_comp_domains, limit=6) if top_comp_domains else "Not available",
            "SERP Features Present": serp_features_txt,
            "People Also Ask questions": paa_txt,
        }
        return pd.DataFrame([row], columns=cols)

    if not SERPAPI_API_KEY:
        return pd.DataFrame([{c: "Not available (no DataForSEO credentials)" for c in cols}], columns=cols)

    data = serpapi_serp_cached(query, device=device)
    if not data or (isinstance(data, dict) and data.get("_error")):
        return pd.DataFrame([{c: "Not available" for c in cols}], columns=cols)

    ai_block = _find_ai_overview_block(data)
    cited_urls = _collect_urls(ai_block) if ai_block is not None else []
    cited_urls = list(dict.fromkeys([u for u in cited_urls if u.startswith("http")]))
    cited_domains = []
    for u in cited_urls:
        d = domain_of(u)
        if d and d not in cited_domains:
            cited_domains.append(d)

    target_dom = domain_of(target_url) if target_url and target_url != "Not applicable" else ""
    if ai_block is None:
        target_cited = "Not available"
        cited_domains_txt = "Not available"
        cited_count = "Not available"
    else:
        if not target_dom:
            target_cited = "Not applicable"
        else:
            target_cited = "Yes" if target_dom in cited_domains else "No"
        cited_domains_txt = format_gap_list(cited_domains, limit=6) if cited_domains else "None detected"
        cited_count = str(len(cited_urls))

    top_comp_domains = []
    organic = data.get("organic_results") or []
    for it in organic:
        link = it.get("link") or ""
        dom = domain_of(link)
        if not dom:
            continue
        if target_dom and dom == target_dom:
            continue
        if dom not in top_comp_domains:
            top_comp_domains.append(dom)
        if len(top_comp_domains) >= 6:
            break

    serp_features = _serp_features_present(data)
    serp_features_txt = format_gap_list(serp_features, limit=6) if serp_features else "None detected"
    paa_questions = _serpapi_paa_questions(data)
    paa_txt = format_gap_list(paa_questions, limit=6) if paa_questions else "None detected"
    tips = _aio_tip_items(target_cited, serp_features, paa_questions, cited_domains, top_comp_domains)

    row = {
        "Target URL Cited in AIO": _aio_tip_cell(target_cited, tips),
        "Cited Domains": cited_domains_txt or "Not available",
        "# AIO Citations": cited_count,
        "Top Competitor Domains": format_gap_list(top_comp_domains, limit=6) if top_comp_domains else "Not available",
        "SERP Features Present": serp_features_txt,
        "People Also Ask questions": paa_txt,
    }
    return pd.DataFrame([row], columns=cols)


# =====================================================
# CONTENT QUALITY (same as your code)
# =====================================================
@st.cache_data(show_spinner=False, ttl=86400)
def _head_last_modified(url: str) -> str:
    try:
        r = requests.head(url, headers=DEFAULT_HEADERS, allow_redirects=True, timeout=18)
        return r.headers.get("Last-Modified", "") or ""
    except Exception:
        return ""

DATE_TEXT_PATTERNS = [
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{4}/\d{1,2}/\d{1,2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    r"\b\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}\b",
    r"\b[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4}\b",
]

def _first_date_in_text(text: str) -> str:
    for pat in DATE_TEXT_PATTERNS:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(0)
    return ""

def _ensure_tz(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _parse_date_string(raw: str) -> Optional[datetime]:
    s = clean(raw or "")
    if not s:
        return None
    s = re.sub(r"\b(\d{1,2})(st|nd|rd|th)\b", r"\1", s, flags=re.I)
    s = re.sub(r"(?i)^(last\s*)?updated\s*(on)?\s*[:\-]?\s*", "", s).strip()
    try:
        dt = parsedate_to_datetime(s)
        if dt:
            return _ensure_tz(dt)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return _ensure_tz(dt)
    except Exception:
        pass
    date_only = _first_date_in_text(s)
    for cand in [s, date_only]:
        if not cand:
            continue
        for fmt in [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%d %b %Y",
            "%d %b, %Y",
            "%d %B %Y",
            "%d %B, %Y",
            "%b %d, %Y",
            "%B %d, %Y",
        ]:
            try:
                return _ensure_tz(datetime.strptime(cand, fmt))
            except Exception:
                continue
    return None

def _extract_primary_date_candidate(html: str) -> Optional[Tuple[str, str]]:
    if not html:
        return None
    m = re.search(r"<h1[^>]*>.*?</h1>", html, re.I | re.S)
    if not m:
        return None
    segment = html[m.end():m.end() + 2500]
    segment_text = re.sub(r"<[^>]+>", " ", segment)
    candidates = _extract_labeled_date_candidates_from_text(segment_text, first_only=True)
    if not candidates:
        return None
    val, kind = candidates[0]
    return (val, f"{kind}_primary")

def _extract_labeled_date_candidates_from_text(text: str, first_only: bool = False) -> List[Tuple[str, str]]:
    if not text:
        return []
    out = []
    for m in re.finditer(r"(last\s*updated|updated\s*on|updated)\s*[:\-]?\s*([^\n]{0,80})", text, re.I):
        snippet = clean(m.group(2))
        if not snippet:
            continue
        date_txt = _first_date_in_text(snippet) or snippet
        if date_txt:
            out.append((date_txt, "modified"))
            if first_only:
                break
    for m in re.finditer(r"(published\s*time|published\s*on|published|date\s*published)\s*[:\-]?\s*([^\n]{0,80})", text, re.I):
        snippet = clean(m.group(2))
        if not snippet:
            continue
        date_txt = _first_date_in_text(snippet) or snippet
        if date_txt:
            out.append((date_txt, "published"))
            if first_only:
                break
    return out

def _extract_labeled_date_candidates(html: str) -> List[Tuple[str, str]]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    scopes = []
    h1 = soup.find("h1")
    if h1:
        scopes.extend([h1.parent, getattr(h1.parent, "parent", None), getattr(getattr(h1.parent, "parent", None), "parent", None)])
    main = soup.find("article") or soup.find("main")
    if main:
        scopes.append(main)
    scopes.append(soup)
    for scope in scopes:
        if not scope:
            continue
        text = scope.get_text(" ", strip=True)
        candidates = _extract_labeled_date_candidates_from_text(text, first_only=True)
        if candidates:
            return candidates
    return []

def _collect_jsonld_dates(obj, out: List[Tuple[str, str]]):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in {"dateModified", "datePublished", "dateCreated", "date"} and isinstance(v, str) and v.strip():
                kind = "modified" if k == "dateModified" else "published"
                out.append((v.strip(), kind))
            elif isinstance(v, (dict, list)):
                _collect_jsonld_dates(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_jsonld_dates(v, out)

def _pick_best_date_candidate(candidates: List[Tuple[str, str]]) -> str:
    parsed = []
    for val, kind in candidates:
        dt = _parse_date_string(val)
        if dt:
            parsed.append((dt, clean(val), kind))
    if not parsed:
        return ""
    primary = [p for p in parsed if p[2].endswith("_primary")]
    if primary:
        modified_primary = [p for p in primary if p[2].startswith("modified")]
        if modified_primary:
            return max(modified_primary, key=lambda x: x[0])[1]
        return max(primary, key=lambda x: x[0])[1]
    modified = [p for p in parsed if p[2].startswith("modified")]
    if modified:
        return max(modified, key=lambda x: x[0])[1]
    return max(parsed, key=lambda x: x[0])[1]

def _extract_last_modified_candidates_from_html(html: str) -> List[Tuple[str, str]]:
    if not html:
        return []
    candidates: List[Tuple[str, str]] = []
    primary = _extract_primary_date_candidate(html)
    if primary:
        candidates.append(primary)
    for m in re.finditer(r'"dateModified"\s*:\s*"([^"]+)"', html, re.I):
        candidates.append((m.group(1), "modified"))
    for m in re.finditer(r'"datePublished"\s*:\s*"([^"]+)"', html, re.I):
        candidates.append((m.group(1), "published"))
    for m in re.finditer(r'"dateCreated"\s*:\s*"([^"]+)"', html, re.I):
        candidates.append((m.group(1), "published"))
    soup = BeautifulSoup(html, "html.parser")
    candidates.extend(_extract_labeled_date_candidates(html))

    meta_candidates = [
        ("meta", {"property": "article:modified_time"}, "content", "modified"),
        ("meta", {"property": "og:updated_time"}, "content", "modified"),
        ("meta", {"property": "article:published_time"}, "content", "published"),
        ("meta", {"name": "lastmod"}, "content", "modified"),
        ("meta", {"name": "last-modified"}, "content", "modified"),
        ("meta", {"name": "date"}, "content", "published"),
        ("meta", {"itemprop": "dateModified"}, "content", "modified"),
        ("meta", {"itemprop": "datePublished"}, "content", "published"),
    ]
    for tag, attrs, key, kind in meta_candidates:
        t = soup.find(tag, attrs=attrs)
        if t and t.get(key):
            v = clean(t.get(key))
            if v:
                candidates.append((v, kind))

    for tm in soup.find_all("time", attrs={"datetime": True}):
        v = clean(tm.get("datetime"))
        if not v:
            continue
        itemprop = (tm.get("itemprop") or "").lower()
        cls = " ".join(tm.get("class") or []).lower()
        kind = "modified" if "updated" in cls or itemprop == "datemodified" else "published"
        candidates.append((v, kind))

    scripts = soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)})
    for s in scripts:
        raw = (s.string or s.get_text(" ") or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        _collect_jsonld_dates(data, candidates)

    return candidates

def _extract_last_modified_from_html(html: str) -> str:
    return _pick_best_date_candidate(_extract_last_modified_candidates_from_html(html))

def get_last_modified(url: str, html: str, text: str = "") -> str:
    candidates: List[Tuple[str, str]] = []
    if html:
        candidates.extend(_extract_last_modified_candidates_from_html(html))
    if text:
        candidates.extend(_extract_labeled_date_candidates_from_text(text, first_only=True))
    v = _pick_best_date_candidate(candidates)
    if v:
        return v
    h = _head_last_modified(url)
    return h if h else "Not available"

def _kw_stuffing_label(word_count: int, repeats: int) -> str:
    if word_count <= 0:
        return "Not available"
    per_1k = (repeats / max(word_count, 1)) * 1000.0
    if per_1k >= 18:
        return f"High ({repeats} repeats, {per_1k:.1f}/1k words)"
    if per_1k >= 10:
        return f"Moderate ({repeats} repeats, {per_1k:.1f}/1k words)"
    return f"Low ({repeats} repeats, {per_1k:.1f}/1k words)"

def _latest_year_mentioned(text: str) -> int:
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", (text or ""))
    ys = []
    for y in years:
        try:
            ys.append(int(y))
        except Exception:
            pass
    return max(ys) if ys else 0

def _has_brief_summary(nodes: List[dict], text: str) -> str:
    blob = (headings_blob(nodes) or "").lower()
    t = (text or "").lower()
    cues = ["tl;dr", "tldr", "key takeaways", "in summary", "summary", "quick summary", "at a glance"]
    if any(c in blob for c in cues) or any(c in t[:1400] for c in cues):
        return "Yes"
    return "No"

def _count_source_links(html: str) -> int:
    if not html:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=True)
    cnt = 0
    for a in links:
        href = a.get("href") or ""
        if href.startswith("http"):
            cnt += 1
    return cnt

GENERIC_ANCHORS = {
    "click here",
    "here",
    "this",
    "learn more",
    "read more",
    "more",
    "see more",
    "view more",
    "view",
    "details",
    "link",
}

INTENT_STOPWORDS = {
    "the","and","for","with","from","that","this","these","those","your","you","our","their","them","they","into",
    "of","in","on","to","a","an","is","are","was","were","be","as","at","by","or","it","its","about","near","vs",
}
PROPERTY_KEYWORDS = {
    "property","properties","apartment","apartments","villa","villas","rent","rental","renting","sale","buy","buying",
    "bedroom","bedrooms","studio","penthouse","townhouse","duplex","freehold","leasehold","mortgage","price","prices",
    "listing","listings","for-sale","for-rent","off-plan","plot","land","invest","investment",
    "community","neighborhood","neighbourhood","district","suburb","area",
}

def _intent_tokens_from_html(html: str, page_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    h1_text = clean(h1.get_text(" ")) if h1 else ""
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = clean(title_tag.get_text(" "))
    slug = urlparse(page_url).path.strip("/").split("/")[-1]
    raw = " ".join([h1_text, title, slug.replace("-", " ")])
    tokens = []
    for w in re.findall(r"[A-Za-z]{3,}", raw.lower()):
        if w in INTENT_STOPWORDS:
            continue
        if w not in tokens:
            tokens.append(w)
    return tokens[:12]

def _looks_like_area_phrase(text: str) -> bool:
    if not text:
        return False
    return bool(re.search(
        r"\b(in|at|near)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}|[A-Z]{2,5})\b",
        text,
    ))

def _is_property_related(html: str, page_url: str) -> bool:
    slug = urlparse(page_url).path.strip("/").replace("-", " ").lower()
    if any(x in slug for x in ["for-sale", "for-rent", "/s/"]):
        return True
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    h1_text = clean(h1.get_text(" ")) if h1 else ""
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = clean(title_tag.get_text(" "))
    if _looks_like_area_phrase(" ".join([h1_text, title])):
        return True
    tokens = set(_intent_tokens_from_html(html, page_url))
    return any(t in PROPERTY_KEYWORDS for t in tokens)

def _is_lpv_or_ltp_link(href: str, base_dom: str) -> Tuple[bool, bool]:
    if not href:
        return (False, False)
    path = href
    if href.startswith("http"):
        dom = urlparse(href).netloc.lower().replace("www.", "")
        if base_dom and dom != base_dom:
            return (False, False)
        path = urlparse(href).path
    if href.startswith("//"):
        dom = urlparse("http:" + href).netloc.lower().replace("www.", "")
        if base_dom and dom != base_dom:
            return (False, False)
        path = urlparse("http:" + href).path
    lpv = (
        "/for-sale/property/" in path
        or "/for-rent/property/" in path
        or "/to-rent/property/" in path
    )
    ltp = path.startswith("/s/")
    return (lpv, ltp)

def _internal_linking_quality(html: str, page_url: str, word_count: int) -> str:
    if not html:
        return "Not available"
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all(list(IGNORE_TAGS)):
        t.decompose()
    root = soup.find("article") or soup.find("main") or soup
    links = root.find_all("a", href=True)
    base_dom = domain_of(page_url)
    total_links = 0
    internal = 0
    contextual = 0
    intent_support = 0
    lpv_count = 0
    ltp_count = 0
    is_property = _is_property_related(html, page_url)
    intent_tokens = _intent_tokens_from_html(html, page_url)
    for a in links:
        href = (a.get("href") or "").strip()
        if not href:
            continue
        if href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        total_links += 1
        is_internal = False
        if href.startswith("/"):
            is_internal = True
        elif href.startswith("http"):
            dom = urlparse(href).netloc.lower().replace("www.", "")
            if base_dom and dom == base_dom:
                is_internal = True
        elif href.startswith("//"):
            dom = urlparse("http:" + href).netloc.lower().replace("www.", "")
            if base_dom and dom == base_dom:
                is_internal = True
        else:
            is_internal = True
        if not is_internal:
            continue
        internal += 1
        anchor_text = clean(a.get_text(" ")).strip()
        anchor_low = anchor_text.lower()
        if anchor_text and anchor_low not in GENERIC_ANCHORS and len(anchor_text) >= 3:
            contextual += 1
        if intent_tokens and anchor_text:
            if any(tok in anchor_low for tok in intent_tokens):
                intent_support += 1
        if is_property:
            lpv, ltp = _is_lpv_or_ltp_link(href, base_dom)
            if lpv:
                lpv_count += 1
            elif ltp:
                ltp_count += 1
    if internal == 0:
        return "Weak (no internal links)"
    score = 0
    internal_ratio = 0.0
    if total_links > 0:
        internal_ratio = internal / max(total_links, 1)
        if internal_ratio >= 0.6 and internal >= 2:
            score += 1
    contextual_ratio = contextual / internal
    if contextual_ratio >= 0.6:
        score += 1
    intent_ok = intent_support >= 2 or (intent_support / internal) >= 0.4
    if intent_ok:
        score += 1
    bonus = 0
    if is_property:
        lpv_share = lpv_count / max(internal, 1)
        ltp_share = ltp_count / max(internal, 1)
        if lpv_count >= 2 or lpv_share >= 0.15:
            lpv_bonus = 2
        elif lpv_count == 1:
            lpv_bonus = 1
        else:
            lpv_bonus = 0
        if ltp_count >= 2 or ltp_share >= 0.15:
            ltp_bonus = 2
        elif ltp_count == 1:
            ltp_bonus = 1
        else:
            ltp_bonus = 0
        bonus = min(4, lpv_bonus + ltp_bonus)
        if internal >= 3 and lpv_count == 0 and ltp_count == 0:
            bonus -= 1
    final_score = score + bonus

    def pick_reason() -> str:
        reasons = []
        if internal < 2:
            reasons.append("few internal links")
        if total_links > 0 and internal_ratio < 0.6:
            reasons.append("low internal share")
        if contextual_ratio < 0.6:
            reasons.append("generic anchors")
        if not intent_ok:
            reasons.append("intent support low")
        if is_property:
            if lpv_count == 0 and ltp_count == 0:
                reasons.append("no LPV/LTP")
            elif bonus <= 1 and (lpv_count or ltp_count):
                reasons.append("low LPV/LTP")
        return reasons[0] if reasons else "needs stronger signals"

    if final_score >= 3:
        return "Strong"
    reason = pick_reason()
    if final_score == 2:
        return f"Medium ({reason})"
    return f"Weak ({reason})"

def _normalize_internal_linking_quality(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    df = df.copy()
    if "Internal Linking Quality" in df.columns and "Internal linking" not in df.columns:
        df = df.rename(columns={"Internal Linking Quality": "Internal linking"})
    if "Internal linking" not in df.columns:
        return df

    def to_label(val):
        if val is None:
            return val
        s = str(val).strip()
        if not s:
            return val
        s_low = s.lower()
        if s_low == "strong":
            return "Strong"
        if s_low in {"moderate", "medium"}:
            return "Medium"
        if s_low == "weak":
            return "Weak"
        if s.isdigit():
            n = int(s)
        else:
            try:
                n = int(float(s))
            except Exception:
                return val
        if n >= 8:
            return "Strong"
        if n >= 3:
            return "Medium"
        return "Weak"

    df["Internal linking"] = df["Internal linking"].map(to_label)
    return df

SPELLCHECK_ALLOWLIST = {
    "bayut",
    "dubai",
    "emirate",
    "emirates",
    "jumeirah",
    "deira",
    "mirdif",
    "dubailand",
    "sharjah",
    "ajman",
    "fujairah",
    "khaimah",
    "abudhabi",
    "abu",
    "dhabi",
    "marina",
    "downtown",
    "jbr",
    "jlt",
}
_CONSONANT_RUN_RE = re.compile(r"[bcdfghjklmnpqrstvwxyz]{5,}")

def _looks_like_misspelling(word: str) -> bool:
    if re.search(r"(.)\1\1", word):
        return True
    if not any(c in "aeiouy" for c in word):
        return True
    if _CONSONANT_RUN_RE.search(word):
        return True
    return False

def _misspelling_and_wrong_words(text: str) -> str:
    if not text:
        return "Not available"
    words = re.findall(r"[A-Za-z][A-Za-z']{2,}", text or "")
    if not words:
        return "Not available"
    issues = set()
    for w in words[:4000]:
        if w.isupper() or w[0].isupper():
            continue
        w = w.lower().strip("'")
        if w.endswith("'s"):
            w = w[:-2]
        if len(w) < 4:
            continue
        if w in SPELLCHECK_ALLOWLIST:
            continue
        if WORDFREQ_OK:
            if zipf_frequency(w, "en") <= 0:
                issues.add(w)
        else:
            if _looks_like_misspelling(w):
                issues.add(w)
        if len(issues) >= 200:
            break
    count = len(issues)
    if count == 0:
        return "None detected"
    examples = sorted(issues)[:5]
    suffix = ""
    if examples:
        suffix = f" ({', '.join(examples)}{' ...' if count > len(examples) else ''})"
    if count == 1:
        return "1 issue" + suffix
    return f"{count} issues" + suffix

CREDIBLE_KEYWORDS = ["gov", "edu", "who.int", "un.org", "worldbank", "statista", "imf", "oecd", "bbc", "nytimes", "guardian", "reuters", "wsj", "ft"]

def _credible_sources_count(html: str, page_url: str) -> int:
    if not html:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=True)
    seen = set()
    base_dom = domain_of(page_url)
    for a in links:
        href = a.get("href") or ""
        if not href.startswith("http"):
            continue
        dom = urlparse(href).netloc.lower().replace("www.", "")
        if dom == base_dom:
            continue
        if dom in seen:
            continue
        if any(k in dom for k in CREDIBLE_KEYWORDS) or dom.endswith(".gov") or dom.endswith(".edu") or dom.endswith(".org"):
            seen.add(dom)
    return len(seen)

def _styling_layout_label(html: str) -> str:
    if not html:
        return "Not available"
    soup = BeautifulSoup(html, "html.parser")
    root = _find_content_root(soup)
    score = 0
    signals = []

    tables = root.find_all("table")
    has_table = len(tables) > 0
    if has_table:
        score += 1
        signals.append("tables")

    has_ul = any(len(ul.find_all("li")) >= 2 for ul in root.find_all("ul"))
    if not has_ul:
        lines = root.get_text("\n").splitlines()
        bullet_lines = [ln for ln in lines if re.match(r"^\s*[-*•]\s+\S+", ln)]
        has_ul = len(bullet_lines) >= 2
    if has_ul:
        score += 1
        signals.append("bullet lists")

    has_ol = any(len(ol.find_all("li")) >= 2 for ol in root.find_all("ol"))
    step_heading = bool(re.search(r"\bstep\s*\d+", root.get_text(" "), re.I))
    if not has_ol:
        lines = root.get_text("\n").splitlines()
        num_lines = [ln for ln in lines if re.match(r"^\s*\d+[\).:-]\s+\S+", ln)]
        has_ol = len(num_lines) >= 2
    has_steps = has_ol or step_heading
    if has_steps:
        score += 1
        signals.append("steps/numbered")

    has_infographic = False
    has_visuals = False
    has_maps = False

    def _int_attr(v) -> int:
        try:
            return int(str(v).strip()) if v is not None and str(v).strip() != "" else 0
        except Exception:
            return 0

    def _img_parts(img):
        alt = clean(img.get("alt") or "").lower()
        title = clean(img.get("title") or "").lower()
        cls = " ".join(img.get("class") or []).lower()
        el_id = (img.get("id") or "").lower()
        src = (img.get("src") or img.get("data-src") or "").lower()
        blob = " | ".join([alt, title, cls, el_id, src])
        return alt, title, cls, blob

    def _is_map_like_image(img) -> bool:
        alt, title, _cls, blob = _img_parts(img)
        map_tokens = (
            "google map", "google maps", "maps.google", "maps.gstatic", "maps.googleapis",
            "mapbox", "openstreetmap", "leaflet", "street view", "staticmap",
            "location map", "map image", "gm-style"
        )
        if any(tok in blob for tok in map_tokens):
            return True
        if re.search(r"\bmap\b", alt) and re.search(r"\b(location|directions?|address|route)\b", alt):
            return True
        if re.search(r"\bmap\b", title) and re.search(r"\b(location|directions?|address|route)\b", title):
            return True
        return False

    def _is_decorative_image(img) -> bool:
        _alt, _title, _cls, blob = _img_parts(img)
        if any(tok in blob for tok in ("logo", "icon", "avatar", "emoji", "sprite", "favicon", "brandmark")):
            return True
        w = _int_attr(img.get("width"))
        h = _int_attr(img.get("height"))
        if w and h and w <= 120 and h <= 120:
            return True
        return False

    def _is_map_like_iframe(frame) -> bool:
        src = (frame.get("src") or "").lower()
        title = clean(frame.get("title") or "").lower()
        cls = " ".join(frame.get("class") or []).lower()
        el_id = (frame.get("id") or "").lower()
        blob = " | ".join([src, title, cls, el_id])
        map_tokens = (
            "google.com/maps",
            "maps.google",
            "maps/embed",
            "maps.gstatic",
            "maps.googleapis",
            "mapbox",
            "openstreetmap",
            "leaflet",
            "bing.com/maps",
            "here.com",
            "waze.com",
        )
        if any(tok in blob for tok in map_tokens):
            return True
        if "map" in title and any(tok in title for tok in ("location", "directions", "route")):
            return True
        return False

    def _is_map_like_link(a) -> bool:
        href = (a.get("href") or "").lower()
        if not href:
            return False
        txt = clean(a.get_text(" ")).lower()
        href_tokens = (
            "google.com/maps",
            "maps.google",
            "maps.app.goo.gl",
            "goo.gl/maps",
            "mapbox.com",
            "openstreetmap.org",
            "bing.com/maps",
            "waze.com",
            "here.com",
        )
        if any(tok in href for tok in href_tokens):
            return True
        if re.search(r"\b(view larger map|get directions|open in maps?)\b", txt):
            return True
        return False

    infographic_tokens = ("infographic", "chart", "graph", "diagram", "data visualization", "data viz")
    for img in root.find_all("img"):
        if _is_map_like_image(img):
            has_maps = True
            continue
        alt, title, _cls, _blob = _img_parts(img)
        if any(tok in alt or tok in title for tok in infographic_tokens):
            has_infographic = True
            break

    if not has_infographic:
        for img in root.find_all("img"):
            if _is_map_like_image(img):
                has_maps = True
                continue
            if _is_decorative_image(img):
                continue
            _alt, _title, cls, _blob = _img_parts(img)
            w = _int_attr(img.get("width"))
            h = _int_attr(img.get("height"))
            if "wp-image" in cls or "attachment" in cls or w >= 240 or h >= 180:
                has_visuals = True
                break

    if not has_infographic and not has_visuals:
        for fig in root.find_all("figure"):
            img = fig.find("img")
            if not img:
                continue
            if _is_map_like_image(img):
                has_maps = True
                continue
            if _is_decorative_image(img):
                continue
            has_visuals = True
            break

    for frame in root.find_all("iframe"):
        if _is_map_like_iframe(frame):
            has_maps = True
            break

    if not has_maps:
        for a in root.find_all("a", href=True):
            if _is_map_like_link(a):
                has_maps = True
                break

    if has_infographic or has_visuals or has_maps:
        score += 1
        if has_infographic:
            signals.append("infographics/charts")
        elif has_visuals:
            signals.append("images/visuals")
        if has_maps:
            signals.append("maps/location")

    if score >= 3:
        label = "Good"
    elif score >= 2:
        label = "OK"
    else:
        label = "Weak"
    if signals:
        return f"{label} ({', '.join(signals)})"
    return label

def _references_section_present(nodes: List[dict], html: str) -> str:
    # Rule: a real references section must appear near the end of article
    # and include source URLs listed under a references-like heading.
    allowed_labels = {
        "reference",
        "references",
        "source",
        "sources",
        "bibliography",
        "further reading",
        "works cited",
        "citation",
        "citations",
        "references and sources",
        "sources and references",
    }
    heading_tags = {"h1", "h2", "h3", "h4", "h5", "h6"}

    def is_reference_label(text: str) -> bool:
        h = norm_header(text)
        if not h:
            return False
        if h in allowed_labels:
            return True
        return bool(re.match(r"^(references?|sources?|citations?)(?:\s+(?:used|consulted))?$", h))

    def is_near_end(idx: int, total: int) -> bool:
        if total <= 0:
            return False
        # Last ~30% of headings, with a small-content safety floor.
        return idx >= max(total - 3, int(total * 0.70))

    def url_count_from_text(text: str) -> int:
        if not text:
            return 0
        return len({u.rstrip(").,;:") for u in URL_RE.findall(text)})

    def section_url_count_from_heading(tag) -> int:
        urls = set()
        for el in tag.find_all_next():
            if el is tag:
                continue
            name = getattr(el, "name", None)
            if name in heading_tags:
                break
            if name == "a":
                href = clean(el.get("href") or "")
                if href.startswith(("http://", "https://")):
                    urls.add(href.rstrip(").,;:"))
                elif href.startswith("//"):
                    urls.add(("https:" + href).rstrip(").,;:"))
            text_chunk = clean(el.get_text(" ")) if hasattr(el, "get_text") else ""
            if text_chunk:
                for u in URL_RE.findall(text_chunk):
                    urls.add(u.rstrip(").,;:"))
        return len(urls)

    # Text-only fallback (manual/Jina): heading near end + URL-like text in section content.
    flat = flatten(nodes or [])
    if flat:
        total = len(flat)
        for idx, node in enumerate(flat):
            if not is_reference_label(node.get("header", "")):
                continue
            if not is_near_end(idx, total):
                continue
            if url_count_from_text(node.get("content", "")) >= 1:
                return "Yes"

    if not html:
        return "No"

    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("article") or soup.find("main") or soup.body or soup
    headings = root.find_all(list(heading_tags))
    total_headings = len(headings)

    for idx, h in enumerate(headings):
        if not is_reference_label(clean(h.get_text(" "))):
            continue
        if not is_near_end(idx, total_headings):
            continue
        if section_url_count_from_heading(h) >= 1:
            return "Yes"

    return "No"

def _data_points_count(text: str) -> int:
    if not text:
        return 0
    matches = re.findall(r"\b\d{1,3}(?:[,\d]{0,})(?:\.\d+)?\b|\b\d+%|\b\d+\.\d+%", text)
    return len(matches)

def _data_backed_claims_count(text: str) -> int:
    if not text:
        return 0
    patterns = [r"according to", r"data from", r"study", r"survey", r"research", r"reported that", r"found that", r"statistics"]
    cnt = 0
    for p in patterns:
        cnt += len(re.findall(p, text, flags=re.I))
    return cnt

STRONG_WORDS_RE = r"\b(best|worst|always|never|guarantee|guaranteed|unbeatable|the most|the best|huge|massive)\b"

def _unsupported_strong_claims_count(text: str) -> int:
    if not text:
        return 0
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cnt = 0
    for s in sentences:
        if re.search(STRONG_WORDS_RE, s, flags=re.I):
            if not re.search(r"\d", s):
                cnt += 1
    return cnt

def _latest_information_label(last_modified: str, text: str) -> str:
    lm = (last_modified or "").lower()
    y = _latest_year_mentioned(text or "")
    if ("2026" in lm) or ("2025" in lm) or y >= 2025:
        return "Likely up-to-date"
    if y >= 2024:
        return "Somewhat recent"
    return "Unclear/Older"

def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [clean(p) for p in parts if clean(p)]

def _extract_years(s: str) -> List[int]:
    years = []
    for y in re.findall(r"\b(19\d{2}|20\d{2})\b", s or ""):
        try:
            years.append(int(y))
        except Exception:
            continue
    return years

def _shorten_outdated_snippet(text: str, limit: int = 120) -> str:
    if not text:
        return ""
    txt = re.sub(r"\s+", " ", text).strip()
    if len(txt) <= limit:
        return txt
    cut = txt[:limit].rsplit(" ", 1)[0]
    if not cut:
        cut = txt[:limit]
    return cut + "..."

def _outdated_snippets(text: str, max_year: int = 2023, limit: int = 6) -> List[str]:
    if not text:
        return []
    out = []
    seen = set()
    for s in _split_sentences(text):
        yrs = _extract_years(s)
        if not yrs:
            continue
        if any(y <= max_year for y in yrs):
            key = norm_header(s)
            if key and key not in seen:
                seen.add(key)
                out.append(_shorten_outdated_snippet(s))
        if len(out) >= limit:
            break
    return out

def _strong_claim_snippets(text: str, limit: int = 6) -> List[str]:
    if not text:
        return []
    out = []
    seen = set()
    for s in _split_sentences(text):
        if re.search(STRONG_WORDS_RE, s, flags=re.I) and not re.search(r"\d", s):
            key = norm_header(s)
            if key and key not in seen:
                seen.add(key)
                out.append(s)
        if len(out) >= limit:
            break
    return out

def _outdated_misleading_cell(last_modified: str, text: str) -> str:
    lm = clean(last_modified or "")
    lm_years = _extract_years(lm)
    outdated_items = _outdated_snippets(text, max_year=2023, limit=6)
    if lm_years and max(lm_years) <= 2023:
        outdated_items.insert(0, f"Last modified date: {lm}")
    if not outdated_items:
        return "No obvious issues"

    label = "Outdated info"

    def as_list(items: List[str]) -> str:
        lis = "".join(f"<li>{html_lib.escape(i)}</li>" for i in items)
        return f"<ul>{lis}</ul>" if lis else ""

    detail_html = "<div><strong>Outdated signals</strong>" + as_list(outdated_items) + "</div>"
    return (
        "<details class='details-link'>"
        f"<summary><span class='link-like'>{html_lib.escape(label)}</span></summary>"
        f"<div class='details-box'>{detail_html}</div>"
        "</details>"
    )

def normalize_url_for_match(u: str) -> str:
    try:
        p = urlparse(u)
        host = p.netloc.lower().replace("www.", "")
        path = (p.path or "").rstrip("/")
        return host + path
    except Exception:
        return (u or "").strip().lower().replace("www.", "").rstrip("/")

def _dataforseo_site_result_count(data: dict, dom: str, target_norm: str) -> int:
    if not isinstance(data, dict):
        return 0
    others = set()
    tasks = data.get("tasks") or []
    for task in tasks:
        if task.get("status_code") != 20000:
            continue
        for res in task.get("result") or []:
            for item in res.get("items") or []:
                if item.get("type") not in {"organic", "organic_extended"}:
                    continue
                url = item.get("url") or ""
                if not url:
                    continue
                nm = normalize_url_for_match(url)
                if dom in nm and nm != target_norm:
                    others.add(url)
    return len(others)

def _topic_cannibalization_label(query: str, page_url: str) -> str:
    dom = domain_of(page_url)
    if not dom or not query or query == "Not available":
        return "Not available"
    site_q = f"site:{dom} {query}"
    target = normalize_url_for_match(page_url)

    if DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD:
        data = dataforseo_serp_cached(site_q, device="desktop")
        if not (isinstance(data, dict) and data.get("_error")):
            cnt = _dataforseo_site_result_count(data, dom, target)
            if cnt >= 3:
                return f"High risk (≈{cnt} other pages on same domain)"
            if cnt >= 1:
                return f"Medium risk (≈{cnt} other page(s) on same domain)"
            return "Low risk"
        return f"Not available ({data.get('_error')})" if isinstance(data, dict) else "Not available"

    if not SERPAPI_API_KEY:
        return "Not available (no DataForSEO credentials)"
    data = serpapi_serp_cached(site_q, device="desktop")
    if not data or data.get("_error"):
        return f"Not available ({data.get('_error')})" if isinstance(data, dict) else "Not available"

    organic = data.get("organic_results") or []
    others = []
    for it in organic:
        link = it.get("link") or ""
        if not link:
            continue
        nm = normalize_url_for_match(link)
        if dom in nm and nm != target:
            others.append(link)

    cnt = len(set(others))
    if cnt >= 3:
        return f"High risk (≈{cnt} other pages on same domain)"
    if cnt >= 1:
        return f"Medium risk (≈{cnt} other page(s) on same domain)"
    return "Low risk"

def _topic_tokens_from_nodes(nodes: List[dict]) -> List[str]:
    h1 = get_first_h1(nodes)
    h2s = []
    for x in flatten(nodes):
        if x.get("level") == 2:
            h = clean(x.get("header", ""))
            if h and not is_noise_header(h):
                h2s.append(h)
        if len(h2s) >= 8:
            break
    raw = clean(" ".join([h1] + h2s))
    tokens = [w for w in norm_header(raw).split() if len(w) >= 3]
    return tokens

def _topic_similarity_score(a_nodes: List[dict], b_nodes: List[dict]) -> float:
    h1_a = get_first_h1(a_nodes)
    h1_b = get_first_h1(b_nodes)
    h1_score = header_similarity(h1_a, h1_b)
    a_tokens = set(_topic_tokens_from_nodes(a_nodes))
    b_tokens = set(_topic_tokens_from_nodes(b_nodes))
    if a_tokens and b_tokens:
        jacc = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
    else:
        jacc = 0.0
    return max(h1_score, jacc)

def _domain_topic_cannibalization_label(
    page_url: str,
    domain_nodes_map: Dict[str, Dict[str, List[dict]]],
) -> str:
    dom = domain_of(page_url)
    if not dom:
        return "Not available"
    url_map = domain_nodes_map.get(dom) or {}
    target_nodes = url_map.get(page_url) or []
    if not target_nodes:
        return "Not available"
    overlap = 0
    for url, nodes in url_map.items():
        if url == page_url:
            continue
        if _topic_similarity_score(target_nodes, nodes) >= 0.7:
            overlap += 1
    if overlap >= 2:
        return f"High risk (≈{overlap} other pages)"
    if overlap >= 1:
        return "Medium risk (≈1 other page)"
    return "Low risk"

def build_content_quality_table_from_seo(
    seo_df: pd.DataFrame,
    fr_map_by_url: Dict[str, FetchResult],
    tree_map_by_url: Dict[str, dict],
    manual_query: str = "",
    manual_query_secondary: str = ""
) -> pd.DataFrame:
    if seo_df is None or seo_df.empty:
        return pd.DataFrame()

    cols = [
        "Page","Last Updated / Modified","Topic Cannibalization","Keyword Stuffing",
        "FAQs","References Section",
        "Internal linking","Misspelling & Wrong Words","Latest Information Score",
        "Outdated / Misleading Info","Styling / Layout",
    ]

    domain_nodes_map: Dict[str, Dict[str, List[dict]]] = {}
    for url, tr in (tree_map_by_url or {}).items():
        if not url:
            continue
        dom = domain_of(url)
        if not dom:
            continue
        nodes = tr.get("nodes", []) if isinstance(tr, dict) else []
        if not nodes:
            continue
        domain_nodes_map.setdefault(dom, {})[url] = nodes

    rows = []
    for _, r in seo_df.iterrows():
        page = str(r.get("Page", "")).strip()
        page_url = str(r.get("__url", "")).strip()

        if not page_url or page_url == "Not applicable":
            rows.append({c: "Not applicable" for c in cols})
            rows[-1]["Page"] = page
            continue

        fr = fr_map_by_url.get(page_url)
        tr = tree_map_by_url.get(page_url) or {}
        nodes = tr.get("nodes", []) if isinstance(tr, dict) else []

        html = (fr.html if fr else "") or ""
        text = (fr.text if fr else "") or ""
        content_text = content_text_from_html(html, include_headings=False) if html else ""
        if not content_text:
            content_text = content_text_from_plaintext(text, include_headings=False)
        if word_count_from_text(content_text) < 120 and text:
            fallback_text = content_text_from_plaintext_lenient(text)
            if word_count_from_text(fallback_text) > word_count_from_text(content_text):
                content_text = fallback_text
        if word_count_from_text(content_text) < 120 and text:
            content_text = clean(text)
        wc_text = content_text_from_html(html, include_headings=True) if html else ""
        if not wc_text:
            wc_text = content_text_from_plaintext(text, include_headings=True)

        wc_body = word_count_from_text(content_text)
        lm = get_last_modified(page_url, html, text)

        fkw = clean(manual_query) if clean(manual_query) else str(r.get("__fkw", ""))
        fkw_secondary = clean(manual_query_secondary) if clean(manual_query_secondary) else ""
        rep_s = compute_kw_repetition(content_text, fkw) if fkw and fkw != "Not available" else "0"
        try:
            rep_i = int(rep_s)
        except Exception:
            rep_i = 0

        is_bayut = page.strip().lower() == "bayut" or domain_of(page_url).endswith("bayut.com")
        topic_cann = _domain_topic_cannibalization_label(page_url, domain_nodes_map)
        kw_stuff = _kw_stuffing_label(wc_body, rep_i)
        if fkw_secondary and fkw_secondary != fkw:
            rep2_s = compute_kw_repetition(content_text, fkw_secondary)
            try:
                rep2_i = int(rep2_s)
                kw_stuff_secondary = _kw_stuffing_label(wc_body, rep2_i)
            except Exception:
                kw_stuff_secondary = "Not available"
            kw_stuff = f"Primary: {kw_stuff} | Secondary: {kw_stuff_secondary}"

        faqs = "Yes" if (fr and page_has_real_faq(fr, nodes)) else "No"
        refs = _references_section_present(nodes, html)
        internal_quality = _internal_linking_quality(html, page_url, wc_body)
        misspell = _misspelling_and_wrong_words(content_text if content_text else text) if is_bayut else "-"
        latest_score = _latest_information_label(lm, text)
        outdated = _outdated_misleading_cell(lm, text)
        styling = _styling_layout_label(html)

        rows.append({
            "Page": page,
            "Last Updated / Modified": lm,
            "Topic Cannibalization": topic_cann,
            "Keyword Stuffing": kw_stuff,
            "FAQs": faqs,
            "References Section": refs,
            "Internal linking": internal_quality,
            "Misspelling & Wrong Words": misspell,
            "Latest Information Score": latest_score,
            "Outdated / Misleading Info": outdated,
            "Styling / Layout": styling,
        })

    return pd.DataFrame(rows, columns=cols)


# =====================================================
# NEW POST MODE helpers
# =====================================================
def list_headers(nodes: List[dict], level: int) -> List[str]:
    return [x["header"] for x in flatten(nodes) if x["level"] == level and not is_noise_header(x["header"])]

def detect_main_angle(comp_nodes: List[dict]) -> str:
    h2s = [norm_header(h) for h in list_headers(comp_nodes, 2)]
    blob = " ".join(h2s)
    if ("pros" in blob and "cons" in blob) or ("advantages" in blob and "disadvantages" in blob):
        return "pros-and-cons decision guide"
    if "payment plan" in blob:
        return "buyer decision / payment-plan-led guide"
    if "amenities" in blob and "location" in blob:
        return "community overview for buyers"
    return "decision-led overview"

def new_post_coverage_rows(comp_nodes: List[dict], comp_url: str) -> List[dict]:
    h1s = list_headers(comp_nodes, 1)
    h1_title = strip_label(h1s[0]) if h1s else ""
    angle = detect_main_angle(comp_nodes)
    h1_text = f"{h1_title} — The competitor frames the page as a {angle}." if h1_title else f"The competitor frames the page as a {angle}."

    h2s = [strip_label(h) for h in list_headers(comp_nodes, 2)]
    h2_main = [h for h in h2s if h and not header_is_faq(h)]
    h2_main = h2_main[:6]
    h2_text = "Major sections include: " + " → ".join(h2_main) + "." if h2_main else "Major sections introduce the topic, break down key points, and end with wrap-up context."

    h3s = [strip_label(h) for h in list_headers(comp_nodes, 3)]
    themes, seen = [], set()
    for h in h3s:
        if not h or is_noise_header(h) or header_is_faq(h):
            continue
        k = norm_header(h)
        if k in seen:
            continue
        seen.add(k)
        themes.append(h)
        if len(themes) >= 7:
            break
    h3_text = "Subsections break sections into practical themes such as: " + ", ".join(themes) + "." if themes else "Subsections add practical depth inside each major section."

    return [
        {"Headers covered": "H1 (main angle)", "Content covered": h1_text, "Source": site_name(comp_url)},
        {"Headers covered": "H2 (sections covered)", "Content covered": h2_text, "Source": site_name(comp_url)},
        {"Headers covered": "H3 (subsections covered)", "Content covered": h3_text, "Source": site_name(comp_url)},
    ]


# =====================================================
# HTML TABLE RENDER (UPDATED: use data-table class)
# =====================================================
def render_table(df: pd.DataFrame, drop_internal_url: bool = True):
    if df is None or df.empty:
        st.info("No results to show.")
        return
    if "Headers" in df.columns and "Description" in df.columns:
        df = df.copy()
        def _normalize_faq_desc(row):
            header = str(row.get("Headers", "")).strip().lower()
            if header == "faqs":
                return _inline_numbered_from_html_list(row.get("Description", ""))
            return row.get("Description", "")
        df["Description"] = df.apply(_normalize_faq_desc, axis=1)
    if drop_internal_url:
        drop_cols = [c for c in df.columns if c.startswith("__")]
        if drop_cols:
            df = df.drop(columns=drop_cols)
    df = _normalize_internal_linking_quality(df)
    if "Internal linking" in df.columns:
        df = df.copy()
        def _ensure_internal_reason(val):
            s = "" if val is None else str(val).strip()
            if "(" in s:
                return s
            low = s.lower()
            if low.startswith("medium"):
                return "Medium (needs stronger signals)"
            if low.startswith("weak"):
                return "Weak (few strong signals)"
            return s
        df["Internal linking"] = df["Internal linking"].apply(_ensure_internal_reason)
        rule_lines = [
            "Base: +1 internal share, +1 descriptive anchors, +1 intent support.",
            "Property bonus: LPV/LTP (count>=2 or share>=0.15 → +2; count=1 → +1).",
            "Bonus cap 4; if internal>=3 and no LPV/LTP, bonus -1.",
            "Final = base + bonus. Strong≥3, Medium=2, Weak≤1.",
            "Property-related = area or sale/rent/buy intent.",
        ]
        rule_html = "".join(f"<li>{html_lib.escape(item)}</li>" for item in rule_lines)
        header_html = (
            "Internal linking "
            "<input type='checkbox' id='internal-linking-rule-toggle' class='rule-toggle'/>"
            "<label for='internal-linking-rule-toggle' class='rule-trigger'>ⓘ</label>"
            "<div class='rule-modal'>"
            "<label for='internal-linking-rule-toggle' class='rule-backdrop'></label>"
            "<div class='rule-card'>"
            "<h4>Internal linking rule</h4>"
            "<label for='internal-linking-rule-toggle' class='rule-close'>×</label>"
            f"<ul>{rule_html}</ul>"
            "</div>"
            "</div>"
        )
        df = df.rename(columns={"Internal linking": header_html})
    html = df.to_html(index=False, escape=False, classes="data-table")
    st.markdown(html, unsafe_allow_html=True)

def rules_modal_html(title: str, rule_lines: List[str], toggle_id: str) -> str:
    rule_html = "".join(f"<li>{html_lib.escape(item)}</li>" for item in rule_lines)
    return (
        f"<input type='checkbox' id='{toggle_id}' class='rule-toggle'/>"
        f"<label for='{toggle_id}' class='rule-trigger'>ⓘ</label>"
        "<div class='rule-modal'>"
        f"<label for='{toggle_id}' class='rule-backdrop'></label>"
        "<div class='rule-card'>"
        f"<h4>{html_lib.escape(title)}</h4>"
        f"<label for='{toggle_id}' class='rule-close'>×</label>"
        f"<ul>{rule_html}</ul>"
        "</div>"
        "</div>"
    )

ICON_LINK = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M10 13a5 5 0 0 1 0-7l1.6-1.6a5 5 0 0 1 7.1 7.1L17 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M14 11a5 5 0 0 1 0 7l-1.6 1.6a5 5 0 0 1-7.1-7.1L7 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

ICON_LIST = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M8 6h12M8 12h12M8 18h12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  <circle cx="4" cy="6" r="1.5" fill="currentColor"/>
  <circle cx="4" cy="12" r="1.5" fill="currentColor"/>
  <circle cx="4" cy="18" r="1.5" fill="currentColor"/>
</svg>
"""

ICON_SEARCH = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="11" cy="11" r="6" stroke="currentColor" stroke-width="2"/>
  <path d="M20 20l-3.6-3.6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

ICON_DOC = """
<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
  <path d="M14 2v6h6" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
  <path d="M9 12h6M9 16h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>
"""

def render_field_label(title: str, meta: str = "", icon_svg: str = ""):
    meta_html = f"<span class='label-meta'>{html_lib.escape(meta)}</span>" if meta else ""
    icon_html = f"<span class='label-icon'>{icon_svg}</span>" if icon_svg else ""
    st.markdown(
        f"<div class='field-label'>{icon_html}<span>{html_lib.escape(title)}</span>{meta_html}</div>",
        unsafe_allow_html=True,
    )

def render_empty_state(title: str, body: str):
    st.markdown(
        f"""
<div class="empty-card">
  <div class="empty-icon">{ICON_SEARCH}</div>
  <div class="empty-title">{html_lib.escape(title)}</div>
  <div class="empty-body">{html_lib.escape(body)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def section_header_pill(title: str, rules_html: str = ""):
    st.markdown(
        f"<div class='section-title'>{html_lib.escape(title)}{rules_html}</div>",
        unsafe_allow_html=True,
    )


# =====================================================
# MODE SELECTOR (CENTERED BUTTONS)
# =====================================================
if "mode" not in st.session_state:
    st.session_state.mode = "update"  # "update" or "new"

st.markdown("<div class='mode-toggle'>", unsafe_allow_html=True)
outer_l, outer_m, outer_r = st.columns([1, 2.2, 1])
with outer_m:
    b1, b2 = st.columns(2)
    with b1:
        if st.button(
            "Update Mode",
            type="primary" if st.session_state.mode == "update" else "secondary",
            use_container_width=True,
            key="mode_update_btn",
        ):
            st.session_state.mode = "update"
    with b2:
        if st.button(
            "New Post Mode",
            type="primary" if st.session_state.mode == "new" else "secondary",
            use_container_width=True,
            key="mode_new_btn",
        ):
            st.session_state.mode = "new"
st.markdown("</div>", unsafe_allow_html=True)

mode_hint = (
    "Compare an existing Bayut article against competitors to find gaps."
    if st.session_state.mode == "update"
    else "Use competitor coverage to shape a new Bayut post outline."
)
st.markdown(f"<div class='mode-hint'>{html_lib.escape(mode_hint)}</div>", unsafe_allow_html=True)

show_internal_fetch = st.sidebar.checkbox("Admin: show internal fetch log", value=False)

# session state
for k, default in [
    ("update_df", pd.DataFrame()),
    ("update_fetch", []),
    ("seo_update_df", pd.DataFrame()),
    ("ai_update_df", pd.DataFrame()),
    ("cq_update_df", pd.DataFrame()),
    ("ai_vis_update_df", pd.DataFrame()),
    ("new_df", pd.DataFrame()),
    ("new_fetch", []),
    ("seo_new_df", pd.DataFrame()),
    ("ai_new_df", pd.DataFrame()),
    ("cq_new_df", pd.DataFrame()),
    ("ai_vis_new_df", pd.DataFrame()),
]:
    if k not in st.session_state:
        st.session_state[k] = default


# =====================================================
# UI - UPDATE MODE
# =====================================================
if st.session_state.mode == "update":
    with st.form("update_form"):
        render_field_label("Bayut Article URL", icon_svg=ICON_LINK)
        bayut_url = st.text_input(
            "Bayut Article URL",
            placeholder="https://www.bayut.com/mybayut/...",
            label_visibility="collapsed",
        )
        render_field_label("Competitor URLs", meta="(one per line)", icon_svg=ICON_LIST)
        competitors_text = st.text_area(
            "Competitor URLs",
            height=130,
            placeholder="https://example.com/article\nhttps://example.com/another",
            label_visibility="collapsed",
        )
        render_field_label("Focus Keyword", meta="(optional)", icon_svg=ICON_SEARCH)
        manual_fkw_update = st.text_input(
            "Focus Keyword",
            placeholder="e.g., pros and cons business bay",
            label_visibility="collapsed",
        )
        render_field_label("Secondary Keyword", meta="(optional)", icon_svg=ICON_SEARCH)
        manual_fkw2_update = st.text_input(
            "Secondary Keyword",
            placeholder="e.g., living in business bay",
            label_visibility="collapsed",
        )
        run = st.form_submit_button("Run Analysis", type="primary", use_container_width=True)

    competitors = [c.strip() for c in competitors_text.splitlines() if c.strip()]

    if run:
        if not bayut_url.strip():
            st.error("Bayut article URL is required.")
            st.stop()
        if not competitors:
            st.error("Add at least one competitor URL.")
            st.stop()

        with st.spinner("Fetching Bayut…"):
            bayut_fr_map = resolve_all_or_require_manual(agent, [bayut_url.strip()], st_key_prefix="bayut")
        bayut_fr = bayut_fr_map[bayut_url.strip()]
        if not bayut_fr.ok:
            st.warning("Bayut URL appears protected/blocked and could not be fetched automatically.")
            st.stop()
        bayut_tree_map = ensure_headings_or_require_repaste([bayut_url.strip()], bayut_fr_map, st_key_prefix="bayut_tree")
        bayut_nodes = bayut_tree_map[bayut_url.strip()]["nodes"]

        with st.spinner("Fetching competitors…"):
            comp_fr_map = resolve_all_or_require_manual(agent, competitors, st_key_prefix="comp_update")
        usable_competitors, skipped_competitors = split_fetch_results(competitors, comp_fr_map)
        if skipped_competitors and usable_competitors:
            st.info(
                f"Skipped {len(skipped_competitors)} protected/unfetchable competitor URL(s) and continued "
                f"with {len(usable_competitors)}."
            )
        if not usable_competitors:
            if len(competitors) == 1:
                st.warning("The competitor website is protected/blocked and could not be fetched automatically.")
            else:
                st.warning("All competitor websites were protected/blocked or unreachable, so there is nothing to analyze.")
            st.stop()
        comp_tree_map = ensure_headings_or_require_repaste(
            usable_competitors, comp_fr_map, st_key_prefix="comp_update_tree"
        )

        all_rows = []
        internal_fetch = []

        for comp_url in usable_competitors:
            src = comp_fr_map[comp_url].source
            internal_fetch.append((comp_url, f"ok ({src})"))
            comp_nodes = comp_tree_map[comp_url]["nodes"]

            all_rows.extend(update_mode_rows_header_first(
                bayut_nodes=bayut_nodes,
                bayut_fr=bayut_fr,
                comp_nodes=comp_nodes,
                comp_fr=comp_fr_map[comp_url],
                comp_url=comp_url,
            ))
        for comp_url in skipped_competitors:
            internal_fetch.append((comp_url, f"skipped ({fetch_failure_label(comp_fr_map.get(comp_url))})"))

        st.session_state.update_fetch = internal_fetch
        st.session_state.update_df = (
            pd.DataFrame(all_rows)[["Headers", "Description", "Source"]]
            if all_rows
            else pd.DataFrame(columns=["Headers", "Description", "Source"])
        )

        st.session_state.seo_update_df = build_seo_analysis_update(
            bayut_url=bayut_url.strip(),
            bayut_fr=bayut_fr,
            bayut_nodes=bayut_nodes,
            competitors=usable_competitors,
            comp_fr_map=comp_fr_map,
            comp_tree_map=comp_tree_map,
            manual_fkw=manual_fkw_update.strip()
        )

        st.session_state.seo_update_df, st.session_state.ai_update_df = enrich_seo_df_with_rank_and_ai(
            st.session_state.seo_update_df,
            manual_query=manual_fkw_update.strip()
        )

        st.session_state.cq_update_df = build_content_quality_table_from_seo(
            seo_df=st.session_state.seo_update_df,
            fr_map_by_url={bayut_url.strip(): bayut_fr, **{u: comp_fr_map[u] for u in usable_competitors}},
            tree_map_by_url={bayut_url.strip(): {"nodes": bayut_nodes}, **{u: comp_tree_map[u] for u in usable_competitors}},
            manual_query=manual_fkw_update.strip(),
            manual_query_secondary=manual_fkw2_update.strip()
        )

        query_for_ai = manual_fkw_update.strip() or get_first_h1(bayut_nodes)
        st.session_state.ai_vis_update_df = build_ai_visibility_table(
            query=query_for_ai,
            target_url=bayut_url.strip(),
            competitors=usable_competitors,
            device="mobile",
        )

    if show_internal_fetch and st.session_state.update_fetch:
        st.sidebar.markdown("### Internal fetch log (Update Mode)")
        st.sidebar.write(f"Playwright enabled: {PLAYWRIGHT_OK}")
        for u, s in st.session_state.update_fetch:
            st.sidebar.write(u, "—", s)

    has_update_results = any(
        df is not None and not df.empty
        for df in [
            st.session_state.update_df,
            st.session_state.cq_update_df,
            st.session_state.seo_update_df,
            st.session_state.ai_vis_update_df,
        ]
    )

    if not has_update_results:
        render_empty_state(
            "No Analysis Yet",
            "Enter your URLs above and run the analysis to see competitor gap insights, SEO comparison, and content quality signals.",
        )
    else:
        gaps_rules = [
            "Compare H2/H3 headings only (FAQ/noise headers excluded).",
            "Competitor H2 with no Bayut match (similarity >= 0.73) becomes a missing section.",
            "If matched, missing competitor H3 subtopics are listed.",
            "Depth gap note appears when competitor coverage is >=30% longer (>=140 chars) and includes missing themes.",
            "Orphan H3s (no H2 parent) are matched against Bayut H2/H3; unmatched ones are included.",
            "FAQs: if competitor has a real FAQ and Bayut lacks questions, a FAQs row is added; rows deduped per source.",
        ]
        gaps_rules_html = rules_modal_html(
            title="Gaps Table rules",
            rule_lines=gaps_rules,
            toggle_id="gaps-table-rules-toggle",
        )
        section_header_pill("Gaps Table", rules_html=gaps_rules_html)
        if st.session_state.update_df is None or st.session_state.update_df.empty:
            st.info("No gaps detected yet. Add more competitors or refine URLs.")
        else:
            render_table(st.session_state.update_df)

        section_header_pill("Content Quality")
        if st.session_state.cq_update_df is None or st.session_state.cq_update_df.empty:
            st.info("Run analysis to see Content Quality signals.")
        else:
            render_table(st.session_state.cq_update_df, drop_internal_url=True)

        section_header_pill("SEO Analysis")
        if st.session_state.seo_update_df is None or st.session_state.seo_update_df.empty:
            st.info("Run analysis to see SEO comparison.")
        else:
            render_table(st.session_state.seo_update_df, drop_internal_url=True)

        section_header_pill("AI Visibility")
        if st.session_state.ai_vis_update_df is None or st.session_state.ai_vis_update_df.empty:
            st.info("Run analysis to see AI visibility signals.")
        else:
            render_table(st.session_state.ai_vis_update_df, drop_internal_url=True)


# =====================================================
# UI - NEW POST MODE
# =====================================================
else:
    with st.form("new_post_form"):
        render_field_label("New Post Title", icon_svg=ICON_DOC)
        new_title = st.text_input(
            "New Post Title",
            placeholder="Pros & Cons of Living in Business Bay (2026)",
            label_visibility="collapsed",
        )
        render_field_label("Competitor URLs", meta="(one per line)", icon_svg=ICON_LIST)
        competitors_text = st.text_area(
            "Competitor URLs",
            height=130,
            placeholder="https://example.com/article\nhttps://example.com/another",
            label_visibility="collapsed",
        )
        render_field_label("Focus Keyword", meta="(optional)", icon_svg=ICON_SEARCH)
        manual_fkw_new = st.text_input(
            "Focus Keyword",
            placeholder="e.g., pros and cons business bay",
            label_visibility="collapsed",
        )
        render_field_label("Secondary Keyword", meta="(optional)", icon_svg=ICON_SEARCH)
        manual_fkw2_new = st.text_input(
            "Secondary Keyword",
            placeholder="e.g., living in business bay",
            label_visibility="collapsed",
        )
        run = st.form_submit_button("Generate Coverage", type="primary", use_container_width=True)

    competitors = [c.strip() for c in competitors_text.splitlines() if c.strip()]

    if run:
        if not new_title.strip():
            st.error("New post title is required.")
            st.stop()
        if not competitors:
            st.error("Add at least one competitor URL.")
            st.stop()

        with st.spinner("Fetching competitors…"):
            comp_fr_map = resolve_all_or_require_manual(agent, competitors, st_key_prefix="comp_new")
        usable_competitors, skipped_competitors = split_fetch_results(competitors, comp_fr_map)
        if skipped_competitors and usable_competitors:
            st.info(
                f"Skipped {len(skipped_competitors)} protected/unfetchable competitor URL(s) and continued "
                f"with {len(usable_competitors)}."
            )
        if not usable_competitors:
            if len(competitors) == 1:
                st.warning("The competitor website is protected/blocked and could not be fetched automatically.")
            else:
                st.warning("All competitor websites were protected/blocked or unreachable, so there is nothing to analyze.")
            st.stop()
        comp_tree_map = ensure_headings_or_require_repaste(
            usable_competitors, comp_fr_map, st_key_prefix="comp_new_tree"
        )

        rows = []
        internal_fetch = []

        for comp_url in usable_competitors:
            src = comp_fr_map[comp_url].source
            internal_fetch.append((comp_url, f"ok ({src})"))
            comp_nodes = comp_tree_map[comp_url]["nodes"]
            rows.extend(new_post_coverage_rows(comp_nodes, comp_url))
        for comp_url in skipped_competitors:
            internal_fetch.append((comp_url, f"skipped ({fetch_failure_label(comp_fr_map.get(comp_url))})"))

        st.session_state.new_fetch = internal_fetch
        st.session_state.new_df = (
            pd.DataFrame(rows)[["Headers covered", "Content covered", "Source"]]
            if rows
            else pd.DataFrame(columns=["Headers covered", "Content covered", "Source"])
        )

        st.session_state.seo_new_df = build_seo_analysis_newpost(
            new_title=new_title.strip(),
            competitors=usable_competitors,
            comp_fr_map=comp_fr_map,
            comp_tree_map=comp_tree_map,
            manual_fkw=manual_fkw_new.strip()
        )

        st.session_state.seo_new_df, st.session_state.ai_new_df = enrich_seo_df_with_rank_and_ai(
            st.session_state.seo_new_df,
            manual_query=manual_fkw_new.strip()
        )

        st.session_state.cq_new_df = build_content_quality_table_from_seo(
            seo_df=st.session_state.seo_new_df,
            fr_map_by_url={u: comp_fr_map[u] for u in usable_competitors},
            tree_map_by_url={u: comp_tree_map[u] for u in usable_competitors},
            manual_query=manual_fkw_new.strip(),
            manual_query_secondary=manual_fkw2_new.strip()
        )

        query_for_ai = manual_fkw_new.strip() or new_title.strip()
        st.session_state.ai_vis_new_df = build_ai_visibility_table(
            query=query_for_ai,
            target_url="Not applicable",
            competitors=usable_competitors,
            device="mobile",
        )

    if show_internal_fetch and st.session_state.new_fetch:
        st.sidebar.markdown("### Internal fetch log (New Post Mode)")
        st.sidebar.write(f"Playwright enabled: {PLAYWRIGHT_OK}")
        for u, s in st.session_state.new_fetch:
            st.sidebar.write(u, "—", s)

    has_new_results = any(
        df is not None and not df.empty
        for df in [
            st.session_state.new_df,
            st.session_state.cq_new_df,
            st.session_state.seo_new_df,
            st.session_state.ai_vis_new_df,
        ]
    )

    if not has_new_results:
        render_empty_state(
            "No Analysis Yet",
            "Enter your competitor URLs above and generate coverage to see insights.",
        )
    else:
        section_header_pill("Competitor Coverage")
        if st.session_state.new_df is None or st.session_state.new_df.empty:
            st.info("Generate competitor coverage to see results.")
        else:
            render_table(st.session_state.new_df)

        section_header_pill("Content Quality")
        if st.session_state.cq_new_df is None or st.session_state.cq_new_df.empty:
            st.info("Generate competitor coverage to see Content Quality signals.")
        else:
            render_table(st.session_state.cq_new_df, drop_internal_url=True)

        section_header_pill("SEO Analysis")
        if st.session_state.seo_new_df is None or st.session_state.seo_new_df.empty:
            st.info("Generate competitor coverage to see SEO comparison.")
        else:
            render_table(st.session_state.seo_new_df, drop_internal_url=True)

    # AI Visibility table removed for new post mode per request.

if (st.session_state.seo_update_df is not None and not st.session_state.seo_update_df.empty) or \
   (st.session_state.seo_new_df is not None and not st.session_state.seo_new_df.empty):
    if not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD) and not SERPAPI_API_KEY:
        st.warning(
            "Note: Add DATAFORSEO_LOGIN/DATAFORSEO_PASSWORD (or DATAFORSEO_API_LOGIN/DATAFORSEO_API_PASSWORD)"
            " or SERPAPI_API_KEY to enable Topic Cannibalization and AI Visibility."
        )

st.markdown(
    "<div class='footer-note'>Bayut Competitor Gap Analysis Tool - Built for content optimization</div>",
    unsafe_allow_html=True,
)
