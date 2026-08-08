"""Concurrent scene downloads with rate-limit-aware pacing.

Note: Bhoonidhi's data endpoint does not honor HTTP Range requests
(verified live — it always returns 200 + the full Content-Length
regardless of a Range header), so an interrupted download cannot be
resumed. A leftover partial file is discarded and the scene is
re-fetched from scratch; this is surfaced via ``DownloadOutcome.
restarted_bytes`` rather than silently dropped.
"""

from __future__ import annotations

import hashlib
import random
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .utils import build_download_url, download_filename, is_downloadable

CHUNK_SIZE = 1024 * 1024  # 1 MiB
MAX_RETRIES = 3
BASE_BACKOFF = 1.5


@dataclass
class DownloadOutcome:
    scene_id: str
    status: str
    # "downloaded" | "skipped_priced" | "already_downloaded" | "cold_storage" | "failed"
    path: str | None = None
    sha256: str | None = None
    bytes_downloaded: int = 0
    error: str | None = None
    restarted_bytes: int = 0  # discarded leftover from a prior interrupted attempt


# scene_id, bytes_so_far, total_bytes (None if unknown)
ProgressCallback = Callable[[str, int, "int | None"], None]


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_one(
    scene: dict[str, Any],
    jwt: str,
    out_dir: Path,
    force: bool,
    on_progress: ProgressCallback | None,
) -> DownloadOutcome:
    scene_id = scene.get("ID", "unknown")

    if not is_downloadable(scene):
        return DownloadOutcome(scene_id=scene_id, status="skipped_priced")

    filename = download_filename(scene)
    out_file = out_dir / filename
    part_file = out_dir / f"{filename}.part"

    if out_file.exists() and out_file.stat().st_size > 0 and not force:
        existing = scene.get("_bhx_download") or {}
        return DownloadOutcome(
            scene_id=scene_id,
            status="already_downloaded",
            path=str(out_file),
            sha256=existing.get("sha256") or _sha256_of_file(out_file),
            bytes_downloaded=out_file.stat().st_size,
        )

    try:
        url = build_download_url(scene, jwt)
    except ValueError as e:
        return DownloadOutcome(scene_id=scene_id, status="failed", error=str(e))

    # A leftover .part from a prior interrupted attempt can't be resumed
    # (the portal ignores Range requests) — discard it and restart clean,
    # but track how much progress was lost so it can be reported.
    restarted_bytes = 0
    if part_file.exists():
        restarted_bytes = part_file.stat().st_size
        part_file.unlink()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, stream=True, timeout=(10, 60))

            if resp.status_code == 404:
                # Scene isn't served directly — commonly older archive
                # data that has aged into cold storage and needs to be
                # requested via the Bhoonidhi Browse & Order cart before
                # it's downloadable again.
                resp.close()
                return DownloadOutcome(
                    scene_id=scene_id,
                    status="cold_storage",
                    error=(
                        "404 — likely archived to cold storage; request it via the "
                        "Bhoonidhi Browse & Order Portal cart, then retry."
                    ),
                )

            if resp.status_code != 200:
                message = f"HTTP {resp.status_code}"
                resp.close()
                raise requests.HTTPError(message)

            content_length = resp.headers.get("Content-Length")
            total_bytes = int(content_length) if content_length else None

            downloaded = 0
            with open(part_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if on_progress:
                        on_progress(scene_id, downloaded, total_bytes)
            resp.close()

            part_file.rename(out_file)
            sha256 = _sha256_of_file(out_file)
            return DownloadOutcome(
                scene_id=scene_id,
                status="downloaded",
                path=str(out_file),
                sha256=sha256,
                bytes_downloaded=downloaded,
                restarted_bytes=restarted_bytes,
            )
        except (requests.RequestException, OSError) as e:
            # Whatever this attempt itself wrote can't be resumed either —
            # clear it so the next attempt starts from a known-clean state.
            if part_file.exists():
                part_file.unlink()
            if attempt == MAX_RETRIES:
                return DownloadOutcome(
                    scene_id=scene_id,
                    status="failed",
                    error=str(e),
                    restarted_bytes=restarted_bytes,
                )
            delay = BASE_BACKOFF * (2 ** (attempt - 1)) + random.random()
            time.sleep(delay)

    return DownloadOutcome(
        scene_id=scene_id,
        status="failed",
        error="unreachable",
        restarted_bytes=restarted_bytes,
    )


class DownloadManager:
    """Runs a batch of scene downloads with bounded concurrency + jittered pacing.

    Concurrency (``parallel``) doubles as the rate-limiter — a small
    submission stagger avoids opening every connection at once against a
    portal that's known to be rate-sensitive (see the jittered back-off
    already used by ``core/search/utils.py``'s ``recursive_search``).
    """

    def __init__(self, jwt: str, out_dir: Path, parallel: int = 4, force: bool = False):
        self.jwt = jwt
        self.out_dir = out_dir
        self.parallel = max(1, parallel)
        self.force = force

    def run(
        self,
        scenes: list[dict[str, Any]],
        on_progress: ProgressCallback | None = None,
    ) -> list[DownloadOutcome]:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        results: list[DownloadOutcome] = []
        lock = threading.Lock()

        def _wrapped_progress(
            scene_id: str, downloaded: int, total: int | None
        ) -> None:
            if on_progress:
                with lock:
                    on_progress(scene_id, downloaded, total)

        with ThreadPoolExecutor(max_workers=self.parallel) as pool:
            futures = {}
            for scene in scenes:
                time.sleep(random.uniform(0.05, 0.2))
                futures[
                    pool.submit(
                        _download_one,
                        scene,
                        self.jwt,
                        self.out_dir,
                        self.force,
                        _wrapped_progress,
                    )
                ] = scene.get("ID")

            for future in as_completed(futures):
                results.append(future.result())

        return results
