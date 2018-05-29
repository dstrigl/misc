#!/usr/bin/env python3

import os
import select
import fcntl
import threading
import time
import queue
import socket
import struct
import urllib.parse
import datetime
import queue

import logging
_logger = logging.getLogger(__name__)
_logger = logging.LoggerAdapter(_logger, extra={"facility": "network"})


class Notify:
    """ Class to notify other thread per pipe.
    """

    #_recvfd = None  # File descriptor to watch
    #_sendfd = None  # File descriptor to notify
 
    def __init__(self):
        # Create a new pipe
        self._recvfd, self._sendfd = os.pipe()
        fcntl.fcntl(self._sendfd, fcntl.F_SETFL, os.O_NONBLOCK)

    def __del__(self):
        # Close the file descriptors
        os.close(self._recvfd)
        os.close(self._sendfd)

    @property
    def notify_fd(self):
        """ Returns the file descriptor to watch for notify event.

        :returns: The file descriptor to watch for as ``int``.
        :rtype: ``int``
        """
        return self._recvfd

    def notify(self):
        """ Writes a notify event to the file descriptor.

        :returns: The number of written bytes; should be 1 in case of success.
        :rtype: ``int``
        """
        return os.write(self._sendfd, b"1")


class NetMessage:
    """ Class for data/message transfer between :class:`Connection` and :class:`MainLoop`.

    :param is_http: Defines whether this is a HTTP message or not.
    :type is_http: bool
    """

    #_is_http = False
    #_condition = None
    #_listening = False
    #_listen_since = None
    #_disconnect = False
    #_request = ""
    #_result = None

    def __init__(self, is_http):
        assert isinstance(is_http, bool)
        self._is_http = is_http
        self._condition = threading.Condition()
        self._listening = False
        self._listen_since = None
        self._disconnect = False
        self._request = ""
        self._result = None

    def __del__(self):
        pass  # nothing to do!

    def is_http(self):
        """ Returns whether this is a HTTP message or not.

        :returns: :const:`True` if it is a HTTP message, :const:`False` otherwise.
        :rtype: ``bool``
        """
        return self._is_http

    @property
    def request(self):
        """ Returns the request string.

        :returns: The request string.
        :rtype: ``str``
        """
        return self._request

    def is_listening(self):
        """ Returns whether the client is in listening mode.

        :returns: A tuple, where the first element represents whether the client is
            in listening mode while the second element is the start time from which
            updates were added (inclusive).
        :rtype: ``tuple`` ( bool, datetime.datetime )
        """
        return (self._listening, self._listen_since)

    def is_disconnect(self):
        """ Returns whether the client shall be disconnected.

        :returns: :const:`True` if the client shall be disconnected, :const:`False` otherwise.
        """
        return self._disconnect

    def add(self, request):
        """ Adds request data received from the client.

        :param request: The request data from the client.
        :type request: str
        :returns: :const:`True` when the request is complete and the response shall be prepared,
            :const:`False` otherwise.
        :rtype: ``bool``
        """
        assert isinstance(request, str)
        self._request += request.replace("\r", "")  # remove all "\r"
        pos = self._request.find("\n\n" if self._is_http else "\n")
        if pos != -1:
            if self._is_http:
                pos = self._request.find("\n")
                self._request = self._request[:pos]  # reduce to first line
                # typical first line: GET /ehp/outsidetemp HTTP/1.1  # TODO
                pos = self._request.rfind(" HTTP/")
                if pos != -1:
                    self._request = self._request[:pos]  # remove " HTTP/x.x" suffix
                # replace "%xx" escapes by their single-character equivalent
                self._request = urllib.parse.unquote(self._request)
            elif pos + 1 == len(self._request):
                self._request = self._request[:pos]  # reduce to complete lines
            return True
        return len(self._request) == 0 and self._listening

    def get_result(self):
        """ Wait for the result being set and return the result string.

        :returns: The result string.
        :rtype: ``str``
        """
        with self._condition:
            if self._result is None:
                self._condition.wait()  # wait until result becomes available
            self._request = ""
            ret = self._result
            self._result = None
            return ret

    def set_result(self, result, listening, listen_until, disconnect):
        """ Sets the result string and notify the waiting thread.

        :param result: The result string.
        :type result: str
        :param listening: Defines whether the client is in listening mode or not.
        :type listening: bool
        :param listen_until: The end time to which updates were added (exclusive).
        :type listen_until: None or datetime.datetime
        :param disconnect: :const:`True` when the client shall be disconnected,
            :const:`False` otherwise.
        :type disconnect: bool
        """
        assert isinstance(result, str)
        assert isinstance(listening, bool)
        assert listen_until is None or isinstance(listen_until, datetime.datetime)
        assert isinstance(disconnect, bool)
        with self._condition:
            self._result = result
            self._listening = listening
            self._listen_since = listen_until
            self._disconnect = disconnect
            self._condition.notify()  # signal that a new result is available


class TcpSocket:
    """ Class for low level TCP socket operations (open, close, send, receive).

    :param device: The socket object.
    :type sock: socket.socket
    """

    #_socket = None  # the socket instance

    def __init__(self, sock):
        _logger.debug("TcpSocket.__init__()")
        assert isinstance(sock, socket.socket)
        self._socket = sock

    def __del__(self):
        # Close the socket
        _logger.debug("TcpSocket.__del__()")
        self._socket.close()

    @property
    def ip_addr(self):
        """ Returns the IP address of the socket.

        :returns: The IP address as ``str``.
        :rtype: ``str``
        """
        return self._socket.getsockname()[0]

    @property
    def port(self):
        """ Returns the TCP port number of the socket.

        :returns: The TCP port number as ``int``.
        :rtype: ``int``
        """
        return self._socket.getsockname()[1]

    @property
    def socket_fd(self):
        """ Returns the socket's file descriptor, or -1 on failure.

        :returns: The file descriptor of the socket as ``int`` (-1 on failure).
        :rtype: ``int``
        """
        return self._socket.fileno()

    def is_valid(self):
        """ Returns whether the file descriptor of the socket is valid or not.

        :returns: :const:`True` if the file descriptor of the socket is valid,
            :const:`False` otherwise.
        :rtype: ``bool``
        """
        return fcntl.fcntl(self._socket.fileno(), fcntl.F_GETFL) != -1

    def set_timeout(self, timeout):
        """ Sets the timeout for :func:`send` and :func:`recv`.

        :param timeout: The timeout value in seconds as ``int`` or ``float``.
        :type timeout: int or float
        """
        assert isinstance(timeout, (int, float))
        tv_sec = int(timeout)  # seconds
        tv_usec = int((timeout - tv_sec) * 1e6)  # microseconds
        timeval = struct.pack("LL", tv_sec, tv_usec)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeval)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeval)

    def send(self, data):
        """ Writes a string to the socket.

        :param data: The provided string.
        :type data: str
        :returns: The number of sent bytes.
        :rtype: ``int``
        """
        return self._socket.send(data.encode("ascii"), socket.MSG_NOSIGNAL)

    def recv(self, len):
        """ Reads a defined amount of bytes/characters from the socket.

        :param len: The amount of bytes/characters to read.
        :type len: int
        :returns: The read byte array as string.
        :rtype: ``str``
        """
        assert isinstance(len, int)
        data = self._socket.recv(len)
        return data.decode("ascii")

    def __repr__(self):
        return repr(self._socket)

    def __str__(self):
        return str(self._socket)


class TcpServer:
    """ Class for a TCP based network server.

    :param port: The port number.
    :type port: int
    :param addr: The IP address.
    :type addr: str
    :param backlog: The number of unaccepted connections before refusing new connections.
    :type backlog: int
    """

    #_port = None        # TCP port number
    #_addr = None        # IP address
    #_backlog = 0        # number of unaccepted connections before refusing new connections
    #_listening = False  # defines whether the object is listening or not
    #_socket = None      # the socket of the network server

    def __init__(self, port, addr, backlog=5):
        _logger.debug("TcpServer.__init__()")
        assert isinstance(port, int)
        assert isinstance(addr, str)
        assert isinstance(backlog, int)
        self._port = port
        self._addr = addr
        self._backlog = backlog if backlog >= 0 else 0
        self._listening = False
        self._socket = None

    def __del__(self):
        _logger.debug("TcpServer.__del__()")
        # Close the socket of the server
        if self._socket:
            self._socket.close()

    def start(self):
        """ Starts listening for incoming TCP connection requests.
        """
        if self._listening:
            return  # already running!
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self._addr, self._port))
            self._socket.listen(self._backlog)
            self._listening = True
        except OSError as ex:
            _logger.error("failed to start TCP server: {!s}".format(ex))
            if self._socket:
                self._socket.close()
            self._socket = None
            raise

    def new_socket(self):
        """ Accepts an incoming connection request and creates a local TCP socket for communication.

        :returns: An instance of :class:`TcpSocket` or ``None`` on failure.
        :rtype: :class:`TcpSocket`
        """
        if not self._listening:
            return None
        try:
            sock, _ = self._socket.accept()
            return TcpSocket(sock)
        except OSError:
            return None

    @property
    def socket_fd(self):
        """ Returns the socket's file descriptor, or -1 on failure.

        :returns: The file descriptor of the socket as ``int`` (-1 on failure).
        :rtype: ``int``
        """
        return -1 if not self._listening else self._socket.fileno()


class Connection(threading.Thread):
    """ TODO doc
    """

    #_notify = None
    #_socket = None
    #_is_http = False
    #_net_queue = None
    #_id = 0
    _ids = 0

    def __init__(self, sock, is_http, net_queue):
        _logger.debug("Connection.__init__()")
        assert isinstance(sock, TcpSocket)
        assert isinstance(is_http, bool)
        assert isinstance(net_queue, queue.Queue)
        threading.Thread.__init__(self, name="Connection-Thread<{}:{:d}>".format(sock.ip_addr, sock.port))
        self._notify = Notify()
        self._socket = sock
        self._is_http = is_http
        self._net_queue = net_queue
        Connection._ids += 1
        self._id = Connection._ids

    def __del__(self):
        _logger.debug("Connection.__del__()")
        pass  # nothing to do!

    @property
    def id(self):
        """ Returns the ID of this connection.

        :returns: The ID of this connection.
        :rtype: ``int``
        """
        return self._id

    def stop(self):
        """ TODO doc
        """
        self._notify.notify()

    def __repr__(self):
        return "Connection<{}:{:d}>".format(self._socket.ip_addr, self._socket.port)

    def run(self):
        _logger.debug("Connection.run()")
        rlist = [self._notify.notify_fd, self._socket.socket_fd]
        xlist = rlist

        closed = False
        message = NetMessage(self._is_http)

        while not closed:
            readable, _, exceptional = select.select(rlist, [], xlist, 2)  # timeout = 2s
            if self._notify.notify_fd in (readable + exceptional):
                break  # notification for shutdown received!
            new_data = self._socket.socket_fd in readable
            closed = self._socket.socket_fd in exceptional

            if new_data or message.is_listening():
                if not self._socket.is_valid():
                    break
                data = ""
                if new_data:
                    data = self._socket.recv(1024)  # TODO: try/except needed?
                    if len(data) == 0:
                        break  # remove closed socket
                    _logger.debug("[{:d}] received data {!r}".format(self.id, data))

                # decode client data
                if message.add(data):
                    _logger.debug("[{:d}] new request {!r}".format(self.id, message.request))
                    self._net_queue.put(message)
                    # wait for result
                    _logger.debug("[{:d}] wait for result ...".format(self.id))
                    result = message.get_result()
                    _logger.debug("[{:d}] get result {!r}".format(self.id, result))
                    if not self._socket.is_valid():
                        break
                    self._socket.send(result)  # TODO: try/except needed?

                if message.is_disconnect() or not self._socket.is_valid():
                    break

        _logger.info("[{:d}] connection closed".format(self.id))


class Network(threading.Thread):

    #_notify = None
    #_connections = []
    #_net_queue = None
    #_tcp_server = None
    #_http_server = None
    #_listening = False

    def __init__(self, local, port, http_port, net_queue):
        assert isinstance(local, bool)
        assert isinstance(port, int)
        assert isinstance(http_port, int)
        assert isinstance(net_queue, queue.Queue)
        _logger.debug("Network.__init__()")
        threading.Thread.__init__(self, name="Network-Thread")
        self._notify = Notify()
        self._connections = []
        self._net_queue = net_queue
        self._tcp_server = TcpServer(port, "127.0.0.1" if local else "")
        self._tcp_server.start()
        self._listening = True
        if http_port > 0:
            self._http_server = TcpServer(http_port, "")
            self._http_server.start()
        else:
            self._http_server = None
        # TODO: possible problem if _listening = True, but start of _http_server failed?!

    def __del__(self):
        _logger.debug("Network.__del__()")
        self.stop()
        while True:
            try:
                message = self._net_queue.get_nowait()
                message.set_result("ERR: shutdown", False, None, True)
            except queue.Empty:
                break
        while len(self._connections) > 0:
            conn = self._connections.pop()
            conn.stop()
            conn.join()
        self._tcp_server = None
        self._http_server = None
        self.join()

    def run(self):
        _logger.debug("Network.run()")
        if not self._listening:
            return
        rlist = [self._notify.notify_fd, self._tcp_server.socket_fd]
        if self._http_server:
            rlist.append(self._http_server.socket_fd)
        while True:
            readable, _, _ = select.select(rlist, [], [], 1)  # timeout = 1s
            if len(readable) == 0:  # timeout -> perform a cleanup of all connections
                self.clean_connections()
                continue
            new_conn = is_http = False
            if self._notify.notify_fd in readable:
                _logger.debug("Network.run(): shutdown")
                return  # shutdown
            if self._tcp_server.socket_fd in readable:
                _logger.debug("Network.run(): new TCP connection")
                new_conn = True
            elif self._http_server and self._http_server.socket_fd in readable:
                _logger.debug("Network.run(): new HTTP connection")
                new_conn = is_http = True
            if new_conn:
                sock = self._tcp_server.new_socket()
                if not sock:
                    continue
                conn = Connection(sock, is_http, self._net_queue)
                _logger.info("Network.run(): new connection {}".format(conn))
                conn.start()
                self._connections.append(conn)
                del sock, conn

    def stop(self):
        _logger.debug("Network.stop()")
        self._notify.notify()
        time.sleep(0.1)  # wait for 100ms

    def clean_connections(self):
        dead_conn = [conn for conn in self._connections if not conn.is_alive()]
        self._connections = [conn for conn in self._connections if conn not in dead_conn]
        if dead_conn:
            _logger.debug("removed {:d} dead connection(s) {}".format(len(dead_conn), dead_conn))









def main():
    #logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)-15s] (%(threadName)s %(facility)s %(levelname)s): %(message)s',
    )
    try:
        _logger.debug("main #1")
        q = queue.Queue()
        network = Network(local=True, port=8888, http_port=0, net_queue=q)
        network.start()
        #_logger.debug("main #2, wait 30s ...")
        #time.sleep(30)
        #_logger.debug("main #3, stop")
        #network.stop()
        #_logger.debug("main #4, wait 3s ...")
        #time.sleep(3)
        network.join()
        _logger.debug("main #5")
    except KeyboardInterrupt:
        _logger.debug("KeyboardInterrupt")
        network.stop()
        network.join()

if __name__ == "__main__":
    main()
