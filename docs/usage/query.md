# `bhd query`

Search and manage saved queries.

**Usage**:

```console
$ bhd query [OPTIONS] COMMAND [ARGS]...
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

## `bhd query create`

Search for scenes and save the results as a new named query.

**Usage**:

```console
$ bhd query create [OPTIONS] {minx} {maxx} {miny} {maxy} {start_date}:<%Y-%m-%d> {end_date}:<%Y-%m-%d>
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

## `bhd query list`

List all saved queries.

**Usage**:

```console
$ bhd query list [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhd query show`

Show a saved query's scenes.

**Usage**:

```console
$ bhd query show [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--help`: Show this message and exit.

## `bhd query rename`

Update a saved query's name/description.

**Usage**:

```console
$ bhd query rename [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--name <str>`: New name
* `--desc <str>`: New description
* `--help`: Show this message and exit.

## `bhd query fork`

Clone a saved query under a new name.

**Usage**:

```console
$ bhd query fork [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug to fork  [required]

**Options**:

* `--name <str>`: Name for the forked query
* `--help`: Show this message and exit.

## `bhd query rm`

Delete a saved query.

**Usage**:

```console
$ bhd query rm [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--help`: Show this message and exit.

## `bhd query refresh`

Check for new scenes matching this query.

**Usage**:

```console
$ bhd query refresh [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `--help`: Show this message and exit.

## `bhd query download`

Download scenes from a saved query.

Priced scenes are skipped; interrupted downloads restart from scratch.
Re-authenticates automatically if the session has expired.

**Usage**:

```console
$ bhd query download [OPTIONS] {slug}
```

**Arguments**:

* `slug`: Query slug  [required]

**Options**:

* `-o, --out <str>`: Directory to save downloaded scenes into  [required]
* `-s, --select <str>`: Scene(s) to download: 1-based index or scene ID from 'query show'. Comma-separated (-s 1,3,5) or repeat the flag (-s 1 -s 3). Omit to download the entire query.
* `-p, --parallel <int>`: Number of scenes to download concurrently  [default: 4]
* `--force`: Re-download scenes even if already present in --out
* `--password <str>`: Password to re-authenticate with if the session has expired (non-interactive use only; omit to be prompted instead).
* `--help`: Show this message and exit.
