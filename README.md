# Stage 1

## Objective
Design REST APIs, contracts, JSON payloads, and a real-time mechanism for a campus notification platform that serves students with placement, result, and event updates.

## Core actions the platform should support
1. Create a notification for one student or a target segment.
2. List notifications for a student with pagination and unread filters.
3. Fetch unread counts.
4. Mark a notification as read/unread.
5. Mark all notifications as read.
6. Deliver real-time updates.
7. Retry asynchronous delivery for email or in-app fan-out failures.

## API design

### Common headers
```http
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
Idempotency-Key: <uuid>   # required for create / bulk notify operations
X-Request-ID: <uuid>      # recommended for tracing
```

### 1) Create a notification
**POST** `/api/v1/notifications`

Request:
```json
{
  "studentId": 1042,
  "type": "Placement",
  "title": "Interview shortlist",
  "message": "You have been shortlisted for the final interview.",
  "channels": ["in_app", "email"],
  "metadata": {
    "company": "CSX Corporation",
    "ctaUrl": "/placements/csx"
  }
}
```

Response `201 Created`:
```json
{
  "notification": {
    "id": "f3d8e6d5-0c6a-45da-b2f6-5fd26063a0bb",
    "studentId": 1042,
    "type": "Placement",
    "title": "Interview shortlist",
    "message": "You have been shortlisted for the final interview.",
    "channels": ["in_app", "email"],
    "isRead": false,
    "createdAt": "2026-05-16T10:00:00Z",
    "metadata": {
      "company": "CSX Corporation",
      "ctaUrl": "/placements/csx"
    }
  }
}
```

### 2) List notifications for a student
**GET** `/api/v1/students/{studentId}/notifications?cursor=<opaque>&limit=20&unreadOnly=true`

Response `200 OK`:
```json
{
  "items": [
    {
      "id": "f3d8e6d5-0c6a-45da-b2f6-5fd26063a0bb",
      "type": "Placement",
      "title": "Interview shortlist",
      "message": "You have been shortlisted for the final interview.",
      "isRead": false,
      "createdAt": "2026-05-16T10:00:00Z"
    }
  ],
  "pageInfo": {
    "nextCursor": "eyJjcmVhdGVkQXQiOiIyMDI2LTA1LTE2VDEwOjAwOjAwWiIsImlkIjoiZjNkOGU2ZDUifQ==",
    "limit": 20,
    "hasMore": true
  }
}
```

### 3) Get unread count
**GET** `/api/v1/students/{studentId}/notifications/unread-count`

Response `200 OK`:
```json
{
  "studentId": 1042,
  "unreadCount": 17
}
```

### 4) Mark one notification read/unread
**PATCH** `/api/v1/students/{studentId}/notifications/{notificationId}`

Request:
```json
{
  "isRead": true
}
```

Response `200 OK`:
```json
{
  "notification": {
    "id": "f3d8e6d5-0c6a-45da-b2f6-5fd26063a0bb",
    "studentId": 1042,
    "isRead": true,
    "updatedAt": "2026-05-16T10:01:00Z"
  }
}
```

### 5) Mark all notifications read
**POST** `/api/v1/students/{studentId}/notifications/mark-all-read`

Response `200 OK`:
```json
{
  "studentId": 1042,
  "updated": 17
}
```

### 6) Bulk notify all / notify a segment
**POST** `/api/v1/notifications/bulk`

Request:
```json
{
  "target": {
    "mode": "segment",
    "segment": "all_students"
  },
  "type": "Placement",
  "title": "New hiring drive",
  "message": "A new company has opened applications.",
  "channels": ["in_app", "email"],
  "metadata": {
    "company": "AMD"
  }
}
```

Response `202 Accepted`:
```json
{
  "jobId": "bb4f4035-3874-4600-94a6-7bcc4c4d16d8",
  "status": "queued"
}
```

### 7) Job status for bulk notify
**GET** `/api/v1/notification-jobs/{jobId}`

Response `200 OK`:
```json
{
  "jobId": "bb4f4035-3874-4600-94a6-7bcc4c4d16d8",
  "status": "processing",
  "submitted": 50000,
  "persisted": 50000,
  "emailSent": 48790,
  "emailFailed": 1210,
  "inAppDelivered": 50000,
  "retryScheduled": 1210
}
```

## Error shape
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "type must be one of Placement, Result, Event",
    "requestId": "a13b63e8-9f1e-4d42-a4dd-7a5926ab8ce8"
  }
}
```

## Real-time notification mechanism
Use **WebSockets** for signed-in clients plus a **message broker** between notification producers and WebSocket gateway workers.

### Flow
1. Backend persists notification record.
2. Backend writes an outbox event in the same DB transaction.
3. Outbox processor publishes event to broker (Kafka/RabbitMQ).
4. Realtime gateway consumes event and pushes it to connected student channels.
5. If user is offline, in-app notification remains queryable through list APIs.

### Why WebSockets
- Lower latency than polling.
- Efficient server-to-client push.
- Supports unread badge updates and live feed refresh.

### Fallback
Use short polling every 30–60 seconds only when WebSocket connection is unavailable.

---

# Stage 2

## Recommended persistent storage
Use **PostgreSQL** as the source of truth, with **Redis** for ephemeral caching and unread counters.

### Why PostgreSQL
- Strong consistency for read/unread state.
- Mature indexing, partitioning, and query planning.
- Great fit for transactional notification records and delivery state.
- Easy support for outbox pattern and auditability.

## Logical schema
```sql
CREATE TYPE notification_type AS ENUM ('Event', 'Result', 'Placement');
CREATE TYPE delivery_channel AS ENUM ('in_app', 'email');
CREATE TYPE delivery_status AS ENUM ('pending', 'sent', 'failed', 'retrying');

CREATE TABLE students (
  id BIGINT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE notifications (
  id UUID PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id),
  notification_type notification_type NOT NULL,
  title TEXT NOT NULL,
  message TEXT NOT NULL,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE notification_deliveries (
  id UUID PRIMARY KEY,
  notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
  channel delivery_channel NOT NULL,
  status delivery_status NOT NULL DEFAULT 'pending',
  attempts INT NOT NULL DEFAULT 0,
  provider_message_id TEXT,
  last_error TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(notification_id, channel)
);

CREATE TABLE notification_outbox (
  id UUID PRIMARY KEY,
  aggregate_type TEXT NOT NULL,
  aggregate_id UUID NOT NULL,
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ NULL
);
```

## Essential indexes
```sql
CREATE INDEX idx_notifications_student_unread_created
  ON notifications (student_id, is_read, created_at DESC);

CREATE INDEX idx_notifications_student_created
  ON notifications (student_id, created_at DESC);

CREATE INDEX idx_notifications_type_created
  ON notifications (notification_type, created_at DESC);

CREATE INDEX idx_deliveries_status_updated
  ON notification_deliveries (status, updated_at);

CREATE INDEX idx_outbox_unprocessed
  ON notification_outbox (processed_at, created_at)
  WHERE processed_at IS NULL;
```

## Queries mapped to Stage 1 APIs

### Create notification
```sql
INSERT INTO notifications (
  id, student_id, notification_type, title, message, metadata
) VALUES (
  $1, $2, $3, $4, $5, $6::jsonb
);
```

### Create delivery rows
```sql
INSERT INTO notification_deliveries (
  id, notification_id, channel, status
) VALUES
  ($1, $2, 'in_app', 'pending'),
  ($3, $2, 'email', 'pending');
```

### Insert outbox event in same transaction
```sql
INSERT INTO notification_outbox (
  id, aggregate_type, aggregate_id, event_type, payload
) VALUES (
  $1, 'notification', $2, 'notification.created', $3::jsonb
);
```

### List notifications
```sql
SELECT id, notification_type, title, message, is_read, created_at
FROM notifications
WHERE student_id = $1
  AND ($2::boolean IS FALSE OR is_read = FALSE)
  AND (created_at, id) < ($3, $4)
ORDER BY created_at DESC, id DESC
LIMIT $5;
```

### Unread count
```sql
SELECT COUNT(*) AS unread_count
FROM notifications
WHERE student_id = $1 AND is_read = FALSE;
```

### Mark one read
```sql
UPDATE notifications
SET is_read = TRUE, updated_at = NOW()
WHERE id = $1 AND student_id = $2;
```

### Mark all read
```sql
UPDATE notifications
SET is_read = TRUE, updated_at = NOW()
WHERE student_id = $1 AND is_read = FALSE;
```

## Problems as volume grows
1. Read-heavy load on list/unread-count endpoints.
2. Hot partitions around the latest notifications.
3. Large table scans when indexes are missing or badly chosen.
4. Expensive offset pagination.
5. Burst fan-out for bulk campaigns.

## Solutions
- Cursor pagination instead of offset pagination.
- Partial/composite indexes shaped around actual filters.
- Table partitioning by time for very large history.
- Redis cache for unread counts and first page of notifications.
- Outbox + broker + worker model for delivery fan-out.
- Archive old notifications to cold storage if needed.

---

# Stage 3

## Is the original query accurate?
Original query:
```sql
SELECT * FROM notifications
WHERE studentID = 1042 AND isRead = false
ORDER BY createdAt DESC;
```

It is **functionally plausible** if the exact column names are `studentID`, `isRead`, and `createdAt`, but it is not ideal.

## Why it is slow
1. `SELECT *` reads unnecessary columns.
2. Without a composite index, the database may scan many rows.
3. Sorting unread rows by `createdAt DESC` becomes expensive at scale.
4. At 5,000,000 rows, poor selectivity or bad indexing can lead to heap reads plus sort work.

## Better query
```sql
SELECT id, notification_type, title, message, created_at
FROM notifications
WHERE student_id = $1
  AND is_read = FALSE
ORDER BY created_at DESC
LIMIT 50;
```

## Best supporting index
```sql
CREATE INDEX idx_notifications_student_unread_created
  ON notifications (student_id, is_read, created_at DESC);
```

### Likely cost profile
- Without index: roughly closer to **O(N log N)** because of scan + sort over large candidate sets.
- With the composite index: close to **O(log N + K)** for index navigation plus returning the top `K` rows.

## Should we add indexes on every column?
No.

### Why not
- Every extra index slows inserts and updates.
- More storage is consumed.
- Poorly chosen indexes are often ignored by the optimizer.
- The right strategy is workload-driven indexing, not blanket indexing.

## Query to find all students who got a placement notification in the last 7 days
```sql
SELECT DISTINCT student_id
FROM notifications
WHERE notification_type = 'Placement'
  AND created_at >= NOW() - INTERVAL '7 days';
```

If student profile data is required:
```sql
SELECT DISTINCT s.id, s.email, s.full_name
FROM notifications n
JOIN students s ON s.id = n.student_id
WHERE n.notification_type = 'Placement'
  AND n.created_at >= NOW() - INTERVAL '7 days';
```

---

# Stage 4

## Problem
Notifications are fetched on every page load for every student, so the database is overloaded and user experience degrades.

## Recommended improvements

### 1) Cache first page + unread count in Redis
- Cache key examples:
  - `student:{id}:notifications:first_page`
  - `student:{id}:unread_count`
- Best for highly repeated reads.
- Tradeoff: cache invalidation complexity.

### 2) Replace full reload with incremental fetch
- Use cursor-based APIs.
- Only fetch new notifications since the latest timestamp already present on client.
- Tradeoff: slightly more client logic.

### 3) WebSocket push for live updates
- Push only new notifications and badge deltas.
- Greatly reduces repeated polling.
- Tradeoff: persistent connection infrastructure required.

### 4) Materialized unread counters
- Maintain unread counts separately in Redis or a compact DB table.
- Tradeoff: eventual consistency if asynchronously maintained.

### 5) Read replicas for heavy read traffic
- Offload list endpoints to replicas.
- Tradeoff: replication lag may show slightly stale reads.

### 6) Partition old data
- Keep hot data small and fast.
- Tradeoff: slightly more operational complexity.

## Recommended combined strategy
Use **WebSockets + Redis cache + cursor pagination + PostgreSQL source of truth**.

---

# Stage 5

## Problems with the proposed pseudocode
```text
function notify_all(student_ids: array, message: string):
    for student_id in student_ids:
        send_email(student_id, message)
        save_to_db(student_id, message)
        push_to_app(student_id, message)
```

### Shortcomings
1. Sequential fan-out is too slow for 50,000 students.
2. Email failure midway causes partial completion.
3. No retry strategy.
4. No idempotency protection.
5. No delivery status tracking.
6. Tight coupling of DB write and external provider call reduces reliability.
7. No backpressure handling.

## What if `send_email` failed for 200 students?
Those 200 students need retryable delivery records. The system must not lose the notification event. Persist first, then process channel delivery asynchronously.

## Should DB save and email send happen together?
They should be **coordinated**, but not as one fragile synchronous unit that depends on an external provider inside the same request path.

### Recommended pattern
- Persist notification + outbox event in **one DB transaction**.
- Worker consumes outbox and sends email/in-app notifications asynchronously.
- Delivery rows track per-channel success, failure, retry count, and last error.

## Revised pseudocode
```text
function bulk_notify(target_segment, payload, idempotency_key):
    if job_exists(idempotency_key):
        return existing_job

    job_id = create_job(target_segment, payload, idempotency_key)

    for each batch of student_ids in target_segment:
        begin transaction
            for each student_id in batch:
                notification_id = insert_notification(student_id, payload)
                insert_delivery(notification_id, 'in_app', 'pending')
                insert_delivery(notification_id, 'email', 'pending')
                insert_outbox_event('notification.created', notification_id)
        commit

        enqueue_batch(job_id, batch)

    return job_id

worker process_batch(job_id, batch):
    for each notification in batch:
        publish_in_app(notification)
        mark_delivery(notification, 'in_app', 'sent')

        try:
            send_email(notification)
            mark_delivery(notification, 'email', 'sent')
        except transient_error:
            schedule_retry(notification, 'email')
            mark_delivery(notification, 'email', 'retrying')
        except fatal_error:
            mark_delivery(notification, 'email', 'failed')
```

## Reliability and speed improvements
- Batch processing.
- Message queue for parallel workers.
- Idempotency key to prevent duplicate campaigns.
- Outbox pattern to avoid message loss.
- Channel-specific retry policy with exponential backoff.
- Job status endpoint for visibility.

---

# Stage 6

## Priority Inbox approach
Priority is driven by:
1. **Type weight**: Placement > Result > Event
2. **Recency**: newer notifications score higher

### Scoring model
```text
score = (type_weight * 10) + recency_bonus
where Placement=3, Result=2, Event=1
and recency_bonus = 1 / (1 + age_in_minutes)
```

This ensures type dominates, while recency breaks ties naturally.

## Efficient maintenance of top 10 as new notifications arrive
Use a **min-heap of size 10** per student:
- Insert new unread notification with computed score.
- If heap size < 10, push directly.
- Else compare with smallest score in heap.
- Replace smallest only when new score is higher.

### Complexity
- Insert/update: **O(log 10)** which is effectively constant.
- Read top 10: **O(10 log 10)** after sorting the tiny heap.

## Python code
```python
from datetime import datetime
import heapq

TYPE_WEIGHT = {"Placement": 3.0, "Result": 2.0, "Event": 1.0}


def compute_score(notification, newest_ts):
    current_ts = datetime.strptime(notification["Timestamp"], "%Y-%m-%d %H:%M:%S")
    age_seconds = max((newest_ts - current_ts).total_seconds(), 0.0)
    recency_bonus = 1 / (1 + age_seconds / 60)
    return TYPE_WEIGHT.get(notification["Type"], 0.0) * 10 + recency_bonus


def top_n_notifications(notifications, n=10):
    if not notifications:
        return []

    newest_ts = max(datetime.strptime(item["Timestamp"], "%Y-%m-%d %H:%M:%S") for item in notifications)
    heap = []

    for item in notifications:
        scored = (compute_score(item, newest_ts), item)
        if len(heap) < n:
            heapq.heappush(heap, scored)
        elif scored[0] > heap[0][0]:
            heapq.heapreplace(heap, scored)

    return [item for _, item in sorted(heap, reverse=True)]
```

## Why this works well
- Very fast for continuously arriving notifications.
- Easy to recompute on mark-read/unread transitions.
- Type weight reflects business importance.
- Recency keeps stale placement messages from permanently outranking fresh relevant ones.
