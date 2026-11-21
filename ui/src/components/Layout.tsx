import { useCallback, useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Mic, Clock, Settings, Waves, Power, Share2, FileAudio } from "lucide-react";
import SetupBanner from "./SetupBanner";
import EngineBanner from "./EngineBanner";
import { desktop, isMac, session } from "../desktop";
import { TailnetLink } from "./TailnetShare";
import { REMOTE, useTailnet } from "../hooks/useTailnet";

/** What the Transcribe page gets from the layout (Mac app: files dropped or opened with the app). */
export type LayoutContext = {
  incoming: string[];
  /** The engine accepted the file at the head of the queue (or he chose New on its error): it leaves. */
  doneIncoming: (path: string) => void;
  /** The job the page is following, so the engine banner can name it after a restart. */
  setWatching: (job: string | null) => void;
};

// Files waiting to be transcribed, kept in sessionStorage: the app acknowledges an opened file as
// soon as the callback returns (preload), and reloads this page whenever the engine comes back.
const QUEUE = "anyscribe_incoming";

/** Mac app only: files dragged onto the window or opened with the app become paths to transcribe. */
function useIncomingFiles() {
  const navigate = useNavigate();
  const [incoming, setIncoming] = useState<string[]>(() => session.get<string[]>(QUEUE) ?? []);
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0);

  const add = useCallback(
    (paths: string[]) => {
      if (!paths.length) return;
      // stored before this callback returns, so a reload after the app's acknowledgement keeps them
      const q = [...(session.get<string[]>(QUEUE) ?? []), ...paths];
      session.set(QUEUE, q);
      setIncoming(q);
      navigate("/");
    },
    [navigate]
  );

  useEffect(() => {
    if (!desktop) return;
    const bridge = desktop;
    const hasFiles = (e: DragEvent) => !!e.dataTransfer?.types.includes("Files");
    const enter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth.current += 1;
      setDragging(true); // a browser gives the file's name only on the drop (drag_probe.out)
    };
    const over = (e: DragEvent) => {
      if (hasFiles(e)) e.preventDefault(); // allows the drop
    };
    const leave = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      depth.current = Math.max(0, depth.current - 1);
      if (!depth.current) setDragging(false);
    };
    const drop = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault(); // never let the window navigate to the file
      depth.current = 0;
      setDragging(false);
      add(Array.from(e.dataTransfer?.files ?? []).map((f) => bridge.pathForFile(f)).filter(Boolean));
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragover", over);
    window.addEventListener("dragleave", leave);
    window.addEventListener("drop", drop);
    const off = bridge.onOpenFile((path) => add([path]));
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragover", over);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("drop", drop);
      off();
    };
  }, [add]);

  const doneIncoming = useCallback((path: string) => {
    const q = session.get<string[]>(QUEUE) ?? [];
    if (q[0] !== path) return; // only the head: a failed typed link never takes a waiting file
    q.shift();
    session.set(QUEUE, q);
    setIncoming(q);
  }, []);
  return { incoming, doneIncoming, dragging };
}

const NAV = [
  { to: "/", icon: Mic, label: "Transcribe" },
  { to: "/history", icon: Clock, label: "History" },
  { to: "/settings", icon: Settings, label: "Settings" },
] as const;

export default function Layout() {
  const [confirmShutdown, setConfirmShutdown] = useState(false);
  const [stopped, setStopped] = useState(false);
  const { state: tailnet } = useTailnet();
  const { incoming, doneIncoming, dragging } = useIncomingFiles();
  const watching = useRef<string | null>(null);
  const setWatching = useCallback((job: string | null) => {
    watching.current = job;
  }, []);

  const handleShutdown = async () => {
    try {
      await fetch("/api/shutdown", { method: "POST" });
    } catch {
      // Expected — server is shutting down
    }
    setStopped(true);
    // Try to close the tab (works if opened by JS, e.g. window.open)
    setTimeout(() => {
      window.close();
    }, 300);
  };

  if (stopped) {
    return (
      <div className="flex items-center justify-center min-h-dvh bg-bg">
        <div className="text-center">
          <Power className="w-8 h-8 text-text-muted mx-auto mb-3" />
          <p className="text-lg font-medium text-text mb-1">Server stopped</p>
          <p className="text-sm text-text-muted">You can close this tab.</p>
          <p className="text-xs text-text-muted mt-3">
            To reopen later, run <code className="font-mono">scribe ui</code> in your
            terminal — or click the anyscribe menu-bar icon, if installed.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row min-h-dvh">
      {/* Sidebar; on a phone it stacks above the page instead of eating its width */}
      <aside className="w-full sm:w-56 shrink-0 border-b sm:border-b-0 sm:border-r border-border-subtle bg-surface flex flex-col">
        {/* Mac app: the window's coloured buttons sit here; dragging this strip moves the window */}
        {isMac && <div className="app-drag h-7 shrink-0" />}
        {/* Logo */}
        <div className={`flex items-center gap-2.5 px-5 py-5 ${isMac ? "app-drag" : ""}`}>
          <Waves className="w-5 h-5 text-amber" />
          <span
            className="text-lg font-semibold tracking-tight text-text"
            style={{ fontFamily: "var(--font-display)" }}
          >
            anyscribe
          </span>
        </div>

        {/* Nav */}
        <nav className="flex flex-row flex-wrap sm:flex-col gap-0.5 px-3 sm:mt-2">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? "bg-surface-raised text-text font-medium"
                    : "text-text-secondary hover:text-text hover:bg-surface-hover"
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Tailnet indicator, under the nav so it is visible without scrolling on every page */}
        <div className="px-3 mt-4">
          {tailnet?.active && tailnet.url ? (
            <div className="rounded-lg border border-border-subtle bg-surface-raised px-2.5 py-2">
              <p className="flex items-center gap-1.5 text-xs text-text-secondary mb-0.5">
                <Share2 className="w-3 h-3 text-green" />
                Shared on your tailnet
              </p>
              <TailnetLink url={tailnet.url} compact />
            </div>
          ) : tailnet?.enabled && !tailnet.unknown && !(REMOTE && tailnet.held) ? (
            // Read over the held link, it plainly works: no failure line.
            <Link
              to="/settings"
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-red hover:bg-surface-hover"
            >
              <Share2 className="w-3 h-3" />
              {tailnet.held ? "Tailnet link isn't confirmed" : "Tailnet sharing isn't working"}
            </Link>
          ) : null}
        </div>

        {/* Bottom — branding + shutdown */}
        <div className="mt-4 sm:mt-auto px-3 pb-4 space-y-2">
          <div className="px-3 py-2 text-xs text-text-secondary space-y-1">
            <p>&copy; 2026 Rishabh Madaan</p>
            <a href="https://github.com/rishmadaan/anyscribe#license" target="_blank" rel="noopener noreferrer" className="block hover:text-text underline">
              AGPLv3 or later · no warranty
            </a>
            <a href="https://github.com/rishmadaan/anyscribe" target="_blank" rel="noopener noreferrer" className="hover:text-text underline">
              Source
            </a>
            {" · "}
            <a href="/THIRD-PARTY-LICENSES.md" target="_blank" rel="noopener noreferrer" className="hover:text-text underline">
              Third-party notices
            </a>
          </div>
          {/* KraftedX branding */}
          <a
            href="https://kraftedx.com"
            target="_blank"
            rel="noopener noreferrer"
            className="block px-3 py-1.5 opacity-20 hover:opacity-35 transition-opacity"
          >
            <img
              src="/kx-logo-white-128.png"
              alt="KraftedX"
              className="h-3.5 w-auto"
            />
          </a>

          {/* Shutdown (browser only: in the Mac app, quitting is the app's job) */}
          {desktop ? null : !confirmShutdown ? (
            <button
              onClick={() => setConfirmShutdown(true)}
              className="
                flex items-center gap-2 w-full px-3 py-2 rounded-lg
                text-xs text-text-muted hover:text-red hover:bg-surface-hover
                transition-colors cursor-pointer
              "
            >
              <Power className="w-3.5 h-3.5" />
              Shutdown
            </button>
          ) : (
            <div className="flex items-center gap-1.5">
              <button
                onClick={handleShutdown}
                className="
                  flex items-center gap-1.5 px-3 py-2 rounded-lg
                  text-xs text-red bg-red/5 border border-red/20
                  hover:bg-red/10 transition-colors cursor-pointer
                "
              >
                <Power className="w-3.5 h-3.5" />
                Shutdown?
              </button>
              <button
                onClick={() => setConfirmShutdown(false)}
                className="text-xs text-text-muted hover:text-text cursor-pointer px-2 py-2"
              >
                no
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto relative">
        <EngineBanner watching={watching} />
        <SetupBanner />
        <Outlet context={{ incoming, doneIncoming, setWatching } satisfies LayoutContext} />

        {dragging && (
          <div className="pointer-events-none fixed inset-3.5 sm:left-[calc(14rem+0.875rem)] z-50 grid place-items-center rounded-2xl border-2 border-dashed border-amber bg-[#1a140e]/90 text-center">
            <div className="flex flex-col items-center gap-1.5">
              <FileAudio className="w-6.5 h-6.5 text-amber" />
              <p className="font-semibold text-text">Drop to transcribe</p>
            </div>
          </div>
        )}

        {/* Decorative doodle — bottom of content area */}
        <div
          className="pointer-events-none fixed bottom-0 right-0 w-[calc(100%-14rem)] h-[50vh] bg-bottom bg-no-repeat opacity-[0.12] hidden md:block"
          style={{ backgroundImage: "url('/doodles-desktop-2.png')", backgroundSize: "100% auto" }}
        />
        <div
          className="pointer-events-none fixed bottom-0 right-0 w-[calc(100%-14rem)] h-[60vh] bg-bottom bg-no-repeat opacity-[0.12] md:hidden"
          style={{ backgroundImage: "url('/doodles-mobile-2.png')", backgroundSize: "100% auto" }}
        />
      </main>
    </div>
  );
}
