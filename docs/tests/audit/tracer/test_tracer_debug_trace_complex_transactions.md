# Overview

Tests for debug trace iterative

| Test case                                                                        | Description                                                                          | XFailed |
|----------------------------------------------------------------------------------|--------------------------------------------------------------------------------------|---------|
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_struct_opcode_tracer | Positive test for tracing an iterative transaction using structured opcode tracer.   |         |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_simple               | Positive test for tracing a simple iterative transaction.                            |         |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_failed_status        | Positive test for tracing a transaction that results in a failed status.             |         |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_with_erc20_for_spl   | Positive test for tracing an iterative transaction involving ERC-20 tokens for SPL.  |         |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_eip_1559             | Positive test for tracing an iterative transaction that uses EIP-1559 fee mechanism. |         |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_sol_chain            | Positive test for tracing an iterative transaction on the Solana-compatible chain.   |         |
| TestDebugTraceIterativeTransaction::test_trace_iterative_tx_block_timestamp      | Positive test for verifying block timestamp in an iterative transaction trace.       |         |
| TestDebugTraceIterativeTransaction::test_trace_scheduled_tx                      | Positive test for tracing a scheduled transaction.                                   |         |
| TestDebugTraceIterativeTransaction::test_trace_success_multiple_scheduled_trx    | Positive test for tracing multiple successfully executed scheduled transactions.     |         |
| TestDebugTraceIterativeTransaction::test_trace_failed_one_scheduled_tx           | Positive test for tracing a scheduled transaction that failed.                       |         |
| TestDebugTraceIterativeTransaction::test_trace_failed_multiply_scheduled_tx      | Positive test for tracing multiple scheduled transactions with failures.             |         |
