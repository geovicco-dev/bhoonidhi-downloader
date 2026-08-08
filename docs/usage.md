# `bhoonidhi-downloader`

Search, save, and download satellite imagery from the Bhoonidhi Earth Observation portal.

**Usage**:

```console
$ bhoonidhi-downloader [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `version`: Package version.
* `auth`: Authenticate with Bhoonidhi Portal.
* `archive`: Browse available satellites and sensors.
* `query`: Search and manage saved queries.

## `bhoonidhi-downloader version`

Package version.

**Usage**:

```console
$ bhoonidhi-downloader version [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhoonidhi-downloader auth`

Authenticate with Bhoonidhi Portal.

**Usage**:

```console
$ bhoonidhi-downloader auth [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `login`: Authenticate and save session to...
* `logout`: Clear the saved session.
* `status`: Show current session status.
* `whoami`: Print the current username.
* `refresh`: Refresh the authentication token.

### `bhoonidhi-downloader auth login`

Authenticate and save session to ~/.bhoonidhi/session.

**Usage**:

```console
$ bhoonidhi-downloader auth login [OPTIONS]
```

**Options**:

* `--username <str>`: Bhoonidhi username
* `--password <str>`: Bhoonidhi password
* `--save / --no-save`: Persist session to disk  [default: save]
* `--help`: Show this message and exit.

### `bhoonidhi-downloader auth logout`

Clear the saved session.

**Usage**:

```console
$ bhoonidhi-downloader auth logout [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader auth status`

Show current session status.

**Usage**:

```console
$ bhoonidhi-downloader auth status [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader auth whoami`

Print the current username.

**Usage**:

```console
$ bhoonidhi-downloader auth whoami [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader auth refresh`

Refresh the authentication token.

**Usage**:

```console
$ bhoonidhi-downloader auth refresh [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhoonidhi-downloader archive`

Browse available satellites and sensors.

**Usage**:

```console
$ bhoonidhi-downloader archive [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List satellites and sensors from the archive.
* `export`: Export archive data to a JSON file.

### `bhoonidhi-downloader archive list`

List satellites and sensors from the archive.

**Usage**:

```console
$ bhoonidhi-downloader archive list [OPTIONS]
```

**Options**:

* `-s, --sat <str>`: Filter by satellite name.
* `--refresh`: Re-fetch archive data from the portal.
* `--help`: Show this message and exit.

### `bhoonidhi-downloader archive export`

Export archive data to a JSON file.

**Usage**:

```console
$ bhoonidhi-downloader archive export [OPTIONS]
```

**Options**:

* `-o, --out <str>`: Output file path.  [required]
* `-s, --sat <str>`: Filter by satellite name.
* `--refresh`: Re-fetch archive data from the portal.
* `--help`: Show this message and exit.

## `bhoonidhi-downloader query`

Search and manage saved queries.

**Usage**:

```console
$ bhoonidhi-downloader query [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `create`: Search for scenes and save the results as...
* `list`: List all saved queries.
* `show`: Show a saved query's scenes.
* `rename`: Update a saved query's name/description.
* `fork`: Clone a saved query under a new name.
* `rm`: Delete a saved query.
* `refresh`: Check for new scenes matching this query.
* `download`: Download scenes from a saved query.

### `bhoonidhi-downloader query create`

Search for scenes and save the results as a new named query.

**Usage**:

```console
$ bhoonidhi-downloader query create [OPTIONS] {minx} {maxx} {miny} {maxy} {start_date}:<%Y-%m-%d> {end_date}:<%Y-%m-%d>
```

**Arguments**:

* `minx`: Minimum longitude  [required]
* `maxx`: Maximum longitude  [required]
* `miny`: Minimum latitude  [required]
* `maxy`: Maximum latitude  [required]
* `start_date:<%Y-%m-%d>`: Start date (YYYY-MM-DD)  [required]
* `end_date:<%Y-%m-%d>`: End date (YYYY-MM-DD)  [required]

**Options**:

* `--sat <str>`: Satellite name (Ex: ResourceSat-2)
* `--sen <str>`: Sensor name (Ex: LISS3)
* `--name <str>`: Override the auto-generated name
* `--desc <str>`: Override the auto-generated description
* `--help`: Show this message and exit.

### `bhoonidhi-downloader query list`

List all saved queries.

**Usage**:

```console
$ bhoonidhi-downloader query list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader query show`

Show a saved query's scenes.

**Usage**:

```console
$ bhoonidhi-downloader query show [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader query rename`

Update a saved query's name/description.

**Usage**:

```console
$ bhoonidhi-downloader query rename [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--name <str>`: New name
* `--desc <str>`: New description
* `--help`: Show this message and exit.

### `bhoonidhi-downloader query fork`

Clone a saved query under a new name.

**Usage**:

```console
$ bhoonidhi-downloader query fork [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug to fork  [required]

**Options**:

* `--name <str>`: Name for the forked query
* `--help`: Show this message and exit.

### `bhoonidhi-downloader query rm`

Delete a saved query.

**Usage**:

```console
$ bhoonidhi-downloader query rm [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader query refresh`

Check for new scenes matching this query.

**Usage**:

```console
$ bhoonidhi-downloader query refresh [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--help`: Show this message and exit.

### `bhoonidhi-downloader query download`

Download scenes from a saved query.

Priced scenes are skipped; interrupted downloads restart from scratch.

**Usage**:

```console
$ bhoonidhi-downloader query download [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `-o, --out <str>`: Directory to save downloaded scenes into  [required]
* `-s, --select <str>`: Scene(s) to download: 1-based index or scene ID from 'query show'. Comma-separated (-s 1,3,5) or repeat the flag (-s 1 -s 3). Omit to download the entire query.
* `-p, --parallel <int>`: Number of scenes to download concurrently  [default: 4]
* `--force`: Re-download scenes even if already present in --out
* `--help`: Show this message and exit.
