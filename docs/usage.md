# `bhoonidhi-downloader`

**Usage**:

```console
$ bhoonidhi-downloader [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `authenticate`
* `search`

## `bhoonidhi-downloader authenticate`

**Usage**:

```console
$ bhoonidhi-downloader authenticate [OPTIONS]
```

**Options**:

* `--username TEXT`: Bhoonidhi username  [required]
* `--password TEXT`: Bhoonidhi password  [required]
* `--help`: Show this message and exit.

## `bhoonidhi-downloader search`

**Usage**:

```console
$ bhoonidhi-downloader search [OPTIONS] MINX MAXX MINY MAXY START_DATE:[%Y-%m-%d] END_DATE:[%Y-%m-%d] SATELLITE SENSOR
```

**Arguments**:

* `MINX`: Minimum longitude  [required]
* `MAXX`: Maximum longitude  [required]
* `MINY`: Minimum latitude  [required]
* `MAXY`: Maximum latitude  [required]
* `START_DATE:[%Y-%m-%d]`: Start date (YYYY-MM-DD)  [required]
* `END_DATE:[%Y-%m-%d]`: End date (YYYY-MM-DD)  [required]
* `SATELLITE`: Satellite name (Ex: ResourceSat-2)  [required]
* `SENSOR`: Sensor name (Ex: LISS3)  [required]

**Options**:

* `--help`: Show this message and exit.
