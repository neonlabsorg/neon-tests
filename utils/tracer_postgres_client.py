import os
import signal
from typing import Sequence

from sqlalchemy import Engine, create_engine, text, Row
from sqlalchemy.orm import sessionmaker


class IndexerPostgresClient:
    def __init__(self):
        self.engine: Engine = self.__create_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        signal.signal(signal.SIGTERM, self.__handle_exit)
        signal.signal(signal.SIGINT, self.__handle_exit)

    @staticmethod
    def __create_engine() -> Engine:
        db_host = os.environ["INDEXER_POSTGRES_DB_HOST"]
        db_port = os.getenv("INDEXER_POSTGRES_DB_PORT", default=5432)
        db_name = os.environ["INDEXER_POSTGRES_DB_NAME"]
        db_user = os.environ["INDEXER_POSTGRES_DB_USER"]
        db_password = os.environ["INDEXER_POSTGRES_DB_PASSWORD"]
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(db_url)
        return engine

    def __handle_exit(self, signum, frame):  # noqa
        self.Session.close_all()

    def get_sum_gas_used_by_solana_signatures(self, signatures: list[str]) -> Sequence[Row]:
        max_sig_per_query = 50000
        query = f"""
            SELECT sol_sig, sum_gas_used 
            FROM public.neon_transactions
            WHERE sol_sig IN :signature_batch
        """
        results = []

        for i in range(0, len(signatures), max_sig_per_query):
            signature_batch = tuple(signatures[i: i + max_sig_per_query])
            result = self.session.execute(text(query), {'signature_batch': signature_batch}).fetchall()
            results.extend(result)

        return results

    def get_last_sol_sig(self) -> str:
        query = """
            SELECT sol_sig FROM public.neon_transactions
            ORDER BY public.neon_transactions.block_slot DESC
            LIMIT 1
        """
        result = self.session.execute(text(query)).fetchall()
        sol_sig = result[0].sol_sig

        return sol_sig
