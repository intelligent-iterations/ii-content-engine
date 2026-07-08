#!/usr/bin/env node

import fs from 'fs';
import path from 'path';

function parseArgs(argv) {
  const args = {
    input: null,
    output: null,
    topic: 'Xquik social research',
    limit: 50,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--output' || arg === '-o') {
      args.output = argv[index + 1] || null;
      index += 1;
    } else if (arg === '--topic') {
      args.topic = argv[index + 1] || args.topic;
      index += 1;
    } else if (arg === '--limit') {
      args.limit = Number.parseInt(argv[index + 1] || '', 10) || args.limit;
      index += 1;
    } else if (!args.input) {
      args.input = arg;
    }
  }

  return args;
}

function readJsonOrJsonl(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8').trim();
  if (!raw) {
    return [];
  }

  try {
    return JSON.parse(raw);
  } catch (jsonError) {
    const rows = raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line, index) => {
        try {
          return JSON.parse(line);
        } catch (lineError) {
          throw new Error(`Invalid JSONL at line ${index + 1}: ${lineError.message}`);
        }
      });

    if (!rows.length) {
      throw jsonError;
    }
    return rows;
  }
}

function rowsFromPayload(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (!payload || typeof payload !== 'object') {
    return [];
  }
  if (pickFirst(payload.id, payload.tweetId, payload.tweet_id, payload.statusId, payload.status_id)) {
    return [payload];
  }
  for (const key of ['tweets', 'posts', 'data', 'results', 'items']) {
    if (Array.isArray(payload[key])) {
      return payload[key];
    }
  }
  return [];
}

function pickFirst(...values) {
  for (const value of values) {
    if (value !== undefined && value !== null && String(value).trim()) {
      return value;
    }
  }
  return '';
}

function normalizeMetric(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, Math.round(value));
  }
  const normalized = String(value || '').replace(/,/g, '').trim().toLowerCase();
  const match = normalized.match(/^(\d+(?:\.\d+)?)([km])?$/);
  if (!match) {
    return 0;
  }
  let parsed = Number(match[1]);
  if (!Number.isFinite(parsed)) {
    return 0;
  }
  if (match[2] === 'k') {
    parsed *= 1000;
  } else if (match[2] === 'm') {
    parsed *= 1000000;
  }
  return Math.max(0, Math.round(parsed));
}

function normalizeUrl(value, id) {
  const fallback = id ? `https://x.com/i/web/status/${id}` : '';
  const raw = String(value || fallback).trim();
  const url = raw
    .replace('https://twitter.com/', 'https://x.com/')
    .replace('https://www.twitter.com/', 'https://x.com/')
    .replace('https://www.x.com/', 'https://x.com/');
  if (/^https:\/\/x\.com\/.+\/status\/\d+/i.test(url) || /^https:\/\/x\.com\/i\/web\/status\/\d+/i.test(url)) {
    return url;
  }
  return fallback;
}

function normalizePost(row) {
  if (!row || typeof row !== 'object') {
    return null;
  }

  const id = String(
    pickFirst(row.id, row.tweetId, row.tweet_id, row.statusId, row.status_id)
  ).trim();
  if (!/^\d{5,}$/.test(id)) {
    return null;
  }

  const author = row.author && typeof row.author === 'object' ? row.author : {};
  const stats = row.stats && typeof row.stats === 'object' ? row.stats : {};
  const username = String(
    pickFirst(row.username, row.handle, row.screenName, row.screen_name, author.username, author.handle)
  ).replace(/^@/, '');
  const text = String(
    pickFirst(row.text, row.fullText, row.full_text, row.content, row.body)
  ).trim();

  return {
    id,
    url: normalizeUrl(pickFirst(row.url, row.tweetUrl, row.tweet_url, row.permalink), id),
    author: username,
    display_name: String(
      pickFirst(row.displayName, row.authorName, row.name, author.displayName, author.name)
    ).trim(),
    created_at: String(
      pickFirst(row.createdAt, row.created_at, row.timestamp, row.time, row.date)
    ).trim(),
    text,
    metrics: {
      replies: normalizeMetric(pickFirst(row.replies, row.replyCount, stats.replies)),
      reposts: normalizeMetric(pickFirst(row.retweets, row.reposts, row.retweetCount, stats.retweets)),
      likes: normalizeMetric(pickFirst(row.likes, row.likeCount, stats.likes)),
      bookmarks: normalizeMetric(pickFirst(row.bookmarks, row.bookmarkCount, stats.bookmarks)),
      views: normalizeMetric(pickFirst(row.views, row.viewCount, stats.views)),
    },
  };
}

function buildResearchArtifact({ posts, topic, sourcePath }) {
  return {
    topic,
    source: {
      label: 'Xquik export',
      path: path.relative(process.cwd(), sourcePath),
    },
    generated_at: new Date().toISOString(),
    summary: [
      `Imported ${posts.length} X posts from a reviewed Xquik export.`,
      'Use these posts as saved research context before writing carousel, video, or post artifacts.',
      'Verify rights, relevance, and tone before quoting or republishing any source text.',
    ],
    sources: posts.map((post) => ({
      label: post.author ? `@${post.author}` : post.id,
      url: post.url,
      created_at: post.created_at || null,
    })),
    posts,
  };
}

function usage() {
  console.error('Usage: node code/cli/xquik-research.js <xquik-export.jsonl> [--output research/xquik.json] [--topic "Topic"] [--limit 50]');
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.input) {
    usage();
    process.exit(1);
  }

  const inputPath = path.resolve(args.input);
  const payload = readJsonOrJsonl(inputPath);
  const posts = rowsFromPayload(payload)
    .map(normalizePost)
    .filter(Boolean)
    .slice(0, Math.max(args.limit, 1));

  if (!posts.length) {
    throw new Error('No valid Xquik tweet rows were found.');
  }

  const outputPath = path.resolve(args.output || path.join('research', 'xquik-research.json'));
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(
    outputPath,
    `${JSON.stringify(buildResearchArtifact({ posts, topic: args.topic, sourcePath: inputPath }), null, 2)}\n`
  );
  console.log(outputPath);
}

main();
