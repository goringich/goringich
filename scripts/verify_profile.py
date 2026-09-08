#!/usr/bin/env python3

from __future__ import annotations

import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"

MARKDOWN_URL_RE = re.compile(r"\]\((https?://[^)\s]+)\)")
HTML_URL_RE = re.compile(r"(?:href|src|srcset)=\"(https?://[^\"]+)\"", re.IGNORECASE)
AUTOLINK_URL_RE = re.compile(r"<((?:https?://)[^>\s]+)>")
LOCAL_IMAGE_RE = re.compile(r"<(?:img|source)[^>]+(?:src|srcset)=\"(\.?/[^\"?# ]+)\"", re.IGNORECASE)

BANNED_ENDPOINTS = {
  "github-readme-stats.vercel.app": "github-readme-stats is no longer maintained; use verified/local profile assets",
  "github-readme-activity-graph.vercel.app": "the upstream activity graph deployment is unavailable; use GitHub's native calendar",
  "github-profile-summary-cards.vercel.app": "third-party inferred profile statistics were shown to be inconsistent for this account",
  "github-stats-extended.vercel.app": "third-party inferred totals and language percentages were shown to be inconsistent for this account",
  "ghchart.rshah.org": "the custom heatmap was replaced by repository-owned activity art and GitHub's native calendar",
  "streak-stats.demolab.com": "third-party streak inference is not used as CV evidence",
  "readme-typing-svg.herokuapp.com": "the legacy Heroku typing endpoint should not be used",
  "capsule-render.vercel.app": "the profile hero is intentionally self-hosted in this repository",
}

SOFT_HOSTS = {
  "vk.com",
  "komarev.com",
}

IMAGE_HOSTS = {
  "img.shields.io",
  "komarev.com",
  "readme-typing-svg.demolab.com",
}

REQUIRED_PROFILE_MARKERS = (
  "Fullstack Engineer · Automation & Agentic Systems",
  "## Professional profile / CV",
  "### Current commercial products and ventures",
  "**Local AI OS**",
  "**Elizabeth**",
  "**Telegram Commerce Ops**",
  "**LeadDesk**",
  "**Lithophane Cube**",
  "### Automation, agents and developer systems",
  "LLM/agent orchestration, context and retrieval",
  "### 🏆 Yocto / Linux Development at YADRO / Radio Gigabit",
  "### 🏆 Fullstack Developer at YADRO / Radio Gigabit",
  "### 🏆 Frontend Developer at Neimark & YADRO (IoT Project)",
  "### 🏆 Technical Lead & Fullstack Developer",
  "### 🏆 Frontend Developer at T-Bank (Academic Project)",
  "### 🏆 Freelance Frontend Developer",
  "## Tech stack",
  "## Contact",
)

FORBIDDEN_POSITIONING = (
  "### Frontend Developer | Fullstack Developer | HSE Software Engineering Student",
)


def fail(message: str) -> None:
  print(f"ERROR: {message}")


def warn(message: str) -> None:
  print(f"WARN: {message}")


def ok(message: str) -> None:
  print(f"OK: {message}")


def extract_urls(text: str) -> list[str]:
  urls: set[str] = set()
  for pattern in (MARKDOWN_URL_RE, HTML_URL_RE, AUTOLINK_URL_RE):
    for match in pattern.findall(text):
      urls.add(match.replace("&amp;", "&"))
  return sorted(urls)


def validate_local_assets(text: str) -> bool:
  success = True
  assets = sorted(set(LOCAL_IMAGE_RE.findall(text)))

  if not assets:
    fail("README contains no local image assets")
    return False

  for raw_path in assets:
    relative = raw_path[2:] if raw_path.startswith("./") else raw_path[1:]
    path = ROOT / relative
    if not path.is_file():
      fail(f"missing local asset: {raw_path}")
      success = False
      continue

    if path.suffix.lower() == ".svg":
      try:
        ET.parse(path)
      except ET.ParseError as exc:
        fail(f"invalid SVG {raw_path}: {exc}")
        success = False
        continue

    ok(f"local asset {raw_path}")

  return success


def validate_profile_content(text: str) -> bool:
  success = True

  for marker in REQUIRED_PROFILE_MARKERS:
    if marker not in text:
      fail(f"required CV/profile content is missing: {marker}")
      success = False

  for marker in FORBIDDEN_POSITIONING:
    if marker in text:
      fail(f"obsolete frontend-first positioning returned: {marker}")
      success = False

  if success:
    ok("CV positioning and information-preservation markers")
  return success


def validate_banned_endpoints(urls: list[str]) -> bool:
  success = True
  for url in urls:
    host = urllib.parse.urlparse(url).hostname or ""
    if host in BANNED_ENDPOINTS:
      fail(f"banned endpoint {host}: {BANNED_ENDPOINTS[host]}")
      success = False
  return success


def request_headers(url: str) -> tuple[int, str]:
  parsed = urllib.parse.urlparse(url)
  headers = {
    "User-Agent": "goringich-profile-health/1.2 (+https://github.com/goringich/goringich)",
    "Accept": "*/*",
  }

  token = os.getenv("GITHUB_TOKEN")
  if token and parsed.hostname in {"github.com", "api.github.com", "raw.githubusercontent.com"}:
    headers["Authorization"] = f"Bearer {token}"

  request = urllib.request.Request(url, headers=headers, method="GET")
  with urllib.request.urlopen(request, timeout=20) as response:
    return response.status, response.headers.get("Content-Type", "").lower()


def validate_external_urls(urls: list[str]) -> bool:
  success = True
  print(f"Checking {len(urls)} unique external URLs")

  for index, url in enumerate(urls, start=1):
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    last_error: Exception | None = None

    for attempt in range(3):
      try:
        status, content_type = request_headers(url)
        if not 200 <= status < 400:
          raise RuntimeError(f"HTTP {status}")

        if host in IMAGE_HOSTS and not (
          content_type.startswith("image/")
          or "svg" in content_type
          or "xml" in content_type
        ):
          raise RuntimeError(f"unexpected content type {content_type or '<missing>'}")

        ok(f"[{index}/{len(urls)}] {url} -> {status} {content_type or '<unknown>'}")
        last_error = None
        break
      except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as exc:
        last_error = exc
        if attempt < 2:
          time.sleep(1.5 * (attempt + 1))

    if last_error is None:
      continue

    message = f"[{index}/{len(urls)}] {url}: {last_error}"
    if host in SOFT_HOSTS:
      warn(message)
    else:
      fail(message)
      success = False

  return success


def validate_repository_hygiene() -> bool:
  success = True
  forbidden_paths = [
    ROOT / ".github/workflows/update-readme.yml",
    ROOT / ".github/workflows/tmp-chat-relay-20260827.yml",
    ROOT / "tmp/chat-relay-link-20260827.md",
  ]

  for path in forbidden_paths:
    if path.exists():
      fail(f"obsolete profile artifact still exists: {path.relative_to(ROOT)}")
      success = False

  workflow_dir = ROOT / ".github/workflows"
  for path in workflow_dir.glob("*.yml"):
    content = path.read_text(encoding="utf-8")
    if re.search(r"https?://[^\s\"']+[?&]token=\$", content):
      fail(f"workflow may send a shell token through a URL: {path.relative_to(ROOT)}")
      success = False

  if success:
    ok("repository hygiene")
  return success


def main() -> int:
  if not README.is_file():
    fail("README.md is missing")
    return 1

  text = README.read_text(encoding="utf-8")
  urls = extract_urls(text)

  checks = [
    validate_local_assets(text),
    validate_profile_content(text),
    validate_banned_endpoints(urls),
    validate_repository_hygiene(),
    validate_external_urls(urls),
  ]

  if all(checks):
    print("\nPROFILE HEALTH: PASS")
    return 0

  print("\nPROFILE HEALTH: FAIL")
  return 1


if __name__ == "__main__":
  sys.exit(main())
