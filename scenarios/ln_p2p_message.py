#!/usr/bin/env python3

from io import BytesIO
import random

from commander import Commander

########
# This scenario relies on pyln-proto, a python implementation of the Lightning
# Network p2p protocol (including the handshake and noise encryption).
# It is maintained by and used for testing in the Core Lightning project:
# https://github.com/ElementsProject/lightning/tree/master/contrib/pyln-proto
#
# Proper documentation of this library is scarce, but there are lots of good
# examples in a related package, pyln-spec:
# https://github.com/ElementsProject/lightning/tree/master/contrib/pyln-spec
########
from pyln.proto.message import Message, MessageNamespace
from pyln.proto.wire import PrivateKey, PublicKey, connect

# genesis block hash is used as a chain identifer in some messages
GENESIS = {
    "regtest": "0f9188f13cb7b2c71f2a335e3a4fc328bf5beb436012afca590b1a11466e2206",
    "signet": "00000008819873e925422c1ff0f99f7cc9bbb232af63a077a480a3633bee1ef6"
}

# Define p2p messages from BOLT specs
ns = MessageNamespace([
    # init (BOLT#1)
    "msgtype,init,16",
    "msgdata,init,gflen,u16,",
    "msgdata,init,globalfeatures,byte,gflen",
    "msgdata,init,flen,u16,",
    "msgdata,init,features,byte,flen",

    # ping (BOLT#1)
    "msgtype,ping,18",
    "msgdata,ping,num_pong_bytes,u16,",
    "msgdata,ping,byteslen,u16,",
    "msgdata,ping,ignored,byte,byteslen",

    # pong (BOLT#1)
    "msgtype,pong,19",
    "msgdata,pong,byteslen,u16,",
    "msgdata,pong,ignored,byte,byteslen",

    # update_add_htlc (BOLT#2)
    # This message contains an onion packet!
    "msgtype,update_add_htlc,128",
    "msgdata,update_add_htlc,channel_id,channel_id,",
    "msgdata,update_add_htlc,id,u64,",
    "msgdata,update_add_htlc,amount_msat,u64,",
    "msgdata,update_add_htlc,payment_hash,sha256,",
    "msgdata,update_add_htlc,cltv_expiry,u32,",
    "msgdata,update_add_htlc,onion_routing_packet,byte,1366",

    # query_channel_range (BOLT#7)
    # LND likes to send this after init
    "msgtype,query_channel_range,263,gossip_queries",
    "msgdata,query_channel_range,chain_hash,chain_hash,",
    "msgdata,query_channel_range,first_blocknum,u32,",
    "msgdata,query_channel_range,number_of_blocks,u32,",
    "msgdata,query_channel_range,tlvs,query_channel_range_tlvs,",
    "tlvtype,query_channel_range_tlvs,query_option,1",
    "tlvdata,query_channel_range_tlvs,query_option,query_option_flags,bigsize,",

    # gossip (BOLT#7)
    "msgtype,channel_announcement,256",
    "msgdata,channel_announcement,node_signature_1,signature,",
    "msgdata,channel_announcement,node_signature_2,signature,",
    "msgdata,channel_announcement,bitcoin_signature_1,signature,",
    "msgdata,channel_announcement,bitcoin_signature_2,signature,",
    "msgdata,channel_announcement,len,u16,",
    "msgdata,channel_announcement,features,byte,len",
    "msgdata,channel_announcement,chain_hash,chain_hash,",
    "msgdata,channel_announcement,short_channel_id,short_channel_id,",
    "msgdata,channel_announcement,node_id_1,point,",
    "msgdata,channel_announcement,node_id_2,point,",
    "msgdata,channel_announcement,bitcoin_key_1,point,",
    "msgdata,channel_announcement,bitcoin_key_2,point,",
    "msgtype,node_announcement,257",
    "msgdata,node_announcement,signature,signature,",
    "msgdata,node_announcement,flen,u16,",
    "msgdata,node_announcement,features,byte,flen",
    "msgdata,node_announcement,timestamp,u32,",
    "msgdata,node_announcement,node_id,point,",
    "msgdata,node_announcement,rgb_color,byte,3",
    "msgdata,node_announcement,alias,byte,32",
    "msgdata,node_announcement,addrlen,u16,",
    "msgdata,node_announcement,addresses,byte,addrlen",
    "msgtype,channel_update,258",
    "msgdata,channel_update,signature,signature,",
    "msgdata,channel_update,chain_hash,chain_hash,",
    "msgdata,channel_update,short_channel_id,short_channel_id,",
    "msgdata,channel_update,timestamp,u32,",
    "msgdata,channel_update,message_flags,byte,",
    "msgdata,channel_update,channel_flags,byte,",
    "msgdata,channel_update,cltv_expiry_delta,u16,",
    "msgdata,channel_update,htlc_minimum_msat,u64,",
    "msgdata,channel_update,fee_base_msat,u32,",
    "msgdata,channel_update,fee_proportional_millionths,u32,",
    "msgdata,channel_update,htlc_maximum_msat,u64,",

    # gossip_timestamp_filter (BOLT#7)
    "msgtype,gossip_timestamp_filter,265,gossip_queries",
    "msgdata,gossip_timestamp_filter,chain_hash,chain_hash,",
    "msgdata,gossip_timestamp_filter,first_timestamp,u32,",
    "msgdata,gossip_timestamp_filter,timestamp_range,u32,",
])


class LNP2PMessage(Commander):
    def set_test_params(self):
        self.num_nodes = 0

    def add_options(self, parser):
        parser.description = "Send p2p messages directly to a LN node"
        parser.usage = "warnet run /path/to/ln_p2p_message.py [options]"
        parser.add_argument(
            "--peer",
            dest="peer",
            type=str,
            help="The complete uri pubkey@host:port to connect and send messages to",
        )

    def run_test(self):
        # Clear the Warnet default random seed
        random.seed(None)
        # Determine what network we are in
        chain = self.nodes[0].chain
        chain_hash = GENESIS[chain]

        # Find the target node
        pk, host = self.options.peer.split("@")
        host, port = host.split(":")
        self.log.info(f"Found node {self.options.peer} at {pk}@{host}:{port}")

        # Create an ephemeral identity key for ourselves
        id_privkey = PrivateKey(random.randbytes(32))

        # Establish a p2p connection to the peer
        connection = connect(id_privkey, PublicKey(bytes.fromhex(pk)), host, port)

        # Define helper functions for connection I/O
        def send(msg):
            buf = BytesIO()
            msg.write(buf)
            connection.send_message(buf.getvalue())
            self.log.info(f">>> {msg.messagetype} {msg.to_py()}")

        def recv():
            msg = connection.read_message()
            stream = BytesIO(msg)
            try:
                msg = Message.read(ns, stream)
                self.log.info(f"<<< {msg.messagetype} {msg.to_py()}")
            except:
                self.log.error(f"Could not parse message from peer:\n{stream.getvalue().hex()}")

            ########
            # API for the Message class:
            # https://github.com/ElementsProject/lightning/blob/c7531b0f8f5fc14a46cd05525f8cb9b3bdebeb5d/contrib/pyln-proto/pyln/proto/message/message.py#L594
            # (messagetype: MessageType, **kwargs)
            # "MessageType is the type of this msg, with fields.
            #  Fields can either be valid values for the type,"
            #  or if they are strings they are converted according
            #  to the field type"
            ########
            init_msg = Message(ns.get_msgtype("init"),
                                globalfeatures=b"\x12\x00",
                                # feature bits naively copied from a message sent by LND
                                features=bytes.fromhex(
                                    "800000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000000000000000000000000000000000000000" +
                                    "000000000000002000888252a1"))
            # Send init
            send(init_msg)
            # Receive init
            recv()

            # Build ping
            ping_msg = Message(ns.get_msgtype("ping"),
                               num_pong_bytes=0,
                               ignored=b"")
            # Send ping
            send(ping_msg)
            # Receive pong
            recv()

def main():
    LNP2PMessage("").main()


if __name__ == "__main__":
    main()
