import { useEffect, useRef, useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import OnboardingWizard from "./components/OnboardingWizard";
import TranscribePage from "./pages/TranscribePage";
import HistoryPage from "./pages/HistoryPage";
import TranscriptView from "./pages/TranscriptView";
import SettingsPage from "./pages/SettingsPage";
import { getOnboardingStatus } from "./api/client";
import Modal from "./components/Modal";
import { BTN_MAIN, Card, LauncherQuestion, RemovalAfterReload, TerminalFlow } from "./components/MacCards";
import {
  desktop,
  engineRunningNow,
  isDoomed,
  MARK_PROBLEM,
  MARK_PROBLEM_EVENT,
  markAsked,
  noteAtLoad,
  resolveRemoval,
  session,
  useEngineStatus,
} from "./desktop";
import type { FirstLaunch, LauncherStatus, MarkProblem, Removal } from "./desktop";

/**
 * Wizard trigger: on app mount, ask the backend whether onboarding has been
 * completed. If not, and the user hasn't previously dismissed the wizard, pop
 * it. A global ``window.openOnboarding()`` escape hatch lets Settings reopen
 * the wizard manually.
 */
export default function App() {
  const [showWizard, setShowWizard] = useState(false);
  // Bumped when the wizard closes so the Transcribe page reloads the config
  // the wizard just saved (it mounted behind the wizard with the old one).
  const [configVersion, setConfigVersion] = useState(0);
  // Mac app only: has the wizard question been settled, and the app's two
  // one-time questions (old launcher first, then Terminal) with what they need.
  const [wizardDecided, setWizardDecided] = useState(
    () => localStorage.getItem("scribe_onboarding_dismissed") === "1"
  );
  const [asked, setAsked] = useState<FirstLaunch | null>(null);
  const [launcher, setLauncher] = useState<LauncherStatus | null>(null);
  // a removal this page started before the engine restart reloaded it
  const [removed, setRemoved] = useState<Removal | null>(null);

  useEffect(() => {
    const dismissed = localStorage.getItem("scribe_onboarding_dismissed") === "1";
    if (dismissed) return;
    getOnboardingStatus()
      .then((s) => {
        if (!s.completed) setShowWizard(true);
      })
      .catch(() => {
        // Backend unreachable — wizard stays closed rather than blocking.
      })
      .finally(() => setWizardDecided(true));
  }, []);

  useEffect(() => {
    if (!desktop) return;
    Promise.all([desktop.firstLaunch.get(), desktop.oldLauncher.status()])
      .then(([a, l]) => {
        setLauncher(l);
        setAsked(a);
      })
      .catch(() => undefined); // unanswered questions wait for the next launch
  }, []);

  // A removal this page's predecessor started: only the note present when this page loaded
  // (noteAtLoad), settled against the app's saved lastRemoval on the first status that reads
  // running. A doomed page (the engine left running since; the app will reload it) does nothing.
  // The Terminal card waits for this, or starts at once when there was no note (H3).
  const engine = useEngineStatus();
  const settled = useRef(false);
  const [removalChecked, setRemovalChecked] = useState(!noteAtLoad);
  useEffect(() => {
    if (!desktop || !noteAtLoad || engine?.state !== "running" || settled.current) return;
    settled.current = true;
    const at = noteAtLoad.at;
    desktop.oldLauncher
      .status()
      .then((l) => {
        if (isDoomed()) return; // the reloaded page settles it; the Terminal card stays held here
        const r = resolveRemoval(l, engineRunningNow(), true, at);
        if (r && r !== "refused") setRemoved(r);
        setRemovalChecked(true);
      })
      .catch(() => setRemovalChecked(!isDoomed()));
  }, [engine?.state]);

  const askLauncher = !!asked && !asked.oldLauncherAsked && !!launcher?.installed;
  const askTerminal = !!asked && !asked.terminalAsked && !askLauncher && !removed && removalChecked;
  const terminalAnswered = () => {
    void markAsked("terminalAsked");
    setAsked((a) => a && { ...a, terminalAsked: true });
  };
  // Each question is asked once (the owner's answer): Escape or a click outside is the quiet
  // answer, Keep both or Skip for now.
  const launcherKept = () => {
    void markAsked("oldLauncherAsked");
    setAsked((a) => a && { ...a, oldLauncherAsked: true });
  };
  // An answer the app couldn't save (firstLaunch.mark said so): shown once things are quiet.
  const [markProblem, setMarkProblem] = useState<MarkProblem | null>(() => session.get<MarkProblem>(MARK_PROBLEM));
  useEffect(() => {
    const show = () => setMarkProblem(session.get<MarkProblem>(MARK_PROBLEM));
    window.addEventListener(MARK_PROBLEM_EVENT, show);
    return () => window.removeEventListener(MARK_PROBLEM_EVENT, show);
  }, []);
  const markProblemSeen = () => {
    session.del(MARK_PROBLEM);
    setMarkProblem(null);
  };

  // Escape hatch: let any component (Settings page) reopen the wizard.
  useEffect(() => {
    (window as unknown as { openOnboarding?: () => void }).openOnboarding = () => {
      localStorage.removeItem("scribe_onboarding_dismissed");
      setShowWizard(true);
    };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<TranscribePage key={configVersion} />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="history/:id" element={<TranscriptView />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
      {removed && (
        <Modal onClose={() => setRemoved(null)} ariaLabel="The old browser launcher" size="lg">
          <RemovalAfterReload initial={removed} onDone={() => setRemoved(null)} />
        </Modal>
      )}
      {askLauncher && launcher && (
        <Modal onClose={launcherKept} ariaLabel="The old browser launcher" size="lg">
          <LauncherQuestion
            status={launcher}
            onDone={() => setAsked((a) => a && { ...a, oldLauncherAsked: true })}
          />
        </Modal>
      )}
      {askTerminal && wizardDecided && !showWizard && (
        <Modal onClose={terminalAnswered} ariaLabel="Terminal and Claude Code" size="lg">
          <TerminalFlow eyebrow="One more option" onDone={terminalAnswered} />
        </Modal>
      )}
      {markProblem && !removed && !askLauncher && !(askTerminal && wizardDecided) && !showWizard && (
        <Modal onClose={markProblemSeen} ariaLabel="Your answer wasn't saved" size="md">
          <Card tone="warn" title="anyscribe couldn't save your answer">
            <p>{markProblem.reason}</p>
            <p>
              {markProblem.keys.length > 1
                ? "These questions may come back the next time anyscribe starts."
                : markProblem.keys[0] === "terminalAsked"
                  ? "The Terminal question may come back the next time anyscribe starts."
                  : "The old launcher question may come back the next time anyscribe starts."}
            </p>
            <div className="flex gap-2 pt-1">
              <button autoFocus onClick={markProblemSeen} className={BTN_MAIN}>OK</button>
            </div>
          </Card>
        </Modal>
      )}
      {showWizard && !askLauncher && (
        <OnboardingWizard
          offerTerminal={askTerminal ? terminalAnswered : undefined}
          onClose={() => {
            setShowWizard(false);
            // no separate Terminal card right after the wizard; it waits for the next launch
            setAsked((a) => a && { ...a, terminalAsked: true });
            setConfigVersion((v) => v + 1);
          }}
        />
      )}
    </BrowserRouter>
  );
}
