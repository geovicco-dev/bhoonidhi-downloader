# `bhoonidhi-downloader archive`

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

## `bhoonidhi-downloader archive list`

List satellites and sensors from the archive.

**Usage**:

```console
$ bhoonidhi-downloader archive list [OPTIONS]
```

**Options**:

* `-s, --sat <str>`: Filter by satellite name.
* `--refresh`: Re-fetch archive data from the portal.
* `--help`: Show this message and exit.

## `bhoonidhi-downloader archive export`

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
