#!/usr/bin/python3

import asyncio
import yaml
import socket
import sys
from imapclient import IMAPClient
from concurrent.futures import ProcessPoolExecutor

SOCKET_ADDRESS = '10.1.1.23'
SOCKET_PORT = 59993
HOSTNAME = 'imap.gmail.com'
MAILBOX = 'INBOX'

sys.stdout = sys.stderr

@asyncio.coroutine
def echo_client(msg):
    try:
        reader, writer = yield from asyncio.open_connection(
            SOCKET_ADDRESS,
            SOCKET_PORT,
            loop=loop,
        )

        print('Send: {}'.format(msg))
        writer.write(msg.encode())

        data = yield from reader.read(100)
        print("Received: {}".format(data.decode()))

        writer.close()
    except:
        print("Failed to connect to daemon.")

class Account(object):
    def __init__(self, username, password, debug=False):
        self.username = username
        self.password = password
        self.debug = debug

    def __call__(self):
        n = 0

        while True:
            if self.debug:
                print("Account: {} -> Opening [{}]".format(self.username, n))
            try:
                server = IMAPClient(HOSTNAME, use_uid=True, ssl=True)
                server.login(self.username, self.password)
                server.select_folder(MAILBOX)
                server.idle()
            except Exception as e:
                print("Account: {} -> Failed to initialize connection: {}".format(self.username, e))
                raise Exception("Failed to login")

            try:
                msg = server.idle_check(timeout=120)

                if msg:
                    print("Account: {} -> Message: {}".format(self.username, msg))

                for i in msg:
                    if b'EXISTS' in i:
                        message = "pulse 0 0 255 1 1000 60"
                        sock = socket.socket()
                        try:
                            sock.connect((SOCKET_ADDRESS, SOCKET_PORT))
                            sock.sendall(message.encode())

                        except Exception as e:
                            print("Account: {} -> socket send failed".format(self.username))
                            print(e)

                        finally:
                            sock.close()

                        if self.debug:
                            print("Account: {} -> sent blink".format(self.username))

            except Exception as e:
                print("Account: {} -> {}".format(self.username, e))

            finally:
                try:
                    server.idle_done()
                    server.logout()
                except: pass
                n += 1

with open("/root/maild.yml") as f: # Yes, this is running as root, sue me
    cfg = yaml.load(f.read())

accounts = list([Account(act, pwd, debug=False) for act, pwd in cfg.items()])

loop = asyncio.get_event_loop()

with ProcessPoolExecutor() as pool:
    T = list([loop.run_in_executor(pool, A) for A in accounts])
    loop.run_forever()
