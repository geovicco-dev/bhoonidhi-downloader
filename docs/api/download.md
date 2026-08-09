# Download

Used internally by `bhd query download` — concurrent scene downloads with SHA256 verification.

Bhoonidhi's data endpoint does not honor HTTP Range requests, so an interrupted download cannot be resumed. A leftover partial file is discarded and the scene is re-fetched from scratch, tracked via `DownloadOutcome.restarted_bytes` rather than silently dropped.

## Client

::: bhoonidhi_downloader.core.download.client.DownloadManager

::: bhoonidhi_downloader.core.download.client.DownloadOutcome

::: bhoonidhi_downloader.core.download.client.sha256_of_file

## Eligibility & URL helpers

::: bhoonidhi_downloader.core.download.utils.is_downloadable

::: bhoonidhi_downloader.core.download.utils.build_download_url

::: bhoonidhi_downloader.core.download.utils.download_filename

## Rendering

::: bhoonidhi_downloader.core.download.render.render_download_report
