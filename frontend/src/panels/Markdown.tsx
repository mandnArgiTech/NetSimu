// react-markdown wrapper that converts `[text](concept:something)` links
// into clickable handles that switch the panel content rather than
// navigating away.

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ComponentPropsWithoutRef } from "react";

interface MarkdownProps {
  body: string;
  /** Called when the user clicks an internal `concept:id` link. */
  onConceptLink: (conceptId: string) => void;
}

const CONCEPT_PREFIX = "concept:";

export function Markdown({ body, onConceptLink }: MarkdownProps) {
  return (
    <div className="md-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children, ...rest }: ComponentPropsWithoutRef<"a">) {
            if (href && href.startsWith(CONCEPT_PREFIX)) {
              const conceptId = href.slice(CONCEPT_PREFIX.length);
              return (
                <a
                  href={href}
                  onClick={(e) => {
                    e.preventDefault();
                    onConceptLink(conceptId);
                  }}
                  style={{
                    color: "#1d4ed8",
                    textDecoration: "underline",
                    cursor: "pointer",
                  }}
                >
                  {children}
                </a>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" {...rest}>
                {children}
              </a>
            );
          },
          code({ children, ...rest }: ComponentPropsWithoutRef<"code">) {
            return (
              <code
                style={{
                  background: "#f1f5f9",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontSize: 16,
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                }}
                {...rest}
              >
                {children}
              </code>
            );
          },
        }}
      >
        {body}
      </ReactMarkdown>
    </div>
  );
}
