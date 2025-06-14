import typing
from http.server import HTTPServer, BaseHTTPRequestHandler
from queue import Queue
from urllib.parse import parse_qs


class RequestHandler(BaseHTTPRequestHandler):

    @staticmethod
    def content_type():
        return 'text/plain'

    @staticmethod
    def success_message():
        return 'Authorization was successful.  You may close this tab and return to the client.'

    @staticmethod
    def error_message():
        return 'Authorization did not complete :(.  You may close this tab and return to the client.'

    def do_GET(self):  # noqa
        self.send_response(200)
        self.send_header('Content-type', self.content_type())
        self.end_headers()

        params = parse_qs(self.path[2:])  # path begins with /?

        # Write response body
        server: LocalHTTPServer = typing.cast(LocalHTTPServer, self.server)
        message = self.success_message() if params.get('code') else self.error_message()
        self.wfile.write(message.encode())

        server.queue.put(params)


class LocalHTTPServer(HTTPServer):

    def __init__(self, queue: Queue, port=8001, request_handler: type[RequestHandler] = None):
        self.port = port
        self.queue = queue

        server_address = ('', port)
        request_handler = request_handler if request_handler else RequestHandler
        super().__init__(server_address, request_handler)  # type: ignore


if __name__ == '__main__':
    httpd = LocalHTTPServer(Queue())
    httpd.serve_forever()
