/** A transcript's markdown, formatted. Covers the shapes vault/writer.py
 * writes: # and ## headings, > quote lines, --- rules, paragraphs, and inline
 * **bold**, *italic* (diarized timestamps), `code` and [text](url) links.
 *
 * Builds React elements only, never HTML: titles and text come from the
 * internet. Links open only for http and https.
 */

import type { ReactNode } from "react";

// `code` | **bold** | *italic* | [text](url)
// (bold and italic need no space just inside their stars, as in markdown)
const INLINE = /`([^`]+)`|\*\*([^\s*](?:.*?\S)?)\*\*|\*([^*\s](?:[^*]*[^*\s])?)\*|\[([^\]]+)\]\(([^)\s]+)\)/g;

function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const key = out.length;
    if (m[1] !== undefined) {
      out.push(
        <code key={key} className="font-mono text-[0.85em] bg-surface-raised rounded px-1 py-0.5">
          {m[1]}
        </code>
      );
    } else if (m[2] !== undefined) {
      out.push(
        <strong key={key} className="font-semibold text-text">
          {inline(m[2])}
        </strong>
      );
    } else if (m[3] !== undefined) {
      out.push(<em key={key}>{inline(m[3])}</em>);
    } else if (/^https?:\/\//i.test(m[5])) {
      out.push(
        <a
          key={key}
          href={m[5]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-amber hover:underline"
        >
          {m[4]}
        </a>
      );
    } else {
      out.push(m[4]); // not http(s): the label only, never a live link
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function TranscriptBody({ body, title }: { body: string; title: string }) {
  const blocks: ReactNode[] = [];
  let para: string[] = [];
  let quote: string[] = [];

  const flush = () => {
    if (para.length) {
      blocks.push(
        <p key={blocks.length} className="mb-4 whitespace-pre-line">
          {inline(para.join("\n"))}
        </p>
      );
      para = [];
    }
    if (quote.length) {
      blocks.push(
        <blockquote
          key={blocks.length}
          className="mb-4 border-l-[3px] border-blue bg-blue/[0.07] rounded-md px-3 py-2 text-[14px] whitespace-pre-line"
        >
          {inline(quote.join("\n"))}
        </blockquote>
      );
      quote = [];
    }
  };

  for (const raw of body.split("\n")) {
    const line = raw.trimEnd();
    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flush();
      const [, hashes, text] = heading;
      // the page shows the title already
      if (blocks.length === 0 && hashes === "#" && text.trim() === title.trim()) continue;
      blocks.push(
        hashes === "#" ? (
          <h2 key={blocks.length} className="text-xl font-semibold text-text mt-2 mb-3">
            {inline(text)}
          </h2>
        ) : (
          <h3
            key={blocks.length}
            className="text-xs font-mono uppercase tracking-wider text-text-muted mt-6 mb-3"
          >
            {inline(text)}
          </h3>
        )
      );
    } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flush();
      blocks.push(<hr key={blocks.length} className="my-5 border-border-subtle" />);
    } else if (/^>\s?/.test(line)) {
      if (para.length) flush();
      quote.push(line.replace(/^>\s?/, ""));
    } else if (!line.trim()) {
      flush();
    } else {
      if (quote.length) flush();
      para.push(line);
    }
  }
  flush();

  if (blocks.length === 0) {
    return <p className="text-sm text-text-muted">This transcript has no text.</p>;
  }
  return (
    <div className="max-w-[70ch] text-[15px] leading-7 text-text-secondary break-words">
      {blocks}
    </div>
  );
}
