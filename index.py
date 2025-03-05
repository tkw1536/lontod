import argparse
import sqlite3
from lontod.indexer import Indexer, Ingester
from os.path import isdir, isfile 
import logging


def main(paths: str, clean: bool, db: str, log_level: str):
    # setup logging
    logging.basicConfig(level="logging.{log_level}")
    logger = logging.getLogger(__name__)

    logger.info('Opening database at %r', db)
    conn = sqlite3.connect(db)
    
    indexer = Indexer(conn)
    ingester = Ingester(indexer, logger)
    
    try:
        logger.info('Initializing schema')
        indexer.initialize_schema()

        if clean:
            logger.info('Cleaning up database')
            indexer.truncate()
        
        for path in paths:
            if isfile(path):
                ingester.ingest_file(path)
            elif isdir(path):
                ingest_directory(path)
            else:
                logger.error('Unable to ingest %r: Neither a path nor a directory', path)

        conn.commit()
    finally:
        conn.close() 

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'input',
        nargs='+',
        help='Path(s) to input file(s) or directories(s) to read',
    )
    parser.add_argument(
        '-d',
        '--database',
        default='./onto.db',
        help='Database file to index into',
    )
    parser.add_argument(
        '-c',
        '--clean',
        default=False,
        action=argparse.BooleanOptionalAction,
        help='Remove all old indexed entities',
    )
    parser.add_argument(
        '-l',
        '--log',
        default="info",
        help='Set logging level',
    )

    result = parser.parse_args()
    main(result.input, result.clean, result.database, result.log)