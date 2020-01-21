from flask import Blueprint
from flask import request, url_for, render_template, jsonify
from flask import current_app as app

from .db import get_db
from .visualize import visualize_candidates, visualize_annotation_sets
from .protocol import SELECT_POSITIVE, SELECT_NEGATIVE, SELECT_NEUTRAL
from .protocol import SELECT_UNCLEAR, CLEAR_SELECTION

bp = Blueprint('view', __name__, static_folder='static', url_prefix='/sentanno')


ANNOTATION_OPTIONS = [
    SELECT_POSITIVE,
    SELECT_NEUTRAL,
    SELECT_NEGATIVE,
    SELECT_UNCLEAR
]


@bp.route('/')
def root():
    return show_collections()


@bp.route('/')
def show_collections():
    db = get_db()
    collections = db.get_collections()
    return render_template('collections.html', collections=collections)


@bp.route('/<collection>/')
def show_collection(collection):
    db = get_db()
    docdata = db.get_documents(collection, include_data=True)
    names, statuses, texts, accepted, keywords = docdata
    return render_template('documents.html', **locals())


@bp.route('/<collection>/<document>.txt')
def show_text(collection, document):
    db = get_db()
    return db.get_document_text(collection, document)


@bp.route('/<collection>/<document>.ann<idx>')
def show_annotation_set(collection, document, idx):
    db = get_db()
    return db.get_document_annotation(collection, document, 'ann'+idx)


@bp.route('/<collection>/<document>.json')
def show_metadata(collection, document):
    db = get_db()
    return jsonify(db.get_document_metadata(collection, document))


def _prev_and_next_url(endpoint, collection, document):
    # navigation helper
    db = get_db()
    prev_doc, next_doc = db.get_neighbouring_documents(collection, document)
    prev_url, next_url = (
        url_for(endpoint, collection=collection, document=d) if d is not None
        else None
        for d in (prev_doc, next_doc)
    )
    return prev_url, next_url


@bp.route('/<collection>/<document>.all')
def show_all_annotations(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    content = visualize_annotation_sets(document_data)
    prev_url, next_url = _prev_and_next_url(
        request.endpoint, collection, document)
    return render_template('annsets.html', **locals())


@bp.route('/<collection>/<document>')
def show_annotation(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    # Filter to avoid irrelevant types in legend
    document_data.filter_to_candidate()
    metadata = document_data.metadata
    content = visualize_candidates(document_data)
    prev_url, next_url = _prev_and_next_url(
        request.endpoint, collection, document)
    options = ANNOTATION_OPTIONS
    status = [document_data.candidate_status(i) for i in options]
    keywords = document_data.get_keywords()
    return render_template('sentanno.html', **locals())


@bp.route('/<collection>/<document>/keywords')
def save_keywords(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    keywords = request.args.get('keywords')
    app.logger.info('{}/{}: keywords "{}"'.format(
        collection, document, keywords))
    db.set_document_keywords(collection, document, keywords)
    return jsonify({
        'keywords': keywords
    })


@bp.route('/<collection>/<document>/pick')
def pick_annotation(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    choice = request.args.get('choice')
    options = ANNOTATION_OPTIONS
    if choice in options:
        accepted = [choice]
        rejected = [o for o in options if o != choice]
    elif choice == CLEAR_SELECTION:
        accepted = []
        rejected = []
    else:
        app.logger.error('invalid choice {}'.format(choice))
        accepted = []
        rejected = []

    app.logger.info('{}/{}: accepted {}, rejected {}'.format(
        collection, document, accepted, rejected))
    db.set_document_picks(collection, document, accepted, rejected)

    # Make sure the DB agrees
    data = db.get_document_metadata(collection, document)

    return jsonify({
        'accepted': data['accepted'],
        'rejected': data['rejected'],
    })
