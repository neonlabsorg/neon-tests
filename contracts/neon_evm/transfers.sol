pragma solidity ^0.7.6;

contract transfers {
    constructor() payable {}

    function transferNeon(uint256 amount, address[] memory recipients) public payable {
        require(address(this).balance >= amount * recipients.length, "contract balance less then needed");
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success,) = recipients[i].call{value: amount}("");
            require(success, "Payment failed.");
        }
    }

    function transferTokensAndRaiseError(uint256 amount, address[] memory recipients) public payable {
        require(address(this).balance >= amount * recipients.length, "contract balance less then needed");
        for (uint256 i = 0; i < recipients.length; i++) {
            (bool success,) = recipients[i].call{value: amount}("");
        }
        uint a;
        for (uint256 i = 0; i < 800; i++) { // some actions to make transaction iterative
            a = a + i;
        }
        require(false, "Error raised");
    }

    function donateTenPercent() public payable {
        if (address(this).balance >= 1000) {
            payable(msg.sender).transfer(address(this).balance / 10);
        }
    }
    function donate1000() public payable {
        payable(msg.sender).transfer(1000);
    }
}