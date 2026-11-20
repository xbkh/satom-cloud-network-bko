import http from 'k6/http';
import { check } from 'k6';

const paths = ['/', '/api/health', '/static/logo.png'];

export const options = {
  scenarios: {
    demo: {
      executor: 'constant-arrival-rate',
      rate: 5,
      timeUnit: '1s',
      duration: '20s',
      preAllocatedVUs: 3,
      maxVUs: 5,
    },
  },
  summaryTrendStats: ['p(95)', 'p(99)', 'avg', 'max'],
  thresholds: {
    'http_req_failed': ['rate<0.005'],
    'http_req_duration': ['p(95)<500', 'p(99)<1000'],
    'checks': ['rate==1'],
    'dropped_iterations': ['count==0'],
  },
};

export default function () {
  const path = paths[__ITER % paths.length];
  const res = http.get(`${__ENV.PORTAL_URL}${path}`, { redirects: 0, timeout: '3s' });
  check(res, {
    'réponse HTTP 200': (r) => r.status === 200,
  });
}

export function handleSummary(data) {
  const durations = data.metrics.http_req_duration.values;
  return {
    stdout: JSON.stringify({
      iterations: data.metrics.iterations.values.count,
      requests: data.metrics.http_reqs.values.count,
      p95_ms: durations['p(95)'],
      p99_ms: durations['p(99)'],
      error_rate: data.metrics.http_req_failed.values.rate,
      checks: data.metrics.checks.values.rate,
      vus_max: data.metrics.vus_max.values.max,
    }) + '\n',
  };
}
