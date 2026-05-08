/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { ContentSession } from "./types";
import type { Question } from "./types";
import { apiService } from "./services/apiService";

import { VideoSession } from "./components/VideoSession";
import { RecordingTask } from "./components/RecordingTask";
import { AIAvatarVideo } from "./components/AIAvatarVideo";

type Step = "start" | "video" | "interstitial" | "practice" | "commitment" | "finish";

export default function App() {
  const [session, setSession] = useState<ContentSession | null>(null);
  const [loading, setLoading] = useState(true);

  const [currentBlockIndex, setCurrentBlockIndex] = useState(-1);
  const [progress, setProgress] = useState(0);

  const [answers, setAnswers] = useState<Record<number, any>>({});
  const [commitment, setCommitment] = useState("");

  // ---------- INIT ----------
  useEffect(() => {
    if (navigator.mediaDevices?.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        stream.getTracks().forEach((t) => t.stop());
      }).catch(() => {});
    }

    loadSession();
  }, []);

  const loadSession = async () => {
    try {
      const data = await apiService.getSession("beginner",1);
      setSession({
        ...data,
         blocks: data.blocks || [],
        });
    } catch (err) {
      console.error("Failed to load session:", err);
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  // ---------- HANDLERS ----------
  const handleQuestionAnswered = (question: Question, answer: any) => {
    setAnswers((prev) => ({ ...prev, [question.id]: answer }));
  };

  const updateProgress = (index: number) => {
  const total = session?.blocks?.length || 0;
  if (total === 0) return;

  setProgress(((index + 1) / total) * 100);
  };

  const nextBlock = () => {
  const blocks = session?.blocks || [];
  if (blocks.length === 0) return;

  const nextIndex = currentBlockIndex + 1;

  if (nextIndex < blocks.length) {
    setCurrentBlockIndex(nextIndex);
    updateProgress(nextIndex);
  } else {
    setCurrentBlockIndex(blocks.length);
    setProgress(100);
  }
};

  const currentBlock =
    session &&
    currentBlockIndex >= 0 &&
    currentBlockIndex < (session?.blocks?.length || 0)
      ? session.blocks[currentBlockIndex]
      : null;

  // ---------- LOADING ----------
  if (loading) {
    return (
      <div style={styles.center}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1 }}
          style={styles.loader}
        />
      </div>
    );
  }

  // ---------- UI ----------
  return (
    <div style={styles.app}>
      {/* LEFT SIDEBAR */}
      <aside style={styles.sidebar}>
        <h2 style={styles.smallText}>Module</h2>
        <h1 style={styles.title}>
          Day {session?.day}: {session?.title}
        </h1>
        <p style={styles.desc}>{session?.description}</p>

        <div style={styles.progressBar}>
          <div style={{ ...styles.progressFill, width: `${progress}%` }} />
        </div>
      </aside>

      {/* MAIN */}
      <main style={styles.main}>
        <AnimatePresence mode="wait">
          {/* START SCREEN */}
          {currentBlockIndex === -1 && (
            <motion.div
              key="start"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={styles.center}
            >
              <button style={styles.button} onClick={nextBlock}>
                Start Workshop
              </button>
            </motion.div>
          )}

          {/* BLOCK RENDER */}
          {currentBlock && (
            <motion.div
              key={currentBlock.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={styles.block}
            >
              {currentBlock.block_type === "ai_message" && (
                <AIAvatarVideo
                  title={currentBlock.title}
                  content={currentBlock.text_content}
                  estimatedSeconds={currentBlock.estimated_seconds}
                  preAudio={currentBlock.preAudio}
                  processedUrl={currentBlock.processed_url}
                  onComplete={nextBlock}
                />
              )}

              {currentBlock.block_type === "video_lesson" && (
                <VideoSession
                  videoUrl={currentBlock.media_items?.[0]?.file_url || ""}
                  questions={currentBlock.questions}
                  onQuestionAnswered={handleQuestionAnswered}
                  onComplete={nextBlock}
                />
              )}

              {currentBlock.block_type === "speaking_task" && (
                <RecordingTask
                  prompt={currentBlock.description}
                  instructions={currentBlock.text_content}
                  mediaItems={currentBlock.media_items}
                  onComplete={(blob) => {
                    setAnswers((p) => ({ ...p, [currentBlock.id]: blob }));
                    nextBlock();
                  }}
                />
              )}

              {currentBlock.block_type === "commitment_task" && (
                <div style={styles.commitBox}>
                  <textarea
                    value={commitment}
                    onChange={(e) => setCommitment(e.target.value)}
                    placeholder="Write your commitment..."
                    style={styles.textarea}
                  />

                  <button
                    style={styles.button}
                    onClick={async () => {
                      try {
                        await apiService.submitCommitment(commitment);
                        nextBlock();
                      } catch (err) {
                        console.error("Commit failed:", err);
                      }
                    }}
                  >
                    Finish
                  </button>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

// ---------- SIMPLE INLINE STYLES ----------
const styles: Record<string, React.CSSProperties> = {
  app: {
    display: "flex",
    height: "100vh",
    background: "#050505",
    color: "#fff",
    fontFamily: "sans-serif",
  },
  sidebar: {
    width: 280,
    padding: 20,
    borderRight: "1px solid #222",
  },
  main: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  block: {
    width: "100%",
    maxWidth: 800,
  },
  center: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
  },
  title: { fontSize: 22, marginBottom: 10 },
  smallText: { fontSize: 12, opacity: 0.6 },
  desc: { fontSize: 14, opacity: 0.7 },
  button: {
    padding: "12px 20px",
    background: "#fff",
    color: "#000",
    border: "none",
    borderRadius: 8,
    cursor: "pointer",
    fontWeight: 600,
  },
  textarea: {
    width: "100%",
    height: 120,
    padding: 10,
    borderRadius: 8,
    border: "1px solid #333",
    background: "#111",
    color: "#fff",
  },
  commitBox: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  progressBar: {
    height: 6,
    background: "#222",
    marginTop: 20,
    borderRadius: 10,
  },
  progressFill: {
    height: "100%",
    background: "#4ade80",
    transition: "width 0.3s",
  },
  loader: {
    width: 40,
    height: 40,
    border: "4px solid #444",
    borderTop: "4px solid #4ade80",
    borderRadius: "50%",
  },
};