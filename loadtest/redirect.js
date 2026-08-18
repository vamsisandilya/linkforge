// k6 load test for the redirect hot path.
//
//   1. Create a link:  curl -X POST localhost:8000/api/links/ \
//                        -H "Content-Type: application/json" \
//                        -d '{"target_url":"https://example.com"}'
//   2. Grab its "code" from the response.
//   3. Run:  k6 run -e CODE=<code> loadtest/redirect.js
//
// Read p95 latency and req/s from the k6 summary — those are your resume numbers.
import http from "k6/http";
import { check } from "k6";

export const options = {
  stages: [
    { duration: "15s", target: 50 },
    { duration: "30s", target: 50 },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<50"], // tighten as you optimize
  },
};

const CODE = __ENV.CODE || "demo";
const BASE = __ENV.BASE || "http://localhost:8000";

export default function () {
  const res = http.get(`${BASE}/${CODE}`, { redirects: 0 });
  check(res, { "is 302": (r) => r.status === 302 });
}
