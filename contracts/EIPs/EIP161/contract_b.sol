pragma solidity ^0.8.0;

contract ContractB {
    event ContractBDeployed(address indexed creator, address indexed contractAddress);

    constructor() {
        emit ContractBDeployed(msg.sender, address(this));
    }

    function getOne() public pure returns (uint256) {
        return 1;
    }
}
