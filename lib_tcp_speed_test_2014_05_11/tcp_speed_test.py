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

import asyncio
import socket
import os
import datetime

READER_LIMIT=10000000
READER_BUF=1000000
RND_GENERATOR_LEN=100

def try_print(*args, **kwargs):
    # safe version of ``print(..)``
    
    try:
        return print(*args, **kwargs)
    except (OSError, ValueError):
        pass

def blocking_create_rnd_generator():
    rnd_list = tuple(
            os.urandom(READER_BUF)
            for rnd_i in range(RND_GENERATOR_LEN)
            )
    
    def rnd_generator():
        while True:
            yield from rnd_list
    
    return rnd_generator()

@asyncio.coroutine    
def async_create_rnd_generator(loop):
    rnd_generator = yield from loop.run_in_executor(
            None,
            blocking_create_rnd_generator,
            )
    
    return rnd_generator

@asyncio.coroutine
def listen_cmd(loop, hostname, port):
    try:
        try_print('creating listen socket {!r}...'.format((hostname, port)))
        
        sock = socket.socket(socket.AF_INET6)
        
        if hasattr(socket, 'SO_REUSEADDR'):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except OSError:
                # SO_REUSEADDR is nice, but not required
                pass
        
        sock.bind((hostname, port))
        
        try_print('initialization random generator...')
        
        rnd_generator = yield from async_create_rnd_generator(loop)
        
        @asyncio.coroutine
        def client_connected_cb(client_reader, client_writer):
            client_writer.get_extra_info('socket').setsockopt(
                    socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            
            try_print('{!r}: accepted client connection'.format(client_writer.get_extra_info('peername')))
            
            while True:
                buf = next(rnd_generator)
                
                client_writer.write(buf)
                
                try:
                    yield from client_writer.drain()
                except OSError:
                    try_print('{!r}: closed client connection'.format(client_writer.get_extra_info('peername')))
                    return
        
        server = yield from asyncio.start_server(
                client_connected_cb,
                sock=sock,
                limit=READER_LIMIT,
                loop=loop,
                )
        
        try_print('start server successfully')
        
        yield from server.wait_closed()
    finally:
        try_print('shutdown')

@asyncio.coroutine
def connect_cmd(loop, hostname, port):
    try:
        try_print('making connection {!r}...'.format((hostname, port)))
        try:
            reader, writer = yield from asyncio.open_connection(
                    host=hostname, port=port, limit=READER_LIMIT, loop=loop)
        except OSError:
            try_print('connection fail')
            return
        
        writer.get_extra_info('socket').setsockopt(
                socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        try_print('connection successfully {!r}'.format(writer.get_extra_info('peername')))
        
        last_time = datetime.datetime.now()
        buf_summ = 0
        while True:
            try:
                buf = yield from reader.read(READER_BUF)
            except OSError:
                buf = None
            
            if not buf:
                try_print('connection closed')
                return
            
            time_delta = datetime.datetime.now() - last_time
            buf_summ += len(buf)
            
            if time_delta >= datetime.timedelta(seconds=1.0):
                speed = buf_summ / time_delta.total_seconds()
                mbit_speed = round(speed * 8 / 1000 / 1000)
                
                try_print('download speed: {} Mbit/s ({} b/s)'.format(mbit_speed, speed))
                
                last_time = datetime.datetime.now()
                buf_summ = 0
    finally:
        try_print('shutdown')
