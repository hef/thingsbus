import optparse
from thingsbus import thing
from zmqfan import zmqsub
import time
import socket
import msgpack

"""
General process for the broker: given the set of things you have, it will keep the latest data for each item, send snapshots on a regular pattern, etc - it also does fan-out, passing information to however many subscribers there are.
"""

INPUT_PORT = 7955
DIRECTORY_PORT = 7954
# tune these TODO
DIRECTORY_INTERVAL = 15
DIRECTORY_EXPIRE = 60
BLOCK_TIME = 0.05


class BrokerThing(thing.Thing):

    def emit_snapshot(self):
        with self.data_lock:
            return {
                'data': self.last_data,
                'ts': self.last_data_ts,
                'ns': self.ns,
                'documentation_url': self.documentation_url
            }

    @property
    def expired(self):
        if self.last_data_ts is None:
            return True
        elif self.last_data_ts < (time.time() - DIRECTORY_EXPIRE):
            return True
        else:
            return False


class Broker(object):

    def __init__(self, verbose=False):
        self.directory = thing.Directory(thing_class=BrokerThing)
        self.ok = True
        self.verbose = verbose

    def stop(self):
        self.ok = False

    def run(self):
        # ZMQ+tcp+json input - SUB
        self.adaptors_in = zmqsub.BindSub('tcp://*:%d' % INPUT_PORT)
        # UDP+msgpack input
        self.udpsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpsock.bind(('0.0.0.0', INPUT_PORT))
        # TODO on end, unbind that..

        self.directory_out = zmqsub.BindPub('tcp://*:%d' % DIRECTORY_PORT)
        self.sent_directory = time.time() - DIRECTORY_INTERVAL
        while self.ok:
            r, _w, _x = zmqsub.select([self.udpsock, self.adaptors_in], [], [], BLOCK_TIME)

            msgs = []

            # TODO handle the situation where fairness between the 2 methods of input can be too much,
            # resulting in one of the inputs being starved for consumption
            for sock in r:
                if sock is self.adaptors_in:
                    msgs.append(self.adaptors_in.recv(timeout=BLOCK_TIME))
                    if self.verbose:
                        print 'recvd zmq adaptor data.'
                elif sock is self.udpsock:
                    data, addr = self.udpsock.recvfrom(4096)
                    if self.verbose:
                        print 'recvd udp adaptor data'

                    try:
                        msgs.append(msgpack.loads(data))
                    except:
                        # TODO handle error better....
                        if self.verbose:
                            print 'failed to unpack msgpack udp packet, skipping'
                            print 'data: %s' % repr(data)
            for msg in msgs:
                try:
                    output_event = self.directory.handle_message(msg, accept_listmsg=True)
                    if output_event:
                        self.directory_out.send(output_event)
                        if self.verbose:
                            print 'sent event update for %s.' % output_event['ns']
                except thing.BadMessageException, bme:
                    if self.verbose:
                        print 'recvd bad message, skipped reason: %s' % str(bme)

            now = time.time()
            if now > self.sent_directory + DIRECTORY_INTERVAL:
                # time to send out a snapshot, for fun!
                # maybe we should send snapshots on another socket, later.
                snapshot_msg = {
                    'type': 'thing_snapshot',
                    'ts': now,
                    'data': dict([
                        (thing_obj.ns, thing_obj.emit_snapshot())
                        for
                        thing_obj
                        in
                        self.directory.all_things
                        if not thing_obj.expired
                    ])
                }
                self.directory_out.send(snapshot_msg)
                if self.verbose:
                    print 'sent snapshot of %d things.' % len(snapshot_msg['data'])
                self.sent_directory = now

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help="Verbose mode.")

    (opts, args) = parser.parse_args()

    broker_obj = Broker(verbose=opts.verbose)
    try:
        broker_obj.run()
    except KeyboardInterrupt:
        broker_obj.stop()
