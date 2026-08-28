import assert from 'node:assert/strict';
import test from 'node:test';

import {
  ValidationError,
  buildIssue,
  handleRequest,
  normalizeFeedback,
} from '../src/index.js';


const VALID_REPORT = Object.freeze({
  name: ' Field operator ',
  title: ' Unexpected flag ',
  description: 'The highlighted point does not match the table.',
  qcs_version: 'v13.3.0',
  website: '',
});


function environment(success = true) {
  return {
    GITHUB_TOKEN: 'test-token-never-sent-to-client',
    FEEDBACK_RATE_LIMITER: {
      limit: async () => ({ success }),
    },
  };
}


function feedbackRequest(value = VALID_REPORT, headers = {}) {
  return new Request('https://feedback.example/feedback', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'CF-Connecting-IP': '192.0.2.10',
      ...headers,
    },
    body: JSON.stringify(value),
  });
}


test('normalizes the report and preserves description lines', () => {
  const report = normalizeFeedback({
    ...VALID_REPORT,
    name: '  Field   operator ',
    description: ' Step 1\nStep 2 ',
  });
  assert.deepEqual(report, {
    name: 'Field operator',
    title: 'Unexpected flag',
    description: 'Step 1\nStep 2',
    qcsVersion: 'v13.3.0',
  });
});


test('requires title, description and a semantic QCS version', () => {
  assert.throws(
    () => normalizeFeedback({ ...VALID_REPORT, title: ' ' }),
    ValidationError,
  );
  assert.throws(
    () => normalizeFeedback({ ...VALID_REPORT, description: '' }),
    ValidationError,
  );
  assert.throws(
    () => normalizeFeedback({ ...VALID_REPORT, qcs_version: '13.3' }),
    ValidationError,
  );
});


test('rejects oversized and honeypot submissions', () => {
  assert.throws(
    () => normalizeFeedback({ ...VALID_REPORT, title: 'x'.repeat(201) }),
    /maximum 200/u,
  );
  assert.throws(
    () => normalizeFeedback({ ...VALID_REPORT, website: 'spam.example' }),
    ValidationError,
  );
});


test('formats a public issue without an operator name', () => {
  const issue = buildIssue(normalizeFeedback({ ...VALID_REPORT, name: '' }));
  assert.equal(issue.title, '[QCS v13.3.0] Unexpected flag');
  assert.match(issue.body, /Name: Not provided/u);
  assert.match(issue.body, /QCS version: v13\.3\.0/u);
  assert.match(issue.body, /## Description\n\nThe highlighted point/u);
});


test('health check performs no rate-limit or GitHub request', async () => {
  const response = await handleRequest(
    new Request('https://feedback.example/health'),
    {},
    () => assert.fail('GitHub must not be called'),
  );
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { ok: true, service: 'qcs-feedback' });
});


test('publishes exactly one issue and returns only its public identity', async () => {
  const calls = [];
  const response = await handleRequest(
    feedbackRequest(),
    environment(),
    async (url, options) => {
      calls.push({ url, options });
      return Response.json(
        { number: 123, html_url: 'https://github.com/RepSage/QCS_SAGE/issues/123' },
        { status: 201 },
      );
    },
  );
  assert.equal(response.status, 201);
  assert.deepEqual(await response.json(), {
    ok: true,
    issue_number: 123,
    issue_url: 'https://github.com/RepSage/QCS_SAGE/issues/123',
  });
  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].url,
    'https://api.github.com/repos/RepSage/QCS_SAGE/issues',
  );
  assert.equal(calls[0].options.headers.Authorization, 'Bearer test-token-never-sent-to-client');
  assert.equal(calls[0].options.headers['X-GitHub-Api-Version'], '2026-03-10');
  assert.equal(JSON.parse(calls[0].options.body).title, '[QCS v13.3.0] Unexpected flag');
});


test('rate limiting blocks the request before GitHub', async () => {
  const response = await handleRequest(
    feedbackRequest(),
    environment(false),
    () => assert.fail('GitHub must not be called'),
  );
  assert.equal(response.status, 429);
});


test('GitHub errors are sanitized and never expose the token', async () => {
  const originalError = console.error;
  console.error = () => {};
  let response;
  try {
    response = await handleRequest(
      feedbackRequest(),
      environment(),
      async () => new Response('upstream secret details', { status: 403 }),
    );
  } finally {
    console.error = originalError;
  }
  assert.equal(response.status, 502);
  const text = await response.text();
  assert.doesNotMatch(text, /test-token|upstream secret/u);
});


test('rejects non-JSON and overlarge declared bodies', async () => {
  const wrongType = new Request('https://feedback.example/feedback', {
    method: 'POST',
    body: 'hello',
  });
  assert.equal((await handleRequest(wrongType, environment())).status, 400);

  const tooLarge = feedbackRequest(VALID_REPORT, { 'Content-Length': '16385' });
  assert.equal((await handleRequest(tooLarge, environment())).status, 400);
});
