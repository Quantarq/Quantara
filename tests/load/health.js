import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '15s',
  thresholds: {
    http_req_duration: ['p(95)<200'], // P95 latency must be under 200ms
    http_req_failed: ['rate<0.01'],   // Error rate must be under 1%
  },
};

export default function () {
  const url = __ENV.API_URL || 'http://localhost:8000/api/v1';
  const res = http.get(`${url}/status`);
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}