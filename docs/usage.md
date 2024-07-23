# `API Reference`

**Usage**:

```console
$ bhoonidhi-downloader [OPTIONS] COMMAND [ARGS]...
```

**Options**:

- `--install-completion`: Install completion for the current shell.
- `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
- `--help`: Show this message and exit.

**Commands**:

- `archive`: Lists satellites and sensors from...
- `authenticate`: Authenticates session using Bhoonidhi...
- `search`: Search for scenes from Bhoonidhi Browse &...

## `bhoonidhi-downloader archive`

Lists satellites and sensors from Bhoonidhi Browse & Order Archive.

Args:
sat (str, optional): Satellite to filter by. Defaults to None.

Returns:
None

**Usage**:

```console
$ bhoonidhi-downloader archive [OPTIONS]
```

**Options**:

- `-s, --sat TEXT`: Filter by Satellite (Ex: ResourceSat-2). If not provided, shows all available satellites and sensors from Bhoonidhi Browse & Order Archive.
- `--help`: Show this message and exit.

## `bhoonidhi-downloader authenticate`

Authenticates session using Bhoonidhi credentials.

**Usage**:

```console
$ bhoonidhi-downloader authenticate [OPTIONS]
```

**Options**:

- `--username TEXT`: Bhoonidhi username [required]
- `--password TEXT`: Bhoonidhi password [required]
- `--help`: Show this message and exit.

## `bhoonidhi-downloader search`

Search for scenes from Bhoonidhi Browse & Order Portal based on bounding box and date range. The results can be filtered by available satellites and sensors. Additional options to export results as CSV, JSON or Markdown table.

**Usage**:

```console
$ bhoonidhi-downloader search [OPTIONS] MINX MAXX MINY MAXY START_DATE:[%Y-%m-%d] END_DATE:[%Y-%m-%d]
```

**Arguments**:

- `MINX`: Minimum longitude [required]
- `MAXX`: Maximum longitude [required]
- `MINY`: Minimum latitude [required]
- `MAXY`: Maximum latitude [required]
- `START_DATE:[%Y-%m-%d]`: Start date (YYYY-MM-DD) [required]
- `END_DATE:[%Y-%m-%d]`: End date (YYYY-MM-DD) [required]

**Options**:

- `--sat TEXT`: Satellite name (Ex: ResourceSat-2)
- `--sen TEXT`: Sensor name (Ex: LISS3)
- `--csv TEXT`: Export results as CSV
- `--json TEXT`: Export results as JSON
- `--md TEXT`: Export results as Markdown table
- `--help`: Show this message and exit.
