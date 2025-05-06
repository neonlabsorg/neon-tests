// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

//Tree of execution:

    //Func1.execute()
    //├── Func2.execute()
    //└── Func3.execute()
    //    ├── Func4.execute()
    //    ├── Func5.execute()
    //    │   └── Func7.execute()
    //    └── Func6.execute()

contract ChainExecution {
    Func2 private func2;
    Func3 private func3;

    constructor(address _func2, address _func3) {
        func2 = Func2(_func2);
        func3 = Func3(_func3);
    }

    function start_execution() external view returns (uint256) {
        uint256 result1 = func2.execute();
        uint256 result2 = func3.execute();
        uint256 sum = result1 + result2;
        return sum;
    }
}

contract Func2 {

    function execute() external pure returns (uint256) {
        return 2;
    }
}

contract Func3 {
    Func4 private func4;
    Func5 private func5;
    Func6 private func6;

    constructor(address _func4, address _func5, address _func6) {
        func4 = Func4(_func4);
        func5 = Func5(_func5);
        func6 = Func6(_func6);
    }

    function execute() external view returns (uint256) {
        uint256 result1 = func4.execute();
        uint256 result2 = func5.execute();
        uint256 result3 = func6.execute();
        uint256 sum = result1 + result2 + result3;
        return sum;
    }
}

contract Func4 {

    function execute() external pure returns (uint256) {
        return 4;
    }
}

contract Func5 {
    Func7 private func7;

    constructor(address _func7) {
        func7 = Func7(_func7);
    }

    function execute() external view returns (uint256) {
        uint256 result1 = func7.execute();
        return result1 + 5;
    }
}

contract Func6 {

    function execute() external pure returns (uint256) {
        return 6;
    }
}

contract Func7 {

    function execute() external pure returns (uint256) {
        return 7;
    }
}