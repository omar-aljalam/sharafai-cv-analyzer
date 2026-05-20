# SharafAI CV Analyzer — API Documentation

**Base URL:** `http://localhost:8080` (development)  
**Version:** 1.0.0

---

## Authentication

Protected endpoints require a JWT token in the request header:

```
Authorization: Bearer <your_token>
```

You get the token from the `/api/users/login` endpoint.

---

## General

### GET `/`
Check that the API is reachable.

**Response `200`**
```json
{
  "message": "Welcome to the SharafAI CV Analyzer API!"
}
```

---

### GET `/health`
Check the health of the API and its dependencies.

**Response `200`**
```json
{
  "status": "healthy",
  "dependencies": {
    "database": "ok"
  }
}
```

**Response `503`** — database is down
```json
{
  "detail": "Database unavailable"
}
```

---

## Users & Auth

### POST `/api/users/register`
Create a new account.

**Request body**
```json
{
  "name": "Ahmed Ali",
  "email": "ahmed@example.com",
  "password": "mypassword123"
}
```

| Field | Type | Rules |
|---|---|---|
| `name` | string | min 2 chars, max 100 chars |
| `email` | string | valid email format, max 255 chars |
| `password` | string | min 8 chars |

**Response `201`**
```json
{
  "name": "string",
  "email": "user@example.com",
  "id": "d40fd1b8-151c-4a43-a9aa-0c734b911472",
  "created_at": "2026-05-16T15:50:30.106265Z"
}
```

**Response `400`** — email already registered
```json
{
  "detail": "Email already registered"
}
```

---

### POST `/api/users/login`
Login with email and password. Returns a JWT token.

> **Note:** This endpoint uses `form-data`, not JSON — this is required by the OAuth2 standard.

**Request — form-data**
| Field | Value |
|---|---|
| `username` | the user's email |
| `password` | the user's password |

**Response `200`**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response `401`** — wrong credentials
```json
{
  "detail": "Invalid email or password"
}
```
---

### GET `/api/users/me`
Get the currently logged-in user's profile.

 **Requires token**

**Response `200`**
```json
{
  "id": "uuid",
  "name": "Ahmed Ali",
  "email": "ahmed@example.com",
  "created_at": "2026-05-15T21:00:00Z"
}
```

**Response `401`** — missing or invalid token
```json
{
  "detail": "Invalid or expired token"
}
```

---

### POST `/api/users/forgot-password`
Request a password reset OTP. The OTP is sent to the user's email.

> **Note:** Always returns `202` whether the email exists or not — this is intentional for security.

**Request body**
```json
{
  "email": "ahmed@example.com"
}
```

**Response `202`**
```json
{
  "message": "If an account exists with this email, you will receive a reset code."
}
```

---

### POST `/api/users/reset-password`
Set a new password using the `otp` from the previous step.

**Request body**
```json
{
  "otp": "123456",
  "new_password": "mynewpassword123"
}
```

**Response `200`**
```json
{
  "message": "Password reset successfully. You can now log in with your new password."
}
```

**Response `400`** — invalid or expired otp
```json
{
  "detail": "Invalid or expired reset otp"
}
```

---

### PATCH `/api/users/me/password`
Change password while logged in. Requires the current password.

 **Requires token**

**Request body**
```json
{
  "current_password": "myoldpassword123",
  "new_password": "mynewpassword456"
}
```

**Response `200`**
```json
{
  "message": "Password changed successfully"
}
```

**Response `400`** — wrong current password
```json
{
  "detail": "Current password is incorrect"
}
```

---

### DELETE `/api/users/me`
Permanently delete the logged-in user's account and all associated data.  
**This action cannot be undone.**

 **Requires token**

**Response `204`** — no content, deletion successful

---

## Analysis API

All endpoints require authentication via a Bearer JWT token:
```
Authorization: Bearer <access_token>
```

---

### POST `/api/analyses/upload`

Upload a CV file. The backend extracts text from the file, sends it to the AI service, saves the result, and returns the full analysis.

**Request — `multipart/form-data`**

| Field  | Type | Required | Details                        |
|--------|------|----------|--------------------------------|
| `file` | File | ✅       | PDF, JPG, or PNG — max 10 MB  |

**Response `201`**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "overall_score": 74.5,
  "sections": [
    {
      "name": "Work Experience",
      "score": 68.0,
      "errors": [
        {
          "text": "No measurable achievements mentioned",
          "severity": "warning"
        }
      ],
      "suggestions": [
        "Use action verbs and quantify results (e.g. 'Increased sales by 20%')"
      ]
    }
  ],
  "errors": [
    {
      "text": "No measurable achievements mentioned",
      "severity": "warning"
    }
  ],
  "suggestions": [
    {
      "original": "Responsible for sales",
      "suggested": "Drove a 20% increase in regional sales over 12 months",
      "section": "Work Experience"
    }
  ],
  "created_at": "2026-05-20T10:00:00Z"
}
```

**Error responses**

| Code  | Detail                                                       |
|-------|--------------------------------------------------------------|
| `401` | Missing or invalid token                                     |
| `413` | File exceeds the 10 MB limit                                 |
| `415` | Unsupported file type (only PDF, JPG, PNG accepted)          |
| `422` | No text could be extracted from the file                     |
| `429` | User has reached their analysis limit                        |
| `502` | AI service returned an unexpected response                   |
| `504` | AI service did not respond in time (timeout)                 |

---

### GET `/api/analyses/history`

Returns the current user's past analyses sorted newest first.

**Response `200`**
```json
{
  "items": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "overall_score": 74.5,
      "created_at": "2026-05-20T10:00:00Z"
    }
  ],
  "total": 1
}
```

**Error responses**

| Code  | Detail                   |
|-------|--------------------------|
| `401` | Missing or invalid token |

---

### GET `/api/analyses/{analysis_id}`

Returns the full result of a single past analysis belonging to the current user.

**Path parameter**

| Parameter     | Type   | Details      |
|---------------|--------|--------------|
| `analysis_id` | UUID   | Analysis ID  |

**Response `200`** — same shape as the upload response above.

**Error responses**

| Code  | Detail                                        |
|-------|-----------------------------------------------|
| `401` | Missing or invalid token                      |
| `404` | Analysis not found or belongs to another user |

---

### GET `/api/analyses/{analysis_id}/export`

Downloads the corrected CV as a watermarked PDF file.

**Path parameter**

| Parameter     | Type | Details     |
|---------------|------|-------------|
| `analysis_id` | UUID | Analysis ID |

**Response `200`**

Binary PDF stream.

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="sharafai_cv_<analysis_id>.pdf"
```

**Error responses**

| Code  | Detail                                        |
|-------|-----------------------------------------------|
| `401` | Missing or invalid token                      |
| `404` | Analysis not found or belongs to another user |
| `500` | PDF generation failed                         |
