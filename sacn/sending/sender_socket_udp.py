# This file is under MIT license. The license file can be obtained in the root directory of this module.

import socket
import threading

from sacn.sending.sender_socket_base import SenderSocketBase

THREAD_NAME = 'sACN sending/sender thread'
DEFAULT_PORT = 5568


class SenderSocketUDP(SenderSocketBase):
    """
    Implements a sender socket with a UDP socket of the OS.
    """

    def __init__(self, listener: SenderSocketListener, bind_address: str, bind_port: int, fps: int):
        super().__init__(listener=listener)

        self._bind_address: str = bind_address
        self._bind_port: int = bind_port
        self._enabled_flag: bool = True
        self.fps: int = fps

        # initialize the UDP socket
        self._socket: socket.socket = socket.socket(socket.AF_INET,  # Internet
                                                    socket.SOCK_DGRAM)  # UDP
        try:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except:  # noqa: E722 Not all systems support multiple sockets on the same port and interface
            pass

        try:
            self._socket.bind((self._bind_address, self._bind_port))
            self._logger.info(f'Bind sender thread to IP:{self._bind_address} Port:{self._bind_port}')
        except socket.error:
            self._logger.exception(f'Could not bind to IP:{self._bind_address} Port:{self._bind_port}')
            raise

    def start(self):
        # initialize thread infos
        thread = threading.Thread(
            target=self.send_loop,
            name=THREAD_NAME
        )
        # thread.setDaemon(True)  # TODO: might be beneficial to use a daemon thread
        thread.start()

    def send_loop(self) -> None:
        self._logger.info(f'Started {THREAD_NAME}')
        self._enabled_flag = True
        while self._enabled_flag:
            time_stamp = time.time()
            self._listener.on_periodic_callback()
            time_to_sleep = (1 / self.fps) - (time.time() - time_stamp)
            if time_to_sleep < 0:  # if time_to_sleep is negative (because the loop has too much work to do) set it to 0
                time_to_sleep = 0
            time.sleep(time_to_sleep)
            # this sleeps nearly exactly so long that the loop is called every 1/fps seconds

        self._logger.info(f'Stopped {THREAD_NAME}')

    def stop(self) -> None:
        """
        Stop a potentially running thread by gracefull shutdown. Does not stop the thread immediately.
        """
        self._enabled_flag = False

    def send_unicast(self, data: bytearray, destination: str) -> None:
        self.send_packet(data, destination)

    def send_multicast(self, data: bytearray, destination: str, ttl: int) -> None:
        # make socket multicast-aware: (set TTL)
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        self.send_packet(data, destination)

    def send_broadcast(self, data: bytearray) -> None:
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.send_packet(data, destination='<broadcast>')

    def send_packet(self, data: bytearray, destination: str) -> None:
        try:
            self._socket.sendto(data, (destination, DEFAULT_PORT))
        except OSError as e:
            self._logger.warning('Failed to send packet', exc_info=e)
