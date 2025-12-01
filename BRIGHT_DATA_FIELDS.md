# Bright Data Webhook Fields - Field Mapping Guide

Based on the actual webhook response, here are the fields you should use:

## ✅ ESSENTIAL FIELDS (Required for your app)

| Bright Data Field | Your App Field | Description | Example |
|------------------|----------------|-------------|---------|
| `video_id` | `video_id` | Unique YouTube video ID | `"1w5cCXlh7JQ"` |
| `title` | `title` | Video title | `"LangGraph Tutorial - How to Build Advanced AI Agent Systems"` |
| `transcript` | `transcript` | Full transcript text (plain text) | `"Overview In this video..."` (51KB+ text) |

**Note:** `formatted_transcript` is also available as an array with timestamps, but the plain `transcript` is better for summarization.

---

## 🟠 IMPORTANT FIELDS (Highly Recommended)

| Bright Data Field | Your App Field | Description | Example |
|------------------|----------------|-------------|---------|
| `video_length` | `video_length` | Duration in **seconds** | `2808` (46.8 minutes) |
| `preview_image` | `thumbnail_url` | Video thumbnail URL | `"https://i.ytimg.com/vi/1w5cCXlh7JQ/hqdefault.jpg"` |
| `date_posted` | `published_at` | Publication date (ISO format) | `"2025-05-05T12:54:24.000Z"` |
| `handle_name` or `youtuber` | `channel_name` | Channel name (prefer `handle_name`) | `"Tech With Tim"` or `"@TechWithTim"` |
| `avatar_img_channel` | `channel_avatar` | Channel profile picture | `"https://yt3.ggpht.com/..."` |
| `channel_url` | `channel_url` | Channel URL | `"https://www.youtube.com/@TechWithTim"` |

**Note:** `handle_name` is cleaner (no @), but `youtuber` is also available. The parser uses `handle_name` first.

---

## 🟡 USEFUL FIELDS (Nice to Have)

| Bright Data Field | Your App Field | Description | Example |
|------------------|----------------|-------------|---------|
| `views` | `view_count` | Total video views | `157818` |
| `likes` | `like_count` | Total likes | `3494` |
| `subscribers` | `subscriber_count` | Channel subscribers | `1910000` |
| `description` | `description` | Video description (truncated to 500 chars) | `"Download PyCharm..."` |

---

## ⚪ OPTIONAL FIELDS (May not be needed)

| Bright Data Field | Your App Field | Description |
|------------------|----------------|-------------|
| `quality_label` | `quality` | Video quality | `"1440p60"` |
| `num_comments` | `num_comments` | Number of comments | `95` |
| `verified` | `verified` | Channel verified status | `true` |
| `formatted_transcript` | - | Array with timestamped transcript segments | Not used (use `transcript` instead) |
| `related_videos` | - | Array of related video URLs | Not used |
| `tags` | - | Array of video tags | Not used |
| `chapters` | - | Array of video chapters | Not used |

---

## 📋 Current Field Mapping in Code

The parser in `services/bright_data.py` now correctly maps:

```python
# ESSENTIAL
video_id → video_id
title → title
transcript → transcript (prefers plain text, falls back to formatted)

# IMPORTANT
video_length → video_length (seconds)
preview_image → thumbnail_url
date_posted → published_at
handle_name/youtuber → channel_name (removes @ if present)
avatar_img_channel → channel_avatar
channel_url → channel_url

# USEFUL
views → view_count
likes → like_count
subscribers → subscriber_count
description → description (truncated to 500 chars)

# OPTIONAL
quality_label → quality
num_comments → num_comments
verified → verified
```

---

## 🎯 Fields Used in Your App

Based on `app.py`, your app uses these fields:

1. **For Display:**
   - `title` - Video title
   - `channel_name` - Channel name
   - `thumbnail_url` - Video thumbnail
   - `video_length` - Duration (converted to minutes for display)

2. **For Processing:**
   - `transcript` - Used to generate summary
   - `video_length` - Used for usage tracking (minutes)

3. **For Metadata:**
   - `published_at` - Publication date
   - `view_count`, `like_count` - Engagement metrics
   - `description` - Video description

4. **For Database:**
   - All fields are stored in Firestore for later retrieval

---

## ✅ Summary

**Keep using these fields:**
- ✅ All ESSENTIAL fields (video_id, title, transcript)
- ✅ All IMPORTANT fields (video_length, thumbnails, channel info, dates)
- ✅ Most USEFUL fields (views, likes, description)

**You can ignore:**
- ❌ `formatted_transcript` (use plain `transcript` instead)
- ❌ `related_videos`, `tags`, `chapters` (not needed for your use case)
- ❌ `video_url` (internal Google video URL, not useful)
- ❌ Technical fields like `codecs`, `color`, `viewport_frames`

The parser has been updated to correctly extract all these fields from the Bright Data webhook response!

