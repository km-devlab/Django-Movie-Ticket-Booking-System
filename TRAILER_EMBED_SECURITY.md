# Secure YouTube Trailer Embedding

## What was implemented

- Movies now support an optional `trailer_url` field.
- Only YouTube watch, embed, shorts, and `youtu.be` URLs with valid 11-character video IDs are accepted.
- Templates never render raw trailer HTML from the database.
- The page builds a safe `youtube-nocookie.com/embed/<video_id>` iframe URL server-side.
- The iframe uses `loading="lazy"` so trailers do not slow the first page render.
- If no trailer is configured, the movie detail page shows a graceful fallback message.

## XSS prevention

Admins store only a URL, not an HTML snippet or script. The validator rejects non-YouTube hosts and invalid video IDs. The template uses Django escaping and only renders the sanitized embed URL generated from the extracted video ID.

## Performance controls

The trailer iframe is lazy-loaded and constrained to a responsive 16:9 container. This keeps mobile/tablet layouts stable and prevents the YouTube player from loading until the browser needs it.
