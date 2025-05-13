// SPDX-License-Identifier: GPL-3.0
pragma solidity ^0.8.12;

contract RevisionChanger {
    uint256 public number_inner_contract_scope = 1;
    bytes32[64] public b;
    uint256 public number_outer_contract_scope = 2;

    function powNumberInnerAndRollback(uint256 n) public {
        require(n > 0, "Exponent should be > 0");

        uint original = number_inner_contract_scope;
        uint computedValue = 1;

        for (uint i = 0; i < n; i++) {
            computedValue *= original;
            number_inner_contract_scope = computedValue;
        }
        number_inner_contract_scope = original;
    }

    function powNumberOuterAndRollback(uint256 n) public {
        require(n > 0, "Exponent should be > 0");

        uint original = number_outer_contract_scope;
        uint computedValue = 1;

        for (uint i = 0; i < n; i++) {
            computedValue *= original;
            number_outer_contract_scope = computedValue;
        }
    }

    function changeGlobalVarB(uint256 n) public {
        for (uint i = 0; i < 64; i++) {
            b[i] = bytes32(abi.encodePacked(n));
        }
    }
}

contract RevisionChangerCaller {
    RevisionChanger rch;
    constructor(address revisionChangerAddress) {
        rch = RevisionChanger(revisionChangerAddress);
    }

    function callRevisionChangerMethods(uint256 n) public {
        rch.powNumberInnerAndRollback(n);
        rch.changeGlobalVarB(n);
        rch.powNumberOuterAndRollback(n);
    }
}
