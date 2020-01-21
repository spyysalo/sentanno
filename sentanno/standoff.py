from flask import current_app as app


def load_standoff(filename, encoding='utf-8'):
    with open(filename, encoding=encoding) as f:
        standoff = f.read()
    return parse_standoff(standoff, filename)


def parse_standoff(standoff, source='<INPUT>'):
    if isinstance(standoff, str):
        standoff = standoff.split('\n')

    annotations = []
    for ln, line in enumerate(standoff, start=1):
        if not line or line[0] == '#':
            continue
        elif line[0] == 'T':
            annotations.append(Textbound.from_standoff_line(line, ln, source))
        else:
            pass    # TODO
    return annotations


class Textbound(object):
    def __init__(self, id_, type_, start, end, text):
        self.id = id_
        self.type = type_
        self.start = start
        self.end = end
        self.text = text
        self.norm = None    # TODO

    def adjust_offsets(self, offset):
        self.start -= offset
        self.end -= offset

    def overlaps(self, other):
        return not (self.end <= other.start or other.end <= self.start)

    def span_matches(self, other):
        return self.start == other.start and self.end == other.end

    def contains(self, other):
        return ((self.start <= other.start and self.end > other.end) or
                (self.start < other.start and self.end >= other.end))

    def span_crosses(self, other):
        return ((self.start < other.start and
                 other.start < self.end < other.end) or
                (other.start < self.start and
                 self.start < other.end < self.end))
    
    def __eq__(self, other):
        return (self.start, self.end, self.type) == (other.start, other.end, other.type)
    
    def __lt__(self, other):
        if self.start != other.start:
            return self.start < other.start
        elif self.end != other.end:
            return self.end > other.end
        else:
            return self.type < other.type

    def __repr__(self):
        return 'Textbound({}, {}, {}, {}, {})'.format(
            self.id, self.type, self.start, self.end, self.text)
        
    def __str__(self):
        return '{}\t{} {} {}\t{}'.format(
            self.id, self.type, self.start, self.end, self.text)

    @classmethod
    def from_standoff_line(cls, line, ln, source):
        fields = line.split('\t')
        id_, type_span, text = fields
        type_, span_str = type_span.split(' ', 1)
        spans = []
        for span in span_str.split(';'):
            start, end = (int(i) for i in span.split())
            spans.append((start, end))
        min_start = min(s[0] for s in spans)
        max_end = max(s[1] for s in spans)
        if len(spans) > 1:
            app.logger.warning('replacing fragmented span {} with {} {}'.format(
                span_str, min_start, max_end))
        return cls(id_, type_, start, end, text)


class Normalization(object):
    def __init__(self, id_, tb_id, norm_id, text):
        self.id = id_
        self.tb_id = tb_id
        self.norm_id = norm_id
        self.text = text

    def adjust_offsets(self, offset):
        pass

    def __str__(self):
        return '{}\tReference {} {}\t{}'.format(
            self.id, self.tb_id, self.norm_id, self.text)

    @classmethod
    def from_standoff_line(cls, line, ln, source):
        raise NotImplementedError
