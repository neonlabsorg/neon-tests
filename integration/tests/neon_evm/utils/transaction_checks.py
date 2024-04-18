import base64

from solana.rpc.commitment import Confirmed

from ..solana_utils import solana_client


def check_transaction_logs_have_text(trx_hash, text):
    receipt = solana_client.get_transaction(trx_hash)
    logs = decode_logs(receipt.value.transaction.meta.log_messages)
    assert text in logs, f"Transaction logs don't contain '{text}'. Logs: {logs}"

def decode_logs(log_messages):
    decoded_logs = ""

    for log in log_messages:
        if "Program data:" in log:
            decoded_logs += "Program data: "
            encoded_part = log.replace("Program data: ", "")
            for item in encoded_part.split(" "):
                decoded_logs += " " + str(base64.b64decode(item))
        else:
            decoded_logs += log
        decoded_logs += " "
    return decoded_logs

def check_holder_account_tag(storage_account, layout, expected_tag):
    account_data = solana_client.get_account_info(storage_account, commitment=Confirmed).value.data
    parsed_data = layout.parse(account_data)
    assert parsed_data.tag == expected_tag, f"Account tag {account_data[0]} != expected {expected_tag}"
