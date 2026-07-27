import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 15,
  duration: '20s',
  thresholds: {
    http_req_duration: ['p(95)<250'], // Dashboard might scale slightly higher, budget at 250ms
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const url = __ENV.API_URL || 'http://localhost:8000/api/v1';
  const res = http.get(`${url}/dashboard`);
  
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}