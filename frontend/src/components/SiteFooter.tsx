export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-ink-200/70 bg-white/70">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 text-sm text-ink-500 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
        <div>
          © 2026 Atlas Conference (a fictional event for portal demos).
        </div>
        <div className="flex items-center gap-4">
          <span className="hidden sm:inline">June 9–11, 2026</span>
          <span className="hidden sm:inline">·</span>
          <span>Moscone West, San Francisco</span>
        </div>
      </div>
    </footer>
  );
}
