import { usersNumber } from "../tests/utils/consts.js";

export const sendNeonOptions = {
    scenarios: {
        sendNeon: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: usersNumber },
                { duration: '1200s', target: usersNumber },
            ],
            gracefulRampDown: '30s',
        },
    },
    noConnectionReuse: true,
};