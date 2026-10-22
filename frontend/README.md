# PR Mentor frontend

React + TypeScript application built with Vite.

## Local development

```bash
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `.env.local` to the FastAPI origin (defaults to `http://127.0.0.1:8000`). Start the backend as described in [`../backend/README.md`](../backend/README.md).

The Discover page asks whether to use demo or live analysis. Demo findings are explicitly sample content from the backend and do not describe the submitted pull request. History, saved links, diffs, and learning data come from API responses. API errors and unavailable backend stages remain visible; this frontend does not invent fallback review results.

The current UI does not call OTP authentication endpoints. Backend OTP endpoints return a not-configured response until secure delivery and challenge storage are implemented.
