# Download

Used internally by `bhd query download` — concurrent scene downloads with SHA256 verification.

Bhoonidhi's data endpoint does not honor HTTP Range requests, so an interrupted download cannot be resumed. A leftover partial file is discarded and the scene is re-fetched from scratch, tracked via `DownloadOutcome.restarted_bytes` rather than silently dropped.

## Client

::: bhoonidhi_downloader.core.download.client.DownloadManager

::: bhoonidhi_downloader.core.download.client.DownloadOutcome

::: bhoonidhi_downloader.core.download.client.sha256_of_file

## Dry-run preview

::: bhoonidhi_downloader.core.download.preview.build_preview

::: bhoonidhi_downloader.core.download.preview.DownloadPreview

## URL helpers

`is_downloadable` lives in [`core.search.availability`](search.md#bhoonidhi_downloader.core.search.availability.is_downloadable) — the same function search uses to classify a scene's availability.

::: bhoonidhi_downloader.core.download.utils.build_download_url

::: bhoonidhi_downloader.core.download.utils.download_filename

## Rendering

::: bhoonidhi_downloader.core.download.render.render_download_report

::: bhoonidhi_downloader.core.download.render.render_download_preview
