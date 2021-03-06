from aleph.core import create_app, celery as app  # noqa

from aleph.ingest import ingest_url, ingest  # noqa
from aleph.analyze import analyze_document, analyze_collection  # noqa
from aleph.index import index_document  # noqa
from aleph.alerts import check_alerts  # noqa
from aleph.logic import reindex_entities  # noqa
from aleph.crawlers import execute_crawler  # noqa

flask_app = create_app()
flask_app.app_context().push()
