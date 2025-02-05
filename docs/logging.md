# Logging

## Configuration variables

See [environment variable reference](environment.md).

## Default logging behavior

-   inboard's logging configuration logic is located in [`logging_conf.py`](https://github.com/br3ndonland/inboard/blob/HEAD/inboard/logging_conf.py). By default, inboard will load the `LOGGING_CONFIG` dictionary in this module. The dictionary was named for consistency with [Uvicorn's logging configuration dictionary](https://github.com/encode/uvicorn/blob/HEAD/uvicorn/config.py).
-   When running Uvicorn alone, logging is configured programmatically from within the [`start.py` start script](https://github.com/br3ndonland/inboard/blob/HEAD/inboard/start.py), by passing the `LOGGING_CONFIG` dictionary to `uvicorn.run()`.
-   When running Gunicorn with the Uvicorn worker, the logging configuration dictionary is specified within the [`gunicorn_conf.py`](https://github.com/br3ndonland/inboard/blob/HEAD/inboard/gunicorn_conf.py) configuration file.

## Extending the logging config

If inboard is installed from PyPI with `poetry add inboard` or `pip install inboard`, the logging configuration can be easily customized as explained in the [Python logging configuration docs](https://docs.python.org/3/library/logging.config.html).

<!-- prettier-ignore -->
!!!example "Example of a custom logging module"

    ```py
    # /app/package/custom_logging.py: set with LOGGING_CONF=package.custom_logging
    import logging
    import os

    from inboard import LOGGING_CONFIG

    # add a custom logging format: set with LOG_FORMAT=mycustomformat
    LOGGING_CONFIG["formatters"]["mycustomformat"] = {
        "format": "[%(name)s] %(levelname)s %(message)s"
    }


    class MyFormatterClass(logging.Formatter):
        """Define a custom logging format class."""

        def __init__(self) -> None:
            super().__init__(fmt="[%(name)s] %(levelname)s %(message)s")


    # use a custom logging format class: set with LOG_FORMAT=mycustomclass
    LOGGING_CONFIG["formatters"]["mycustomclass"] = {
        "()": "package.custom_logging.MyFormatterClass",
    }

    # only show access logs when running Uvicorn with LOG_LEVEL=debug
    LOGGING_CONFIG["loggers"]["gunicorn.access"] = {"propagate": False}
    LOGGING_CONFIG["loggers"]["uvicorn.access"] = {
        "propagate": str(os.getenv("LOG_LEVEL")) == "debug"
    }

    # don't propagate boto logs
    LOGGING_CONFIG["loggers"]["boto3"] = {"propagate": False}
    LOGGING_CONFIG["loggers"]["botocore"] = {"propagate": False}
    LOGGING_CONFIG["loggers"]["s3transfer"] = {"propagate": False}

    ```

## Design decisions

### Simplify logging

**Logging is complicated in general, but logging a Uvicorn+Gunicorn+Starlette/FastAPI stack is particularly, and unnecessarily, complicated**. Uvicorn and Gunicorn use different logging configurations, and it can be difficult to unify the log streams.

Gunicorn's API for loading [logging configuration dictionaries](https://docs.python.org/3/library/logging.config.html) has some problems:

-   Gunicorn does not have a clearly-documented interface for running programmatically from within a Python module, like `uvicorn.run()`, so `subprocess.run()` can be used instead. There isn't a clear way to pass logging configuration dictionaries to Gunicorn from the command line, unless you `json.dumps()` a logging configuration dictionary.
-   As of Gunicorn version 20, Gunicorn accepted a command-line argument `--log-config-dict`, but it didn't work, and [the maintainers removed it](https://github.com/benoitc/gunicorn/pull/2476).

Uvicorn's API for loading logging configurations is confusing and poorly documented:

-   The [settings documentation as of version 0.11.8](https://github.com/encode/uvicorn/blob/4597b90ffcfb99e44dae6c7d8cc05e1f368e0624/docs/settings.md) (the version available when this project started) said, "`--log-config <path>` - Logging configuration file," but there was no information given on file format.
-   [encode/uvicorn#665](https://github.com/encode/uvicorn/pull/665) and [Uvicorn 0.12.0](https://github.com/encode/uvicorn/releases/tag/0.12.0) added support for loading JSON and YAML configuration files, but not `.py` files.
-   Uvicorn's own logging configuration is a dictionary, `LOGGING_CONFIG`, in [`config.py`](https://github.com/encode/uvicorn/blob/HEAD/uvicorn/config.py), but there's no information provided on how to supply a custom dictionary config. It is possible to pass a dictionary config to Uvicorn when running programmatically, such as `uvicorn.run(log_config=your_dict_config)`, although so far, this capability is only documented in the [changelog](https://github.com/encode/uvicorn/blob/HEAD/CHANGELOG.md) for version 0.10.0.

**The inboard project eliminates this complication and confusion**. Uvicorn, Gunicorn, and FastAPI log streams are propagated to the root logger, and handled by the custom root logging config.

### Require dict configs

The project initially also had support for the old-format `.conf`/`.ini` files, and YAML files, but this was later dropped, because:

-   **Dict configs are the newer, recommended format**, as explained in the [`logging.config` docs](https://docs.python.org/3/library/logging.config.html):

    > The `fileConfig()` API is older than the `dictConfig()` API and does not provide functionality to cover certain aspects of logging. For example, you cannot configure Filter objects, which provide for filtering of messages beyond simple integer levels, using `fileConfig()`. If you need to have instances of Filter in your logging configuration, you will need to use `dictConfig()`. Note that future enhancements to configuration functionality will be added to `dictConfig()`, so it’s worth considering transitioning to this newer API when it’s convenient to do so.

-   **Dict configs allow programmatic control of logging settings** (see how log level is set in [`logging_conf.py`](https://github.com/br3ndonland/inboard/blob/HEAD/inboard/logging_conf.py) for an example).
-   **Gunicorn and Uvicorn both use dict configs in `.py` files for their own logging configurations**.
-   **Gunicorn prefers dict configs** specified with the [`logconfig_dict` option](https://docs.gunicorn.org/en/latest/settings.html#logconfig-dict).
-   **Uvicorn accepts dict configs when running programmatically**, like `uvicorn.run(log_config=your_dict_config)`.
-   **Relying on Python dictionaries reduces testing burden** (only have to write unit tests for `.py` files)
-   **YAML isn't a Python data structure**. YAML is confusingly used for examples in the documentation, but isn't actually a recommended format. There's no built-in YAML data structure in Python, so the YAML must be parsed by PyYAML and converted into a dictionary, then passed to `logging.config.dictConfig()`. **Why not just make the logging config a dictionary in the first place?**

## Further info

For more details on how logging was implemented initially, see [br3ndonland/inboard#3](https://github.com/br3ndonland/inboard/pull/3).

For more information on Python logging configuration, see the [Python `logging` how-to](https://docs.python.org/3/howto/logging.html), [Python `logging` cookbook](https://docs.python.org/3/howto/logging-cookbook.html), [Python `logging` module docs](https://docs.python.org/3/library/logging.html), and [Python `logging.config` module docs](https://docs.python.org/3/library/logging.config.html). Also consider [Loguru](https://loguru.readthedocs.io/en/stable/index.html), an alternative logging module with many improvements over the standard library `logging` module.
