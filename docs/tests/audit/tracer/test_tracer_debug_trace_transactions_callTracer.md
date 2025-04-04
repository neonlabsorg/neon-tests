# Overview

Tests for debug trace transactions callTracer

| Test case                                                                                                     | Description                                                                     | XFailed |
|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|---------|
| TestDebugTraceTransactionCallTracer::fill_expected_response                                                   | Positive test for filling the expected response in call tracer.                 |         |
| TestDebugTraceTransactionCallTracer::assert_response_contains_expected                                        | Positive test to assert that response contains expected values in call tracer.  |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_type_create                                              | Positive test for call tracer with type 'create'.                               |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_type_create2                                             | Positive test for call tracer with type 'create2'.                              |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_type_call                                                | Positive test for call tracer with type 'call'.                                 |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_withLog_check                                            | Positive test to check logs generated during call trace.                        |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_onlyTopCall_check                                        | Positive test to verify call tracer with only top-level calls.                  |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_static_call             | Positive test for static call from one contract to another.                     |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_static_call_with_events | Positive test for static call with events between contracts.                    |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_call_with_events        | Positive test for regular call with events between contracts.                   |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_call                    | Positive test for contract-to-contract call using 'call' type.                  |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_delegate_call           | Positive test for delegate call between contracts.                              |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_contract_type_callcode                | Positive test for call using 'callcode' between contracts.                      |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_with_zero_division                         | Positive test for contract call that causes a zero division error.              |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_revert_with_assert     | Positive test for call that reverts with 'assert'.                              |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_trivial_revert         | Positive test for call that triggers a trivial revert.                          |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_revert                 | Positive test for contract call that reverts.                                   |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_from_other_contract_revert_with_require    | Positive test for call that reverts with 'require'.                             |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_to_precompiled_contract                             | Positive test for calling a precompiled contract.                               |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_without_tracerConfig                                     | Positive test for call tracer behavior without explicit tracer config.          |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_call_contract_with_event_from_other_one_with_two_events  | Positive test for contract call that triggers two events from another contract. |         |
| TestDebugTraceTransactionCallTracer::test_callTracer_new_contract_and_event_from_constructor                  | Positive test for new contract creation and event emission from constructor.    |         |
