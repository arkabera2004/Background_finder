import Link from "next/link";

/**
 * Brand mark ported from Chronos (mriganko da/Chronos): the orange clock
 * tile. The wordmark is set live in the display face rather than reusing
 * Chronos's own lettering, since that SVG literally spells "Chronos".
 */
export function Logo({
  wordmark = false,
  className = "",
  href = "/",
}: {
  wordmark?: boolean;
  className?: string;
  href?: string | false;
}) {
  const mark = (
    <>
      <img
        src="/brand/mark.svg"
        alt=""
        width={32}
        height={32}
        className="size-8 shrink-0 rounded-[10px]"
      />
      {wordmark ? (
        <span className="font-display text-base tracking-tight text-primary">ProspectLens</span>
      ) : null}
    </>
  );

  const frame = `flex min-w-0 items-center gap-2.5 ${className}`;

  if (!href) {
    return <span className={frame}>{mark}</span>;
  }

  return (
    <Link
      href={href}
      aria-label="ProspectLens home"
      className={`${frame} outline-none focus-visible:ring-2 focus-visible:ring-active`}
    >
      {mark}
    </Link>
  );
}
