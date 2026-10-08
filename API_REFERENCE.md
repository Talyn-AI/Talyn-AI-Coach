# Talyn AI Coach API reference

Generated from the application's OpenAPI schema — do not edit by hand.
Regenerate with `python -m scripts.generate_api_reference`.

## Conventions

| Column | Meaning |
|---|---|
| `🔒 backend JWT` | pass the learner's backend access token as `backend_token` in the request body |
| `— public` | no token needed |
| `✓` wired | some frontend page calls this |
| `—` unwired | backend only; no page calls it yet |

Base URL: every path below as-is. In development that is
`http://localhost:8001`; deployed it is the coach's public origin
(`VITE_COACH_URL` / the coach base URL on the frontend).

Auth: every row marked 🔒 takes `backend_token` — the same JWT the
backend issues at login — inside the JSON body, not as a header.
The coach loads the live learner context with it and validates it
against the backend, so a forged or expired token fails here, not
silently downstream. There is deliberately no anonymous mode in
production: every call bills a real API, so every call proves who
is asking. (Mock mode, `TALYN_MOCK=1`, accepts an inline `learner`
object instead — local development and tests only.)

Errors are always `{"detail": "..."}`; validation errors put an array
of objects in `detail` instead. Timestamps are UTC ISO-8601.

## Calling the coach from the frontend

1. The learner signs in through the backend; keep its `access_token`.
2. `POST` the coach endpoint with `backend_token` set to that token
   plus the action fields. Do not send a `learner` object from the
   browser in production — the coach rejects it with 401.
3. Render the structured response directly; quiz, path, schedule,
   and insight payloads are shaped for UI consumption.

Rate limit: 30 requests/minute per IP, shared across endpoints.
A loop that retries without backoff will spend that budget fast —
and each retried call would have billed again.

---

21 endpoints across 9 areas.

## Ai Insights

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/insights/generate` | 🔒 backend JWT | ✓ |
| | `POST` | `/insights/priority` | 🔒 backend JWT | ✓ |

### POST /insights/generate

Analyses the learner's performance and behaviour data (quiz scores, XP,
streaks, lessons completed, mission progress) into an honest report with:

- Learning strengths (evidence-based)
- Weaknesses (honest, never shaming)
- Improvement suggestions (actionable this week)
- Progress forecast (with stated assumptions)

**When to call this:**
- On a weekly check-in
- When a learner opens a dashboard / progress view

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | sightsAction | no | default `generate_insights` |
| `learner_id` | string | yes | — |
| `report` | sightsReport | yes | — |

<details><summary><code>report</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `summary` | string | yes | — |
| `strengths` | array of Strength | yes | — |
| `weaknesses` | array of Weakness | yes | — |
| `suggestions` | array of ImprovementSuggestion | yes | — |
| `forecast` | ProgressForecast | yes | — |

</details>

- **422** Validation Error


### POST /insights/priority

Returns the 1-3 highest-impact actions the learner should focus on this
week, each with a concrete action and a success metric, plus a short
encouraging framing message.

**When to call this:**
- At the start of each week
- After significant progress or performance changes

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | sightsAction | no | default `priority_focus` |
| `learner_id` | string | yes | — |
| `priorities` | array of PriorityFocus | yes | — |
| `message` | string | yes | — |

<details><summary><code>priorities</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `focus_area` | string | yes | — |
| `action` | string | yes | — |
| `rationale` | string | yes | — |
| `suggested_metric` | string | yes | — |

</details>

- **422** Validation Error


## Ai Learning Coach

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/coach/ask` | 🔒 backend JWT | ✓ |
| | `POST` | `/coach/course-qa` | 🔒 backend JWT | — |
| | `POST` | `/coach/encourage` | 🔒 backend JWT | ✓ |
| | `POST` | `/coach/explain` | 🔒 backend JWT | ✓ |
| | `POST` | `/coach/quiz` | 🔒 backend JWT | ✓ |
| | `POST` | `/coach/study-plan` | 🔒 backend JWT | ✓ |

### POST /coach/ask

The learner asks a free-form question about their current course or topic.
The coach responds with a personalized, context-aware answer.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `question` | string | yes | — |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | CoachAction | yes | — |
| `learner_id` | string | yes | — |
| `response` | string | yes | — |

- **422** Validation Error


### POST /coach/course-qa

Grounded Q&A: the backend passes the actual lesson text, and the answer
must come from it — never from general knowledge. The backend (not the
model) reports which lessons were supplied, so citations stay truthful.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `course_title` | string | yes | — |
| `content` | string | yes | — |
| `question` | string | yes | — |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `answer` | string | yes | — |

- **422** Validation Error


### POST /coach/encourage

Triggered by backend events (lesson completed, quiz failed, streak at risk, etc.)
Returns a short, personalized motivational message.

Example triggers:
- "completed lesson"
- "low quiz score on CSS Flexbox"
- "streak at risk — hasn't studied today"
- "reached 50% course completion"
- "earned 500 XP this week"

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `trigger` | string | yes | What triggered this encouragement moment, e.g. 'completed lesson', 'low quiz score', 'streak at risk' |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | CoachAction | yes | — |
| `learner_id` | string | yes | — |
| `response` | string | yes | — |

- **422** Validation Error


### POST /coach/explain

The coach explains a concept, adapting the example to the learner's
declared interests and difficulty level.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `concept` | string | yes | — |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | CoachAction | yes | — |
| `learner_id` | string | yes | — |
| `response` | string | yes | — |

- **422** Validation Error


### POST /coach/quiz

Generates a multiple-choice quiz tailored to the learner's level and
prior performance on the topic. Returns structured JSON for the frontend
to render directly.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `topic` | string | yes | — |
| `num_questions` | integer | no | default `5` |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | CoachAction | no | default `generate_quiz` |
| `learner_id` | string | yes | — |
| `topic` | string | yes | — |
| `questions` | array of QuizQuestion | yes | — |

<details><summary><code>questions</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `question` | string | yes | — |
| `options` | array of string | yes | — |
| `correct_answer` | string | yes | — |
| `explanation` | string | yes | — |

</details>

- **422** Validation Error


### POST /coach/study-plan

Creates a structured study plan based on the learner's goals, current
progress, quiz performance, and available time.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `goals` | string | yes | What the learner wants to achieve |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | CoachAction | yes | — |
| `learner_id` | string | yes | — |
| `response` | string | yes | — |

- **422** Validation Error


## Ai-Generated Revision Schedules

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/revision/generate` | 🔒 backend JWT | — |
| | `POST` | `/revision/update` | 🔒 backend JWT | — |

### POST /revision/generate

Analyses the learner's full topic history — quiz scores, days since studied,
review counts, and lesson completion — and generates a 30-day spaced repetition
schedule that maximises long-term retention.

Each entry in the schedule includes:
- The topic to revise and which lesson it belongs to
- The suggested revision method (quiz / flashcard / re-read)
- Estimated time in minutes
- The specific reason this topic was scheduled on this day

**When to call this:**
- When a learner first requests a revision schedule
- At the start of a new month / study period
- When a learner's topic history changes significantly (e.g. completed many new lessons)

**Spaced repetition logic applied:**
- Topics with low quiz scores are scheduled sooner and more frequently
- Topics studied long ago are prioritised over recently studied ones
- Daily session length is capped to the learner's `daily_study_minutes` budget
- Rest days are included naturally — not every day has a revision task

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | RevisionScheduleProfile *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner_id` | string | yes | — |
| `schedule_start_date` | string | yes | — |
| `total_days` | integer | yes | — |
| `summary` | string | yes | — |
| `entries` | array of RevisionEntry | yes | — |

<details><summary><code>entries</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `day` | integer | yes | — |
| `date` | string | yes | — |
| `topic` | string | yes | — |
| `lesson` | string | yes | — |
| `method` | RevisionMethod | yes | — |
| `estimated_minutes` | integer | yes | — |
| `reason` | string | yes | — |

</details>

- **422** Validation Error


### POST /revision/update

Called by the backend immediately after a learner completes a revision session.
Re-evaluates and regenerates the schedule for the remaining days based on the
outcome of the session.

**Adaptive behaviour:**
- If the quiz score was **low (<60%)**: the topic is resurfaced sooner in the
  remaining schedule with a higher-intensity method (quiz)
- If the quiz score was **high (80%+)**: the topic is pushed later or dropped,
  freeing up time for weaker areas
- All other topics are also re-evaluated against the updated topic history

**When to call this:**
- After every completed revision session
- Pass the current day number (1–29) so the AI only regenerates what's left

**Returns:** The updated schedule for days `current_schedule_day + 1` to 30

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | RevisionScheduleProfile *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object |
| `completed_topic` | string | yes | — |
| `session_quiz_score` | number *(nullable)* | no | — |
| `current_schedule_day` | integer | yes | — |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner_id` | string | yes | — |
| `schedule_start_date` | string | yes | — |
| `total_days` | integer | yes | — |
| `summary` | string | yes | — |
| `entries` | array of RevisionEntry | yes | — |

<details><summary><code>entries</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `day` | integer | yes | — |
| `date` | string | yes | — |
| `topic` | string | yes | — |
| `lesson` | string | yes | — |
| `method` | RevisionMethod | yes | — |
| `estimated_minutes` | integer | yes | — |
| `reason` | string | yes | — |

</details>

- **422** Validation Error


## Health

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `GET` | `/health` | — public | — |

### GET /health

**Responses**

**200**

_empty_


## Interest-Based Content Personalization

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/personalize/batch` | 🔒 backend JWT | — |
| | `POST` | `/personalize/content` | 🔒 backend JWT | — |

### POST /personalize/batch

Personalizes multiple pieces of content for the same learner in one call.
More efficient than calling `/personalize/content` repeatedly when loading
a full lesson (explanation + examples + exercise brief together).

**Request body example:**
```json
{
  "learner": { ... },
  "items": [
    { "content_type": "explanation", "original_content": "CSS Flexbox is a layout model..." },
    { "content_type": "example", "original_content": "Consider a navigation bar with..." },
    { "content_type": "exercise_brief", "original_content": "Build a responsive card grid..." }
  ]
}
```

**When to call this:**
- On lesson load — send all content pieces at once
- Maximum recommended batch size: 5 items

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | PersonalizationProfile *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object |
| `items` | array of object | yes | List of {content_type, original_content} objects to personalize in batch |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner_id` | string | yes | — |
| `items` | array of BatchPersonalizedItem | yes | — |

<details><summary><code>items</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `content_type` | ContentType | yes | — |
| `original_content` | string | yes | — |
| `personalized_content` | string | yes | — |
| `interest_used` | string | yes | — |

</details>

- **422** Validation Error


### POST /personalize/content

Takes an original piece of course content and rewrites it so the framing,
analogies, and examples reflect the learner's personal interests — while
keeping the concept, facts, and learning objective exactly intact.

**Content types:**
- `explanation` — A lesson explanation or concept introduction
- `example` — A worked example illustrating a concept
- `quiz_context` — The scenario/context of a quiz question
- `exercise_brief` — A project or practice exercise brief

**When to call this:**
- When rendering a lesson for a specific learner
- Before displaying a quiz question to add personal context
- When showing an exercise brief

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | PersonalizationProfile *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object |
| `content_type` | ContentType | yes | — |
| `original_content` | string | yes | The original course content to be personalized — explanation, example, quiz context, or exercise brief |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner_id` | string | yes | — |
| `content_type` | ContentType | yes | — |
| `original_content` | string | yes | — |
| `personalized_content` | string | yes | — |
| `interest_used` | string | yes | — |

- **422** Validation Error


## Mission-Based Learning

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/mission/guide` | 🔒 backend JWT | — |
| | `POST` | `/mission/recommend` | 🔒 backend JWT | — |

### POST /mission/guide

Looks at the learner's active mission (its steps and which are done) and
returns warm, concrete coaching for the single next step.

**When to call this:**
- When a learner opens their active mission
- After a mission step is completed (to surface the next step)

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | MissionAction | no | default `guide_mission` |
| `learner_id` | string | yes | — |
| `mission_title` | string | yes | — |
| `next_step` | RecommendedMissionStep | yes | — |
| `message` | string | yes | — |

<details><summary><code>next_step</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `order` | integer | yes | — |
| `title` | string | yes | — |
| `description` | string | yes | — |

</details>

- **422** Validation Error


### POST /mission/recommend

Analyses the learner's stage (onboarding, in-progress, returning after a
break) and recommends a short, achievable mission designed to create a
quick win.

**When to call this:**
- When a learner first joins the platform (First Mission)
- After a learner completes their previous mission
- When a learner requests something new to do

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | MissionAction | no | default `recommend_mission` |
| `learner_id` | string | yes | — |
| `mission_title` | string | yes | — |
| `mission_description` | string | yes | — |
| `purpose` | string | yes | — |
| `reward_xp` | integer | yes | — |
| `badge` | string *(nullable)* | no | — |
| `steps` | array of RecommendedMissionStep | yes | — |
| `message` | string | yes | — |

<details><summary><code>steps</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `order` | integer | yes | — |
| `title` | string | yes | — |
| `description` | string | yes | — |

</details>

- **422** Validation Error


## Personalized Learning Path

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/path/adjust` | 🔒 backend JWT | — |
| | `POST` | `/path/generate` | 🔒 backend JWT | — |

### POST /path/adjust

Re-evaluates and updates an existing learning path given a reason for change.

The AI may remove, add, reorder, or replace courses depending on the reason.

**Example reasons:**
- `"learner is progressing faster than expected"`
- `"learner is struggling with current course and needs easier material first"`
- `"learner changed goal from frontend to full-stack development"`
- `"learner now has 10 hours/week instead of 5"`
- `"learner completed an external course on Python basics"`

**When to call this:**
- When learner changes goals
- After significant quiz performance changes
- When learner requests a path review
- On a scheduled monthly path review

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerPathProfile *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object |
| `current_path_course_ids` | array of string | yes | The course IDs in the learner's current path, in order |
| `reason` | string | yes | Why the path needs adjusting, e.g. 'learner is ahead of schedule', 'learner struggling with current course', 'learner changed goals' |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | PathAction | yes | — |
| `learner_id` | string | yes | — |
| `summary` | string | yes | — |
| `recommended_courses` | array of RecommendedCourse | yes | — |
| `milestones` | array of Milestone | yes | — |
| `weekly_schedule` | array of WeeklyScheduleEntry | yes | — |
| `total_estimated_weeks` | number | yes | — |

<details><summary><code>recommended_courses</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `order` | integer | yes | — |
| `course_id` | string | yes | — |
| `title` | string | yes | — |
| `why_recommended` | string | yes | — |
| `estimated_hours` | number | yes | — |
| `estimated_weeks` | number | yes | — |

</details>

<details><summary><code>milestones</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | — |
| `description` | string | yes | — |
| `due_week` | integer | yes | — |

</details>

<details><summary><code>weekly_schedule</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `week` | integer | yes | — |
| `focus` | string | yes | — |
| `course_title` | string | yes | — |
| `hours_recommended` | number | yes | — |

</details>

- **422** Validation Error


### POST /path/generate

Takes a learner profile (skill level, goals, interests, available time)
and the full course catalogue, then returns an ordered path with:

- Recommended courses (with reasoning per course)
- Estimated time per course
- Milestones & checkpoints
- Week-by-week schedule

**When to call this:**
- When a new learner onboards and needs a path
- When a learner resets or changes their goals entirely

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerPathProfile *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live profile from the backend instead of using an inline 'learner' object |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | PathAction | yes | — |
| `learner_id` | string | yes | — |
| `summary` | string | yes | — |
| `recommended_courses` | array of RecommendedCourse | yes | — |
| `milestones` | array of Milestone | yes | — |
| `weekly_schedule` | array of WeeklyScheduleEntry | yes | — |
| `total_estimated_weeks` | number | yes | — |

<details><summary><code>recommended_courses</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `order` | integer | yes | — |
| `course_id` | string | yes | — |
| `title` | string | yes | — |
| `why_recommended` | string | yes | — |
| `estimated_hours` | number | yes | — |
| `estimated_weeks` | number | yes | — |

</details>

<details><summary><code>milestones</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | — |
| `description` | string | yes | — |
| `due_week` | integer | yes | — |

</details>

<details><summary><code>weekly_schedule</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `week` | integer | yes | — |
| `focus` | string | yes | — |
| `course_title` | string | yes | — |
| `hours_recommended` | number | yes | — |

</details>

- **422** Validation Error


## Study Buddy System

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/buddy/icebreaker` | 🔒 backend JWT | ✓ |
| | `POST` | `/buddy/match` | 🔒 backend JWT | — |

### POST /buddy/icebreaker

Generates a natural, personal opening message for the learner to send their
chosen buddy — grounded in shared interests/goals, with one concrete next
step to get the partnership moving.

**When to call this:**
- When the learner picks a buddy from the match results

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `buddy` | BuddyCandidate | yes | The buddy the learner chose to start a conversation with |

<details><summary><code>buddy</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner_id` | string | yes | — |
| `learner_name` | string | yes | — |
| `skill_level` | DifficultyLevel | yes | — |
| `interests` | array of string | no | default `[]` |
| `current_course` | string | no | default `` |
| `goals` | string | no | default `` |
| `hours_per_week` | number | no | default `0.0` |
| `schedule` | string | no | default `` |
| `xp_this_week` | integer | no | default `0` |
| `streak_days` | integer | no | default `0` |

</details>


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | BuddyAction | no | default `icebreaker` |
| `learner_id` | string | yes | — |
| `buddy_id` | string | yes | — |
| `buddy_name` | string | yes | — |
| `message` | string | yes | — |

- **422** Validation Error


### POST /buddy/match

Ranks the given candidate pool for the learner using six weighted criteria:
goals alignment, course/topic overlap, interest overlap, skill level
closeness, time availability, and consistency.

Returns matches best-first with a compatibility score, reasons, shared
interests, and a ready-to-send intro message for the top match.

**When to call this:**
- When a learner opts into the Study Buddy System
- Periodically to refresh suggestions as learners progress

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `candidates` | array of BuddyCandidate | yes | The pool of learners the AI should rank as potential study buddies |

<details><summary><code>candidates</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner_id` | string | yes | — |
| `learner_name` | string | yes | — |
| `skill_level` | DifficultyLevel | yes | — |
| `interests` | array of string | no | default `[]` |
| `current_course` | string | no | default `` |
| `goals` | string | no | default `` |
| `hours_per_week` | number | no | default `0.0` |
| `schedule` | string | no | default `` |
| `xp_this_week` | integer | no | default `0` |
| `streak_days` | integer | no | default `0` |

</details>


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `action` | BuddyAction | no | default `find_buddy` |
| `learner_id` | string | yes | — |
| `matches` | array of BuddyMatch | yes | — |
| `intro_message` | string | yes | — |

<details><summary><code>matches</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `buddy_id` | string | yes | — |
| `learner_name` | string | yes | — |
| `match_score` | integer | yes | — |
| `shared_interests` | array of string | no | default `[]` |
| `reasons` | array of string | yes | — |
| `caveat` | string *(nullable)* | no | — |

</details>

- **422** Validation Error


## Study Materials

| | Method | Path | Auth | Wired |
|---|---|---|---|---|
| | `POST` | `/coach/analyze-material` | 🔒 backend JWT | — |
| | `POST` | `/coach/generate-schedule` | 🔒 backend JWT | — |

### POST /coach/analyze-material

The free preview behind "Here's what we found". One call per analysis —
the backend decides when re-analysis is warranted, not the caller.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `document_text` | string | yes | — |
| `filename` | string | yes | — |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `topics` | array of string | yes | — |
| `objectives` | array of string | yes | — |
| `estimated_minutes` | integer | yes | — |
| `summary` | string | yes | — |

- **422** Validation Error


### POST /coach/generate-schedule

Runs only after the backend has confirmed payment. The backend stores
the result; this endpoint is pure generation with no side effects.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `learner` | LearnerContext *(nullable)* | no | — |
| `backend_token` | string *(nullable)* | no | Backend JWT — the coach loads the live learner context from the backend instead of using an inline 'learner' object |
| `document_text` | string | yes | — |
| `topics` | array of string | no | — |
| `objectives` | array of string | no | — |
| `days` | integer | no | default `14` |
| `difficulty` | string | no | default `beginner` |
| `purpose` | string | no | default `` |


**Responses**

**200**

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | — |
| `days` | array of ScheduleDay | yes | — |

<details><summary><code>days</code> object</summary>

| Field | Type | Required | Notes |
|---|---|---|---|
| `day` | integer | yes | — |
| `title` | string | yes | — |
| `objectives` | array of string | no | default `[]` |
| `tasks` | array of string | no | default `[]` |

</details>

- **422** Validation Error

