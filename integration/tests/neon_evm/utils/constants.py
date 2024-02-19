import os
from solana.publickey import PublicKey


SYSTEM_ADDRESS = "11111111111111111111111111111111"
TOKEN_KEG_ADDRESS = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SYSVAR_CLOCK_ADDRESS = "SysvarC1ock11111111111111111111111111111111"
SYS_INSTRUCT_ADDRESS = "Sysvar1nstructions1111111111111111111111111"
KECCAKPROG_ADDRESS = "KeccakSecp256k11111111111111111111111111111"
RENT_ID_ADDRESS = "SysvarRent111111111111111111111111111111111"
INCINERATOR_ADDRESS = "1nc1nerator11111111111111111111111111111111"
TREASURY_POOL_SEED = os.environ.get("NEON_TREASURY_POOL_SEED", "treasury_pool")
TREASURY_POOL_COUNT = os.environ.get("NEON_TREASURY_POOL_COUNT", 128)
COMPUTE_BUDGET_ID: PublicKey = PublicKey("ComputeBudget111111111111111111111111111111")

ACCOUNT_SEED_VERSION = b'\3'

TAG_EMPTY = 0
TAG_FINALIZED_STATE = 32
TAG_HOLDER = 52

SOLANA_URL = os.environ.get("SOLANA_URL", "http://solana:8899")
NEON_CORE_API_URL = os.environ.get("NEON_CORE_API_URL", "http://neon_api:8085/api")
EVM_LOADER = os.environ.get("EVM_LOADER", "53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io")
NEON_TOKEN_MINT_ID: PublicKey = PublicKey(os.environ.get("NEON_TOKEN_MINT", "HPsV9Deocecw3GeZv1FkAPNCBRfuVyfw9MMwjwRe1xaU"))
CHAIN_ID = int(os.environ.get("NEON_CHAIN_ID", 111))
