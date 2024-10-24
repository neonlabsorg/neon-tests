import rlp
from rlp.sedes import big_endian_int, binary


class ScheduledTxRLP(rlp.Serializable):

    fields = [
        ("payer", rlp.sedes.Binary(min_length=20, max_length=20, allow_empty=False)),
        ("sender", rlp.sedes.Binary(min_length=20, max_length=20, allow_empty=True)),
        ("nonce", big_endian_int),
        ("index", big_endian_int),
        ("intent", binary),
        ("intent_call_data", binary),
        ("target", rlp.sedes.Binary(min_length=20, max_length=20, allow_empty=True)),
        ("call_data", binary),
        ("value", big_endian_int),
        ("chain_id", big_endian_int),
        ("gas_limit", big_endian_int),
        ("max_fee_per_gas", big_endian_int),
        ("max_priority_fee_per_gas", big_endian_int),
    ]


def encode_scheduled_trx(
    payer,
    sender,
    nonce,
    index,
    target,
    intent=None,
    intent_call_data=None,
    call_data=None,
    value=0,
    chain_id=112,
    gas_limit=9999999999,
    max_fee_per_gas=100,
    max_priority_fee_per_gas=10,
):
    tx = ScheduledTxRLP(
        payer=payer,
        sender=sender if sender else b"",
        nonce=nonce,
        index=index,
        intent=intent if intent else b"",
        intent_call_data=intent_call_data if intent_call_data else b"",
        target=target,
        call_data=call_data if call_data else b"",
        value=value,
        chain_id=chain_id,
        gas_limit=gas_limit,
        max_fee_per_gas=max_fee_per_gas,
        max_priority_fee_per_gas=max_priority_fee_per_gas,
    )
    type = 0x7F
    sub_type = 0x01
    return bytes([type]) + bytes([sub_type]) + rlp.encode(tx)
