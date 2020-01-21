from flask import current_app as app


DATADIR_KEY = 'DATADIR'

FONT_SIZE_KEY = 'FONT_SIZE'

FONT_FILE_KEY = 'FONT_FILE'

LINE_WIDTH_KEY = 'LINE_WIDTH'


class ConfigError(Exception):
    pass


def get_datadir():
    try:
        return app.config[DATADIR_KEY]
    except KeyError:
        raise ConfigError('missing {} in config'.format(DATADIR_KEY))


def get_font_size():
    try:
        return app.config[FONT_SIZE_KEY]
    except KeyError:
        raise ConfigError('missing {} in config'.format(FONT_SIZE_KEY))


def get_font_file():
    try:
        return app.config[FONT_FILE_KEY]
    except KeyError:
        raise ConfigError('missing {} in config'.format(FONT_FILE_KEY))


def get_line_width():
    try:
        return app.config[LINE_WIDTH_KEY]
    except KeyError:
        raise ConfigError('missing {} in config'.format(LINE_WIDTH_KEY))
