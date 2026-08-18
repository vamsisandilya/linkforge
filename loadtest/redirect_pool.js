// Realistic variant of redirect.js: draws a random code from a pool of
// "hot" links per iteration instead of hammering a single code, so the
// cache-aside layer actually gets exercised the way real traffic would.
//
//   k6 run loadtest/redirect_pool.js
//
// Requires loadtest/hot_codes.json (a JSON array of existing link codes).
import http from "k6/http";
import { check } from "k6";
import { SharedArray } from "k6/data";

const codes = new SharedArray("codes", function () {
  return JSON.parse(open("./hot_codes.json"));
});

export const options = {
  stages: [
    { duration: "15s", target: 50 },
    { duration: "30s", target: 50 },
    { duration: "15s", target: 0 },
  ],
};

const BASE = __ENV.BASE || "http://localhost:8000";

export default function () {
  const code = codes[Math.floor(Math.random() * codes.length)];
  const res = http.get(`${BASE}/${code}`, { redirects: 0 });
  check(res, { "is 302": (r) => r.status === 302 });
}
