# Warnet: The Wrath Of Nalo

![nalo](./docs/nalo-legend.jpg)

```
(.venv) $ warnet ln rpc armada-1-ln walletbalance
{
    "total_balance":  "10000000000",
    "confirmed_balance":  "10000000000",
    "unconfirmed_balance":  "0",
    "locked_balance":  "0",
    "reserved_balance_anchor_chan":  "0",
    "account_balance":  {
        "default":  {
            "confirmed_balance":  "10000000000",
            "unconfirmed_balance":  "0"
        }
    }
}
```

```
(.venv) $ warnet ln rpc armada-1-ln connect 02dceade95abc5635611f3e096ff7d8c7491006f4742d9ed581ccc23d317a37ed8@tank-0002-ln.default
{
    "status":  "connection to 02dceade95abc5635611f3e096ff7d8c7491006f4742d9ed581ccc23d317a37ed8@10.108.5.24:9735 initiated"
}
```

```
(.venv) $ warnet ln rpc armada-1-ln openchannel --local_amt=12345678 039e483a49be48fde184e0fca39d53c7a12639212e25dc16c6e7149687b5e636e2
{
    "funding_txid": "39dd8f08511c3955143b3b90f6cbd72779566c1d093b59443de661b06e0e273b"
}
```

```
(.venv) $ warnet ln rpc armada-1-ln openchannel 0328ed8ed73d267c117fa7406eb093458fce613a06aec9dc18df1a313d12895e5a --connect tank-0000-ln.default --local_amt=10000000
{
    "funding_txid": "1840a6d8a003f89abf1a633fee32bae8b96cf1707df174f852a4ee98f2f36718"
}
```

```
(.venv) $ warnet ln rpc armada-1-ln pendingchannels
{
    "total_limbo_balance":  "0",
    "pending_open_channels":  [
        {
            "channel":  {
                "remote_node_pub":  "039e483a49be48fde184e0fca39d53c7a12639212e25dc16c6e7149687b5e636e2",
                "channel_point":  "39dd8f08511c3955143b3b90f6cbd72779566c1d093b59443de661b06e0e273b:0",
                "capacity":  "12345678",
                "local_balance":  "12342208",
                "remote_balance":  "0",
                "local_chan_reserve_sat":  "123456",
                "remote_chan_reserve_sat":  "123456",
                "initiator":  "INITIATOR_LOCAL",
                "commitment_type":  "ANCHORS",
                "num_forwarding_packages":  "0",
                "chan_status_flags":  "",
                "private":  false,
                "memo":  "",
                "custom_channel_data":  ""
            },
            "commit_fee":  "2810",
            "commit_weight":  "772",
            "fee_per_kw":  "2500",
            "funding_expiry_blocks":  2015
        }
    ],
    "pending_closing_channels":  [],
    "pending_force_closing_channels":  [],
    "waiting_close_channels":  []
}
```