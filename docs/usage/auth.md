# `bhoonidhi-downloader auth`

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

## `bhoonidhi-downloader auth login`

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

## `bhoonidhi-downloader auth logout`

Clear the saved session.

**Usage**:

```console
$ bhoonidhi-downloader auth logout [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhoonidhi-downloader auth status`

Show current session status.

**Usage**:

```console
$ bhoonidhi-downloader auth status [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhoonidhi-downloader auth whoami`

Print the current username.

**Usage**:

```console
$ bhoonidhi-downloader auth whoami [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhoonidhi-downloader auth refresh`

Refresh the authentication token.

**Usage**:

```console
$ bhoonidhi-downloader auth refresh [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
