import os
import sys
import re

from itertools import chain

from flask import current_app as app

from sentanno import conf
from .so2html import standoff_to_html, generate_legend


try:
    from fontTools.ttLib import TTFont
except ImportError:
    print('Failed `import fontTools`, try `pip3 install fonttools`',
          file=sys.stderr)
    raise


def visualize_legend(document_data):
    types = sorted(set(
        a.type for annset in document_data.annsets.values() for a in annset))
    return generate_legend(types, include_style=True)


def visualize_annotation_sets(document_data):
    """Generate visualization of several annotation sets for the same text."""
    text = document_data.text
    annsets = document_data.annsets
    return [(k, standoff_to_html(text, a)) for k, a in annsets.items()]


def _find_covering_span(text, annsets, word_boundary=True):
    """Find text span covering giving annotation sets, optionally
    extending it to word boundaries."""
    flattened = [a for anns in annsets.values() for a in anns]
    start = min(a.start for a in flattened)
    end = max(a.end for a in flattened)
    if word_boundary and text[start].isalnum():
        while start > 0 and text[start-1].isalnum():
            start -= 1
    if word_boundary and text[end-1].isalnum():
        while end < len(text) and text[end].isalnum():
            end += 1
    return start, end


def visualize_candidates(document_data):
    """Generate visualization of alternative annotation candidates."""
    text = document_data.text
    data = document_data.metadata

    # Filter all annotation sets to overlapping (note: destructive)
    document_data.filter_to_candidate()
    annsets = document_data.annsets

    # Identify span to center in the visualization
    span_start, span_end = _find_covering_span(text, annsets)

    # Split text to segments around centered span
    above, left, span, right, below = _split_text(text, span_start, span_end)

    # Adjust offsets for filtered annotations to zero at centered span start
    annsets = _adjust_offsets(annsets, span_start)

    if not app.config['HIGHLIGHT_CONTEXT_MENTIONS']:
        above_ann, left_ann, right_ann, below_ann = [], [], [], []
    else:
        # TODO annotations spanning boundaries (e.g. above-left)
        above_ann, left_ann, right_ann, below_ann = (
            _add_highlight_annotations(t, annsets)
            for t in (above, left, right, below)
        )

    so2html = standoff_to_html
    return {
        'above': so2html(above, above_ann),
        'left': so2html(left, left_ann),
        'spans': { k: so2html(span, a) for k, a in annsets.items() },
        'right': so2html(right, right_ann),
        'below': so2html(below, below_ann),
    }


def _add_highlight_annotations(text, annsets):
    from .so2html import Standoff, FORMATTING_TYPE_TAG_MAP
    underline = [k for k, v in FORMATTING_TYPE_TAG_MAP.items() if v == 'u'][0]
    flattened = [a for anns in annsets.values() for a in anns]
    texts = [a.text for a in flattened if a.text]
    patterns = [ re.compile(r'\b'+re.escape(t)+r'\b', re.I) for t in texts ]
    spans = []
    for p in patterns:
        for m in p.finditer(text):
            start, end = m.span()
            spans.append(Standoff(start, end, underline, 'u'))
    return spans


def _adjust_offsets(annsets, offset):
    # TODO consider making copies instead of modifying annotations in place
    for key, annset in annsets.items():
        for a in annset:
            a.adjust_offsets(offset)
    return annsets


def _tokenize(text, reverse=False):
    if not reverse:
        tokens = re.split(r'(\s+)', text)
    else:
        text = text[::-1]
        rev_tokens = re.split(r'(\s+)', text)
        tokens = [t[::-1] for t in rev_tokens]
    return [t for t in tokens if t]


def _split_text(text, start, end, line_width=None):
    """Split text into five parts with reference to (start, end) span: (above,
    left, span, right, below), where (left, span, right) are on the
    same line.
    """
    if line_width is None:
        nontext_space = 10    # TODO figure out how much margins etc. take
        line_width = conf.get_line_width() - nontext_space

    span_text = text[start:end]
    span_width = _text_width(span_text)

    # add words to left and right until line width would be exceeded
    left_tokens = _tokenize(text[:start])
    right_tokens = _tokenize(text[end:], reverse=True)

    # trim candidate tokens to avoid including newlines in span
    def trim_tokens(tokens, filter_chars='\n'):
        trimmed = []
        for t in tokens:
            if any(c for c in filter_chars if c in t):
                trimmed = []
            else:
                trimmed.append(t)
        return trimmed
    right_tokens = trim_tokens(right_tokens)
    left_tokens = trim_tokens(left_tokens)
    
    left_text, right_text = '', ''
    left_width, right_width = 0, 0
    while True:
        if left_tokens and (left_width <= right_width or not right_tokens):
            new_text = left_tokens[-1] + left_text
            new_width = _text_width(new_text)
            if new_width + span_width + right_width < line_width:
                left_text = new_text
                left_width = new_width
                left_tokens.pop()
                continue
        if right_tokens:
            new_text = right_text + right_tokens[-1]
            new_width = _text_width(new_text)
            if left_width + span_width + new_width < line_width:
                right_text = new_text
                right_width = new_width
                right_tokens.pop()
                continue
        break

    above_text = text[:start-len(left_text)]
    below_text = text[end+len(right_text):]

    assert above_text+left_text+span_text+right_text+below_text == text

    # logging
    lw, sw, rw = (_text_width(t) for t in (left_text, span_text, right_text))
    tw = lw + sw + rw
    app.logger.info('_split_text(): split line "{}"---"{}"---"{}",'
                    'widths {}+{}+{}={}'.format(left_text, span_text,
                                                right_text, lw, sw, rw, tw))

    return above_text, left_text, span_text, right_text, below_text


def _text_width(text, point_size=None, font_file=None):
    """Return width of text in given point size and font."""
    if point_size is None:
        point_size = conf.get_font_size()
    if font_file is None:
        font_file = conf.get_font_file()
    if font_file not in _text_width.cache:
        font_path = os.path.join(app.root_path, 'static', 'fonts', font_file)
        _text_width.cache[font_file] = TTFont(font_path)
    ttfont = _text_width.cache[font_file]
    # Following https://stackoverflow.com/a/48357457
    cmap = ttfont['cmap']
    tcmap = cmap.getcmap(3,1).cmap
    glyphset = ttfont.getGlyphSet()
    units_per_em = ttfont['head'].unitsPerEm
    total = 0
    for c in text:
        if ord(c) in tcmap and tcmap[ord(c)] in glyphset:
            total += glyphset[tcmap[ord(c)]].width
        else:
            total += glyphset['.notdef'].width
    total_points = total * point_size / units_per_em
    return total_points
_text_width.cache = {}
