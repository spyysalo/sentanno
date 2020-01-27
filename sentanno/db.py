import os
import json

from collections import OrderedDict, defaultdict
from glob import iglob
from tempfile import mkstemp

from flask import current_app as app

from sentanno import conf
from .standoff import parse_standoff


class DocumentData(object):
    """Text with alternative annotation sets, designated candidate
    annotation, and possible judgments."""
    def __init__(self, text, annsets, metadata):
        self.text = text
        self.annsets = annsets
        self.metadata = metadata
        self.candidate = self.get_annotation(self.candidate_annset,
                                             self.candidate_id)

    def accepted_candidates(self):
        return self.metadata.get('accepted', [])

    def rejected_candidates(self):
        return self.metadata.get('rejected', [])

    def get_keywords(self, processed=False):
        keywords = self.metadata.get('keywords', '')
        if not processed:
            return keywords
        else:
            keywords = [k.lower().strip() for k in keywords.split(',')]
            keywords = sorted(list(set([k for k in keywords if k])))
            return keywords
    
    def candidate_status(self, candidate):
        if candidate in self.accepted_candidates():
            return 'accepted'
        elif candidate in self.rejected_candidates():
            return 'rejected'
        else:
            return 'incomplete'
    
    def judgment_complete(self):
        judged = (set(self.accepted_candidates()) |
                  set(self.rejected_candidates()))
        return len(judged) == 4    # TODO avoid hard-coded count

    def filter_to_candidate(self):
        """Filter annsets to annotations overlapping candidate."""
        filtered = { k: [] for k in self.annsets }
        for key, annset in self.annsets.items():
            for a in annset:
                if a.overlaps(self.candidate):
                    filtered[key].append(a)
        self.annsets = filtered

    def annotated_strings(self, unique=True, include_empty=False):
        flattened = [a for anns in self.annsets.values() for a in anns]
        texts = [a.text for a in flattened]
        if not include_empty:
            texts = [t for t in texts if t]
        if unique:
            texts = list(OrderedDict.fromkeys(texts))
        return texts

    @property
    def candidate_annset(self):
        return self.annsets['ann']    # This tool only uses one annotation set

    @property
    def candidate_id(self):
        if 'candidate_id' not in self.metadata:
            if not self.candidate_annset:
                raise ValueError('No candidate annotations')
            id_ = self.candidate_annset[0].id
            app.logger.warning('No candidate_id, using {}'.format(id_))
            self.metadata['candidate_id'] = id_
        return self.metadata['candidate_id']

    @staticmethod
    def get_annotation(annset, id_):
        """Return identified annotation."""
        matching = [t for t in annset if t.id == id_]
        if not matching:
            raise KeyError('annotation {} not found'.format(id_))
        if len(matching) > 1:
            raise ValueError('duplicate annoation id {}'.format(id_))
        return matching[0]


class FilesystemData(object):
    def __init__(self, root_dir, temp_dir=None):
        self.root_dir = root_dir
        self.temp_dir = temp_dir

    def get_collections(self):
        subdirs = []
        for name in sorted(os.listdir(self.root_dir)):
            path = os.path.join(self.root_dir, name)
            if os.path.isdir(path):
                subdirs.append(name)
        return subdirs

    def _get_contents_by_ext(self, collection):
        """Get collection contents organized by file extension."""
        contents_by_ext = defaultdict(list)
        collection_dir = os.path.join(self.root_dir, collection)
        for name in sorted(os.listdir(collection_dir)):
            path = os.path.join(collection_dir, name)
            if os.path.isfile(path):
                root, ext = os.path.splitext(name)
                contents_by_ext[ext].append(root)
        return contents_by_ext

    def get_documents(self, collection, include_data=False):
        contents_by_ext = self._get_contents_by_ext(collection)
        names = contents_by_ext['.txt']
        if not include_data:            
            return names    # simple listing
        else:
            statuses, texts, accepted, keywords = [], [], [], []
            for root in names:
                try:
                    document_data = self.get_document_data(collection, root)
                    texts.append(document_data.text)
                    accepted.append(document_data.accepted_candidates())
                    keywords.append(document_data.get_keywords(processed=True))
                    if document_data.judgment_complete():
                        status = app.config['STATUS_COMPLETE']
                    else:
                        status = app.config['STATUS_INCOMPLETE']
                except:
                    status = app.config['STATUS_ERROR']
                statuses.append(status)
            return names, statuses, texts, accepted, keywords

    def get_neighbouring_documents(self, collection, document):
        documents = self.get_documents(collection)
        doc_idx = documents.index(document)
        prev_doc = None if doc_idx == 0 else documents[doc_idx-1]
        next_doc = None if doc_idx == len(documents)-1 else documents[doc_idx+1]
        return prev_doc, next_doc

    def get_document_text(self, collection, document):
        path = os.path.join(self.root_dir, collection, document+'.txt')
        with open(path, encoding='utf-8') as f:
            return f.read()

    def get_document_annotation(self, collection, document, annset,
                                parse=False):
        path = os.path.join(self.root_dir, collection, document+'.'+annset)
        with open(path, encoding='utf-8') as f:
            data = f.read()
        if not parse:
            return data
        else:
            return parse_standoff(data)

    def _document_metadata_path(self, collection, document):
        return os.path.join(self.root_dir, collection, document+'.json')

    def save_document_metadata(self, collection, document, data):
        path = self._document_metadata_path(collection, document)
        self.safe_write_file(path, json.dumps(data, indent=4, sort_keys=True))
        
    def get_document_metadata(self, collection, document):
        path = self._document_metadata_path(collection, document)
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    def get_document_data(self, collection, document):
        root_path = os.path.join(self.root_dir, collection, document)
        glob_path = root_path + '.*'

        extensions = set()
        for path in iglob(glob_path):
            root, ext = os.path.splitext(os.path.basename(path))
            assert ext[0] == '.'
            ext = ext[1:]
            extensions.add(ext)
        app.logger.info('Found {} for {}'.format(extensions, glob_path))

        if 'json' not in extensions:
            app.logger.warning('No {}.json, creating'.format(root_path))
            self.save_document_metadata(collection, document, {})
            extensions.add('json')
        
        for ext in ('txt', 'ann', 'json'):
            if ext not in extensions:
                raise KeyError('missing {}.{}'.format(root_path, ext))

        text = self.get_document_text(collection, document)
        annsets = OrderedDict()
        annsets['ann'] = self.get_document_annotation(
            collection, document, 'ann', parse=True)
        metadata = self.get_document_metadata(collection, document)

        return DocumentData(text, annsets, metadata)

    def set_document_keywords(self, collection, document, keywords):
        data = self.get_document_metadata(collection, document)
        data['keywords'] = keywords
        self.save_document_metadata(collection, document, data)

    def set_document_picks(self, collection, document, accepted, rejected):
        data = self.get_document_metadata(collection, document)
        data['accepted'] = accepted
        data['rejected'] = rejected
        self.save_document_metadata(collection, document, data)

    def safe_write_file(self, fn, text):
        """Atomic write using os.rename()."""
        fd, tmpfn = mkstemp(dir=self.temp_dir)
        with open(fd, 'wt') as f:
            f.write(text)
            # https://stackoverflow.com/a/2333979
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmpfn, fn)

    @staticmethod
    def read_ann(path, parse=True):
        with open(path, encoding='utf-8') as f:
            data = f.read()
        if not parse:
            return data
        else:
            return parse_standoff(data, path)


def get_db():
    data_dir = conf.get_datadir()
    temp_dir = conf.get_tempdir()
    return FilesystemData(data_dir, temp_dir)


def close_db(err=None):
    pass


def init(app):
    app.teardown_appcontext(close_db)
