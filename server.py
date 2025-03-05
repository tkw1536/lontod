import argparse
import sqlite3
from lontod.indexer import Query
from lontod.daemon import Handler
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler


def main(db: str, port: int, host: str, log_level: str):
    # setup logging
    logging.basicConfig(level="logging.{log_level}")
    logger = logging.getLogger(__name__)

    logger.info('Opening database at %r', db)
    conn = sqlite3.connect(f'file:{db}?mode=ro')

    try:
        query = Query(conn)
        handler = Handler(query, logger)

        class HTTPHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                handler(self)
        
        server = HTTPServer((host, port), HTTPHandler)
        
        logger.info('Starting server at %s:%s', host, port)
        server.serve_forever()
    finally:
        conn.close() 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-d',
        '--database',
        default='./onto.db',
        help='Database file to index into',
    )
    parser.add_argument(
        '-H',
        '--host',
        default="localhost",
        help='Host to listen on',
    )
    parser.add_argument(
        '-p',
        '--port',
        type=int,
        default=8080,
        help='Host to listen on',
    )
    parser.add_argument(
        '-l',
        '--log',
        default="info",
        help='Set logging level',
    )

    result = parser.parse_args()
    main(result.database, result.port, result.host, result.log)