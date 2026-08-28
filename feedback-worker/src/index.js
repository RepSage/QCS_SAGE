const GITHUB_OWNER = 'RepSage';
const GITHUB_REPOSITORY = 'QCS_SAGE';
const GITHUB_API_VERSION = '2026-03-10';
const MAX_REQUEST_BYTES = 16_384;

export const LIMITS = Object.freeze({
  name: 120,
  title: 200,
  description: 4000,
});

const RESPONSE_HEADERS = Object.freeze({
  'Cache-Control': 'no-store',
  'Content-Type': 'application/json; charset=utf-8',
  'X-Content-Type-Options': 'nosniff',
});


export class ValidationError extends Error {}


function jsonResponse(status, value) {
  return new Response(JSON.stringify(value), {
    status,
    headers: RESPONSE_HEADERS,
  });
}


function singleLine(value) {
  return String(value ?? '').trim().replace(/\s+/gu, ' ');
}


export function normalizeFeedback(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new ValidationError('The report must be a JSON object.');
  }
  if (value.website) {
    throw new ValidationError('The report could not be accepted.');
  }

  const report = {
    name: singleLine(value.name),
    title: singleLine(value.title),
    description: String(value.description ?? '').trim(),
    qcsVersion: singleLine(value.qcs_version),
  };
  if (!report.title) {
    throw new ValidationError('Enter a title for the report.');
  }
  if (!report.description) {
    throw new ValidationError('Describe the problem or suggestion.');
  }
  for (const field of ['name', 'title', 'description']) {
    if (report[field].length > LIMITS[field]) {
      throw new ValidationError(
        `${field[0].toUpperCase()}${field.slice(1)} is too long ` +
        `(${report[field].length} characters; maximum ${LIMITS[field]}).`,
      );
    }
  }
  if (!/^v\d+\.\d+\.\d+$/u.test(report.qcsVersion)) {
    throw new ValidationError('The QCS version is missing or invalid.');
  }
  return report;
}


export function buildIssue(report) {
  const reporter = report.name || 'Not provided';
  return {
    title: `[QCS ${report.qcsVersion}] ${report.title}`,
    body: [
      '## Reporter',
      '',
      `- Name: ${reporter}`,
      `- QCS version: ${report.qcsVersion}`,
      '',
      '## Description',
      '',
      report.description,
      '',
      '---',
      'Submitted through the QCS in-app feedback form.',
    ].join('\n'),
  };
}


async function readJson(request) {
  const contentType = request.headers.get('Content-Type') || '';
  if (!contentType.toLowerCase().startsWith('application/json')) {
    throw new ValidationError('Content-Type must be application/json.');
  }
  const declaredLength = Number(request.headers.get('Content-Length') || 0);
  if (declaredLength > MAX_REQUEST_BYTES) {
    throw new ValidationError('The report is too large.');
  }
  const raw = await request.text();
  if (new TextEncoder().encode(raw).length > MAX_REQUEST_BYTES) {
    throw new ValidationError('The report is too large.');
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new ValidationError('The report contains invalid JSON.');
  }
}


export async function handleRequest(request, env, fetchImpl = fetch) {
  const url = new URL(request.url);
  if (request.method === 'GET' && url.pathname === '/health') {
    return jsonResponse(200, { ok: true, service: 'qcs-feedback' });
  }
  if (request.method !== 'POST' || url.pathname !== '/feedback') {
    return jsonResponse(404, { ok: false, error: 'Not found.' });
  }

  if (!env.FEEDBACK_RATE_LIMITER?.limit) {
    return jsonResponse(503, { ok: false, error: 'Feedback service is unavailable.' });
  }
  const clientIp = request.headers.get('CF-Connecting-IP') || 'unknown';
  const rate = await env.FEEDBACK_RATE_LIMITER.limit({ key: clientIp });
  if (!rate.success) {
    return jsonResponse(429, {
      ok: false,
      error: 'Too many reports were sent from this connection. Try again later.',
    });
  }

  let report;
  try {
    report = normalizeFeedback(await readJson(request));
  } catch (error) {
    if (error instanceof ValidationError) {
      return jsonResponse(400, { ok: false, error: error.message });
    }
    throw error;
  }
  if (!env.GITHUB_TOKEN) {
    return jsonResponse(503, { ok: false, error: 'Feedback service is unavailable.' });
  }

  const githubResponse = await fetchImpl(
    `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPOSITORY}/issues`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        'Content-Type': 'application/json',
        'User-Agent': 'QCS-SAGE-feedback-worker',
        'X-GitHub-Api-Version': GITHUB_API_VERSION,
      },
      body: JSON.stringify(buildIssue(report)),
    },
  );
  if (githubResponse.status !== 201) {
    console.error('GitHub issue creation failed with status', githubResponse.status);
    return jsonResponse(502, {
      ok: false,
      error: 'GitHub did not accept the report. Try again later.',
    });
  }
  const issue = await githubResponse.json();
  return jsonResponse(201, {
    ok: true,
    issue_number: issue.number,
    issue_url: issue.html_url,
  });
}


export default {
  fetch(request, env) {
    return handleRequest(request, env);
  },
};
