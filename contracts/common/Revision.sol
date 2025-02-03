// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.12;

contract RevisionChanger {

    uint256 public number_inner_contract_scope = 1;
    bytes32[64] public b;
    uint256 public number_outer_contract_scope = 2;

    function powNumberInnerAndRollback(uint256 n) public {
        require(n > 0, "Exponent should be > 0");

        uint base = number_inner_contract_scope;
        uint number_start = 1;

        for (uint i = 0; i < n; i++) {
            number_start *= base;
        }

        number_inner_contract_scope = base;
    }

    function powNumberOuterAndRollback(uint256 n) public {
        require(n > 0, "Exponent should be > 0");

        uint base = number_outer_contract_scope;
        uint number_start = 1;

        for (uint i = 0; i < n; i++) {
            number_start *= base;
        }

        number_outer_contract_scope = base;
    }
}

