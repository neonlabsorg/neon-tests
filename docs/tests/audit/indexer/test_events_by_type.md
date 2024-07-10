# Overview

Tests for neon logs events separated by type

| Test case                                              | Description                           | XFailed |
|--------------------------------------------------------|---------------------------------------|---------|
| TestNeonEventType::test_event_log                      | Check Log event                       |         |
| TestNeonEventType::test_event_enter_call               | Check EnterCall event                 |         |
| TestNeonEventType::test_event_enter_call_code          | Check EnterCallCode event             |         |
| TestNeonEventType::test_event_enter_static_call        | Check EnterStaticCall event           |         |
| TestNeonEventType::test_event_enter_delegate_call      | Check EnterDelegateCall event         |         |
| TestNeonEventType::test_event_enter_create             | Check EnterCreate event               |         |
| TestNeonEventType::test_event_enter_create_2           | Check EnterCreate2 event              |         | 
| TestNeonEventType::test_event_exit_stop                | Check ExitStop event                  |         | 
| TestNeonEventType::test_event_exit_return              | Check ExitReturn event                |         | 
| TestNeonEventType::test_event_exit_self_destruct       | Check SELFDESTRUCT(ExitSendAll) event |         | 
| TestNeonEventType::test_event_exit_revert_predefined   | Check ExitRevert event                |         | 
| TestNeonEventType::test_event_exit_revert_trivial      | Check ExitRevert event                |         | 
| TestNeonEventType::test_event_exit_revert_custom_error | Check ExitRevert event                |         | 
| TestNeonEventType::test_event_exit_send_all            | Check ExitSendAll event               |         | 
| TestNeonEventType::test_event_return                   | Check Return event                    |         | 
| TestNeonEventType::test_event_cancel                   | Check Cancel event                    |         | 