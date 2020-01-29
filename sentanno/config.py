from os import path
from sentanno.protocol import *


DATADIR = path.join(path.dirname(__file__), '..', 'data')

TEMPDIR = path.join(path.dirname(__file__), '..', 'temp')

# Visualization configuration

FONT_SIZE = 16    # pixels
FONT_FILE = 'OpenSans-Regular.ttf'    # filename in static/fonts
FONT_FAMILY = 'Open Sans'             # font-family in css
LINE_WIDTH = 800    # pixels, for visualizations

# Add abbreviated type as subscript to spans

ANNOTATION_TYPE_SUBSCRIPT = False # True

# Highlight context mentions of candidate annotations

HIGHLIGHT_CONTEXT_MENTIONS = True

# Annotation option
ANNOTATION_OPTIONS = [
    SELECT_POSITIVE,
    SELECT_NEUTRAL,
    SELECT_NEGATIVE,
    SELECT_MIXED,
    SELECT_UNCLEAR
]

# Fontawesome icons
ICONS = {
    SELECT_POSITIVE: 'smile',
    SELECT_NEUTRAL: 'meh-blank',
    SELECT_NEGATIVE: 'frown',
    SELECT_MIXED: 'meh',
    SELECT_UNCLEAR: 'question-circle',
}

# Icon colors
ICON_COLORS = {
    SELECT_POSITIVE: 'green',
    SELECT_NEUTRAL: 'black',
    SELECT_NEGATIVE: 'red',
    SELECT_MIXED: 'purple',
    SELECT_UNCLEAR: 'blue',
}

# Key binding configuration
HOTKEYS = {
    '1': SELECT_POSITIVE,    # select positive sentiment
    '2': SELECT_NEUTRAL,  # select neutral sentiment
    '3': SELECT_NEGATIVE,  # select negative sentiment
    '4': SELECT_UNCLEAR,   # select sentiment mixed or unclear
    'z': CLEAR_SELECTION,          # clear accept/reject
}

# Document status constants (TODO: maybe not the right place for these)

STATUS_COMPLETE = 'complete'
STATUS_INCOMPLETE = 'todo'
STATUS_ERROR = 'ERROR'
