import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '15s',
  thresholds: {
    http_req_duration: ['p(95)<200'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const url = __ENV.API_URL || 'http://localhost:8000/api/v1';
  const res = http.get(`${url}/leaderboard`);
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}