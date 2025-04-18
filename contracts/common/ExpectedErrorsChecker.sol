
contract A {
    int a = 0;
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
}

contract Divider {
    function riskyDivision(uint a, uint b) external pure returns (uint) {
        return a / b;
    }
}

contract Fail {
    Divider public myDivider;
    uint public M;

    constructor(address _address) {
        myDivider = Divider(_address);
    }

    function runLoopWithZeroDivision() public {
        for (uint i = 0; i < 300; i++) {
            if (i == 250) {
                uint result = myDivider.riskyDivision(i, 0);
                M += result;
            } else {
                M += 1;
            }
        }
    }
}