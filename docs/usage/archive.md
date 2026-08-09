# `bhd archive`

Browse available satellites and sensors.

**Usage**:

```console
$ bhd archive [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `list`: List satellites and sensors from the archive.
* `export`: Export archive data to a JSON file.

## `bhd archive list`

List satellites and sensors from the archive.

**Usage**:

```console
$ bhd archive list [OPTIONS]
```

**Options**:

* `-s, --sat <str>`: Filter by satellite name.
* `--refresh`: Re-fetch archive data from the portal.
* `--help`: Show this message and exit.

## `bhd archive export`

Export archive data to a JSON file.

**Usage**:

```console
$ bhd archive export [OPTIONS]
```

**Options**:

* `-o, --out <str>`: Output file path.  [required]
* `-s, --sat <str>`: Filter by satellite name.
* `--refresh`: Re-fetch archive data from the portal.
* `--help`: Show this message and exit.
