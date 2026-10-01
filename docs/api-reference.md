# API reference — ocr-platform (R1 thin slice)

OpenAPI 3.0 outline for the R1 async extraction API. Design SoT until `service/api.py` spec is authored under `docs/files/`.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Base URL

```
https://{host}/v1
```

All endpoints are versioned under `/v1`. Breaking changes require `/v2`.

---

## 2. Authentication

| Scheme | Header | Description |
|---|---|---|
| Bearer | `Authorization: Bearer <token>` | Tenant API key |

**Token lifecycle:**
- Tokens are issued per tenant
- Expiry: 24 hours (configurable)
- Refresh: not supported in R1; re-issue required
- Scopes: `extract`, `read`, `review`

---

## 3. Endpoints

### 3.1 POST /extractions

Submit a PDF for extraction.

**Request:**

```json
{
  "fixture_id": "ward42-1rn982-095",
  "idempotency_key": "client-generated-uuid",
  "priority": "normal"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `fixture_id` | string | yes | Fixture identifier from `fixture_manifest.json` |
| `idempotency_key` | string | yes | Client-generated UUID for retry safety |
| `priority` | enum: `low` \| `normal` \| `high` | no | Queue priority; default `normal` |

**Response (202 Accepted):**

```json
{
  "job_id": "job-abc123",
  "run_id": "sha256:config-hash",
  "status": "queued",
  "estimated_start": "2026-09-27T10:05:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Unique job identifier |
| `run_id` | string | `(document_content_hash, configuration_fingerprint)` |
| `status` | enum: `queued` \| `running` \| `succeeded` \| `failed` | Current job status |
| `estimated_start` | string | ISO-8601 estimated start time |

**Errors:**

| Status | Code | Message | Retryable |
|---|---|---|---|
| 400 | `INVALID_FIXTURE` | Fixture not found or not classified | No |
| 401 | `UNAUTHORIZED` | Invalid or missing token | No |
| 409 | `DUPLICATE_KEY` | Idempotency key already used | No |
| 429 | `RATE_LIMITED` | Too many requests | Yes (with backoff) |

---

### 3.2 GET /extractions/{job_id}

Get job status.

**Request:**

```
GET /v1/extractions/job-abc123
Authorization: Bearer <token>
```

**Response (200 OK):**

```json
{
  "job_id": "job-abc123",
  "run_id": "sha256:config-hash",
  "status": "running",
  "progress": {
    "pages_rendered": 1,
    "pages_total": 2,
    "fields_evaluated": 150,
    "fields_total": 344
  },
  "created_at": "2026-09-27T10:00:00Z",
  "updated_at": "2026-09-27T10:02:30Z"
}
```

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Unique job identifier |
| `run_id` | string | Run identity tuple |
| `status` | enum: `queued` \| `running` \| `succeeded` \| `failed` | Current job status |
| `progress` | object | Progress indicators (optional, best-effort) |
| `created_at` | string | ISO-8601 creation time |
| `updated_at` | string | ISO-8601 last update time |

**Errors:**

| Status | Code | Message | Retryable |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | Invalid or missing token | No |
| 404 | `JOB_NOT_FOUND` | Job does not exist | No |

---

### 3.3 GET /extractions/{job_id}/result

Get extraction result (canonical JSON).

**Request:**

```
GET /v1/extractions/job-abc123/result
Authorization: Bearer <token>
```

**Response (200 OK):**

```json
{
  "job_id": "job-abc123",
  "run_id": "sha256:config-hash",
  "status": "succeeded",
  "result": {
    "document": {
      "municipality": "...",
      "zone": "...",
      "ward_no": "..."
    },
    "household": {
      "head_name": "...",
      "mobile": "...",
      "members": [
        {
          "name": "...",
          "gender": "...",
          "age": 35
        }
      ]
    },
    "education": [
      {
        "highest_qualification": "...",
        "member_key": "member-0"
      }
    ]
  },
  "provenance": {
    "complete": true,
    "evidence_count": 342
  },
  "configuration_fingerprint": "sha256:...",
  "completed_at": "2026-09-27T10:05:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Unique job identifier |
| `run_id` | string | Run identity tuple |
| `status` | enum: `succeeded` \| `failed` | Final job status |
| `result` | object | Canonical JSON (Household/Member/EducationRecord) |
| `provenance` | object | Provenance summary |
| `configuration_fingerprint` | string | Config fingerprint used |
| `completed_at` | string | ISO-8601 completion time |

**Errors:**

| Status | Code | Message | Retryable |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | Invalid or missing token | No |
| 404 | `JOB_NOT_FOUND` | Job does not exist | No |
| 409 | `JOB_NOT_COMPLETE` | Job still running | Yes (poll) |

---

### 3.4 GET /extractions/{job_id}/review

Get review candidates.

**Request:**

```
GET /v1/extractions/job-abc123/review
Authorization: Bearer <token>
```

**Response (200 OK):**

```json
{
  "job_id": "job-abc123",
  "run_id": "sha256:config-hash",
  "review_candidates": [
    {
      "field_id": "member.name",
      "row_key": "row-0",
      "crop_url": "https://.../crops/member-name-row0.png",
      "reason_codes": ["HANDWRITING_SUSPECTED"],
      "primary_reason": "HANDWRITING_SUSPECTED",
      "ocr_value": "...",
      "confidence": 0.85
    }
  ],
  "total_review": 12,
  "total_accepted": 332
}
```

| Field | Type | Description |
|---|---|---|
| `job_id` | string | Unique job identifier |
| `run_id` | string | Run identity tuple |
| `review_candidates` | array | List of fields needing review |
| `total_review` | integer | Total review count |
| `total_accepted` | integer | Total accepted count |

**Errors:**

| Status | Code | Message | Retryable |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | Invalid or missing token | No |
| 404 | `JOB_NOT_FOUND` | Job does not exist | No |
| 409 | `JOB_NOT_COMPLETE` | Job still running | Yes (poll) |

---

## 4. Error response envelope

All errors use this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "retryable": false,
    "run_id": "sha256:..."
  }
}
```

| Field | Type | Description |
|---|---|---|
| `code` | string | Machine-readable error code |
| `message` | string | Human-readable description |
| `retryable` | boolean | Whether the request can be retried |
| `run_id` | string? | Run identity if available |

---

## 5. Idempotency

- Client sends `idempotency_key` (UUID) with each `POST /extractions`
- If the same key is sent twice, the second request returns the original `job_id`
- Idempotency keys are scoped per tenant
- Keys expire after 24 hours

---

## 6. Rate limiting

| Tier | Requests/minute | Burst |
|---|---|---|
| Default | 60 | 100 |
| Premium | 600 | 1000 |

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1727430000
```

---

## 7. Backwards compatibility

| Change type | Example | Version bump |
|---|---|---|
| Adding optional field | New field in response | None (additive) |
| Deprecating field | Mark field deprecated | None (with notice) |
| Removing field | Delete field from response | `/v2` |
| Changing type | `string` → `integer` | `/v2` |
| Changing semantics | `accepted` → `auto_accepted` | `/v2` |

---

## 8. Related documents

- Market roadmap: `docs/market-roadmap.md §R1`
- Sequences: `docs/sequences.md §6`
- Reason codes: `docs/reason-codes.md`
- Observability: `docs/observability.md`

---

## 9. Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial API reference outline for R1 thin slice |
