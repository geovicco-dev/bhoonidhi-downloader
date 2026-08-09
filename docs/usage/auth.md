# `bhd auth`

Authenticate with Bhoonidhi Portal.

**Usage**:

```console
$ bhd auth [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `login`: Authenticate and save session to...
* `logout`: Clear the saved session.
* `status`: Show current session status.
* `whoami`: Print the current username.
* `refresh`: Refresh the authentication token.

## `bhd auth login`

Authenticate and save session to ~/.bhoonidhi/session.

**Usage**:

```console
$ bhd auth login [OPTIONS]
```

**Options**:

* `--username <str>`: Bhoonidhi username
* `--password <str>`: Bhoonidhi password
* `--save / --no-save`: Persist session to disk  [default: save]
* `--help`: Show this message and exit.

## `bhd auth logout`

Clear the saved session.

**Usage**:

```console
$ bhd auth logout [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhd auth status`

Show current session status.

**Usage**:

```console
$ bhd auth status [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhd auth whoami`

Print the current username.

**Usage**:

```console
$ bhd auth whoami [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `bhd auth refresh`

Refresh the authentication token.

**Usage**:

```console
$ bhd auth refresh [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
