// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

contract A {
    int a = 0;
    uint public M;
    string[10] text_array;

    function method1() public {
        string memory text = "sdsd";

        for (uint i; i < 10; i++) {
            a += 1;
            text = string.concat(text, text);
        }

        for (uint i = 0; i < 5; i++) {
            text_array[i] = text;
        }
    }

    function cancel_in_iterative_tx(uint N, address resaver) public payable {
        for (uint i = 1; i <= N; i++) {
            if (i == N / 2) {
                method1();
            }
        }
    }

    function loopWithMethodCall(uint N, address payable recipient) public payable {
        for (uint i = 1; i <= N; i++) {
            if (i == N / 2) {
                // Отправка всего полученного value получателю
                (bool success,) = recipient.call{value: msg.value}("");
                require(success, "Transfer failed");

                method1();
            }
        }
    }

    function loopAndReturnNumber(uint N) public pure returns (uint) {
        uint result;

        for (uint i = 0; i < N; i++) {
            result = i;
        }
        return result;
    }

    function riskyDivision(uint x, uint y) public pure returns (uint) {
        return x / y;
    }

    function runLoopWithZeroDivision() public {
        for (uint i = 0; i < 300; i++) {
            if (i == 250) {
                uint result = riskyDivision(i, 0);
                M += result;
            } else {
                M += 1;
            }
        }
    }
}