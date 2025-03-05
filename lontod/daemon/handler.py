from http.server import BaseHTTPRequestHandler
from sqlite3 import Connection
from logging import Logger
from ..indexer import Query
from mimeparse import best_match, MimeTypeParseException 

class Handler:
    def __init__(self, query: Query, logger: Logger):
        self.query = query
        self.logger = logger

    def __call__(self, handler: BaseHTTPRequestHandler):
        """ Call responds to a GET request on the given handler """
        
        try:
            self._serve_ontology(handler, '') # for now!
        except Exception as err:
            handler.send_error(500, 'Something went wrong')
            raise err
            
    def _serve_ontology(self, handler: BaseHTTPRequestHandler, slug: str):
        accepts = handler.headers.get_all('accept')

        # find the mime times we can serve for this ontology
        offers = self.query.get_mime_types(slug)
        if len(offers) == 0:
            handler.send_error(404, 'Ontology not found')
            return

        

        # decide on the actual content type
        decision = None 
        if len(accepts) > 0:
            try:
                decision = best_match(offers, ','.join(accepts))
            except MimeTypeParseException:
                pass
        
        if decision is None or decision not in offers:
            decision = 'text/plain' if 'text/plain' in offers else None
             
        if decision is None:
            handler.send_error(406, 'No available content type')
            return

        self.logger.debug('ontology %r: decided on %s', slug, decision) 
        result = self.query.get_data(slug, decision)
        if result is None:
            handler.send_error(500, 'Negotiated content type went away')
            return
        
        handler.send_response(200,)
        handler.send_header('Content-Type', decision)
        handler.end_headers()

        handler.wfile.write(result)
