# -*- mode: python; coding: utf-8 -*-
#
# Copyright (c) 2014 Andrej Antonov <polymorphm@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

assert str is not bytes

from . import tcp_speed_test

import argparse
import asyncio
import signal

def main():
    parser = argparse.ArgumentParser(
            description='simple utility for testing speed of TCP-socket channel',
            )
    
    subparsers = parser.add_subparsers(
            dest='cmd',
            )
    
    listen_cmd_parser = subparsers.add_parser(
            'listen',
            help='listen for connection',
            description='listen for connection. speed info will NOT be shown',
            )
    
    listen_cmd_parser.add_argument(
            'hostname',
            metavar='HOSTNAME',
            help='hostname for listen. '
                    'use IPv6-format (example -- "::ffff:127.0.0.1"). '
                    'use "::" for listen on all interfaces',
            )
    
    listen_cmd_parser.add_argument(
            'port',
            type=int,
            metavar='PORT',
            help='port for listen',
            )
    
    connect_cmd_parser = subparsers.add_parser(
            'connect',
            help='make connection to listener',
            description='make connection to listener. will be shown download speed',
            )
    
    connect_cmd_parser.add_argument(
            'hostname',
            metavar='HOSTNAME',
            help='hostname to connect. '
                    'use IPv6-format (example -- "::ffff:127.0.0.1")',
            )
    
    connect_cmd_parser.add_argument(
            'port',
            type=int,
            metavar='PORT',
            help='port to connect',
            )
    
    args = parser.parse_args()
    
    if args.cmd is None:
        parser.print_help()
        exit()
    
    loop = asyncio.get_event_loop()
    
    if args.cmd == 'listen':
        cmd_future = asyncio.async(
                tcp_speed_test.listen_cmd(loop, args.hostname, args.port),
                loop=loop,
                )
    elif args.cmd == 'connect':
        cmd_future = asyncio.async(
                tcp_speed_test.connect_cmd(loop, args.hostname, args.port),
                loop=loop,
                )
    else:
        raise NotImplementedError
    
    def shutdown_handler():
        cmd_future.cancel()
    
    for sig_name in ('SIGINT', 'SIGTERM'):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            try:
                loop.add_signal_handler(sig, shutdown_handler)
            except NotImplementedError:
                pass
    
    @asyncio.coroutine
    def wait_coro():
        yield from asyncio.wait((cmd_future,), loop=loop)
    
    loop.run_until_complete(wait_coro())
