import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, Square, Check, RefreshCcw, Volume2 } from 'lucide-react';
import { cn, getDirectDriveUrl } from '../lib/utils';

import type { MediaItem } from '../types';

interface RecordingTaskProps {
  prompt: string;
  instructions: string;
  mediaItems?: MediaItem[];
  preAudio?: string | null;
  processedUrl?: string | null;
  onComplete: (blob: Blob) => void;
}

export const RecordingTask: React.FC<RecordingTaskProps> = ({ prompt, instructions, mediaItems, preAudio, processedUrl, onComplete }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [isPlayingPre, setIsPlayingPre] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const preAudioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    if (preAudio || processedUrl) {
      const url = getDirectDriveUrl(processedUrl || preAudio!);
      console.log("RecordingTask pre-audio (refined):", url);
      const audio = new Audio();
      if (url.includes('google.com')) {
        // Skip strict type setting for Drive links to avoid clash with sniffed types on redirect
      }
      audio.src = url;
      audio.preload = "auto";
      preAudioRef.current = audio;
      audio.onplay = () => setIsPlayingPre(true);
      audio.onended = () => setIsPlayingPre(false);
      audio.onloadstart = () => console.log("RecordingTask audio load start for:", url);
      audio.onerror = (e: any) => {
        const err = audio.error;
        console.warn("RecordingTask audio error details:", {
          code: err?.code,
          message: err?.message,
          event: e
        });
        
        // Retry logic for Google domain swap and confirm=t bypass - only 1 retry
        if (url.includes('google.com') && !url.includes('retried=true')) {
           const baseUrl = url.includes('docs.google.com') 
             ? url.replace('docs.google.com', 'drive.google.com')
             : url.replace('drive.google.com', 'docs.google.com');
           
           const connector = baseUrl.includes('?') ? '&' : '?';
           const altUrl = `${baseUrl}${baseUrl.includes('confirm=') ? '' : connector + 'confirm=t'}${baseUrl.includes('?') ? '&' : '?'}retried=true`;
           console.log("RecordingTask retrying with alternative configuration:", altUrl);
           audio.src = altUrl;
           audio.load();
           audio.play().catch(err => console.warn("Retry failed:", err));
           return;
        }

        setIsPlayingPre(false);
      };
      
      // Removed autoplay to comply with browser policies and user request.
      // User can now trigger audio via the "Play Guide" button.
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (preAudioRef.current) {
        preAudioRef.current.pause();
        preAudioRef.current = null;
      }
    };
  }, [preAudio, processedUrl]);

  const startRecording = async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      alert("Your browser does not support audio recording or is blocking it. Please try opening in a new tab or use a modern browser (Chrome/Edge/Safari).");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const url = URL.createObjectURL(blob);
        setAudioBlob(blob);
        setAudioUrl(url);
      };

      mediaRecorder.start();
      setIsRecording(true);
      setDuration(0);
      timerRef.current = window.setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } catch (err: any) {
      console.error("Mic access denied", err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        alert("Microphone access was denied. Please allow microphone access in your browser settings and try again.");
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        alert("No microphone found. Please connect a microphone and try again.");
      } else {
        alert("Microphone access error: " + err.message + ". Please try opening the app in a new tab.");
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="w-full space-y-8">
      <div className="relative overflow-hidden bg-[#0d1117] border border-white/5 rounded-[2.5rem] p-8 backdrop-blur-2xl shadow-[0_32px_64px_-16px_rgba(0,0,0,0.6)]">
        {/* Decorative background elements */}
        <div className="absolute -top-24 -left-24 w-64 h-64 bg-sky-500/10 rounded-full blur-[80px] pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-64 h-64 bg-indigo-500/10 rounded-full blur-[80px] pointer-events-none" />

        <div className="relative z-10 flex items-center gap-4 mb-8">
          <div className="w-12 h-12 rounded-2xl bg-sky-500/10 flex items-center justify-center border border-sky-500/20 shadow-inner">
            <Mic className="text-sky-500" size={24} />
          </div>
          <div>
            <h4 className="text-lg font-light tracking-tight text-white">{prompt}</h4>
            <div className="flex items-center gap-2 mt-1">
              <p className="text-slate-500 text-[10px] uppercase font-black tracking-[0.2em]">Section 2: Practical</p>
              {(preAudio || processedUrl) && (
                <button 
                  onClick={() => {
                    if (preAudioRef.current) {
                      preAudioRef.current.currentTime = 0;
                      preAudioRef.current.play().catch(e => console.warn("Manual play blocked:", e));
                    }
                  }}
                  className="flex items-center gap-2 ml-4 px-3 py-1 rounded-full bg-sky-500/10 border border-sky-500/20 hover:bg-sky-500/20 transition-all group"
                >
                  <Volume2 size={12} className={cn("text-sky-400", isPlayingPre && "animate-pulse")} />
                  <span className="text-sky-400 text-[9px] font-black uppercase tracking-widest">
                    {isPlayingPre ? 'Playing Guide' : 'Play Guide'}
                  </span>
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="relative z-10 bg-black/40 rounded-3xl p-8 mb-8 border border-white/5 text-[15px] text-slate-200 leading-relaxed font-medium shadow-inner">
          {instructions.split('\n').map((line, i) => (
            <p key={i} className="mb-2 last:mb-0">{line}</p>
          ))}
          
          {mediaItems?.filter(m => m.media_type === 'text' && m.text_content).map((item, idx) => (
            <div key={idx} className="mt-6 pt-6 border-t border-slate-800/50">
              <p className="text-[10px] uppercase tracking-[0.2em] font-black text-slate-500 mb-4 flex items-center gap-2">
                <span className="w-1 h-1 rounded-full bg-sky-500" />
                Target Passage
              </p>
              {item.text_content?.split('\n').map((line, i) => (
                <p key={i} className="mb-4 last:mb-0 font-light text-slate-200">{line}</p>
              ))}
            </div>
          ))}
        </div>

        <div className="relative z-10 flex flex-col items-center justify-center gap-4 py-8">
          <AnimatePresence mode="wait">
            {!audioUrl ? (
              <motion.div 
                key="recording-ui"
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex flex-col items-center gap-8"
              >
                <div className="relative group">
                  {isRecording && (
                    <motion.div
                      animate={{ scale: [1, 1.8, 1], opacity: [0.3, 0, 0.3] }}
                      transition={{ repeat: Infinity, duration: 2 }}
                      className="absolute inset-0 bg-red-500 rounded-full blur-3xl"
                    />
                  )}
                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                    className={cn(
                      "relative w-24 h-24 rounded-full flex items-center justify-center transition-all shadow-2xl active:scale-90 border-[6px] border-black/50 z-10 cursor-pointer overflow-hidden",
                      isRecording ? "bg-red-600 text-white" : "bg-white text-black hover:bg-slate-100"
                    )}
                  >
                    {isRecording ? (
                      <Square size={28} fill="currentColor" />
                    ) : (
                      <Mic size={32} className="group-hover:scale-110 transition-transform" />
                    )}
                  </button>
                </div>
                
                <div className="text-center">
                   <div className={cn("text-4xl font-mono mb-3 tracking-tighter", isRecording ? "text-red-500" : "text-slate-500")}>
                    {formatTime(duration)}
                   </div>
                   <p className="text-[10px] uppercase tracking-[0.4em] font-black text-slate-500">
                     {isRecording ? "Transcribing Voice" : "Tap to record answer"}
                   </p>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="playback-ui"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center gap-8 w-full max-w-sm"
              >
                 <div className="w-full bg-white/5 h-2 rounded-full overflow-hidden border border-white/5 shadow-inner">
                    <motion.div 
                      className="bg-sky-500 h-full shadow-[0_0_15px_rgba(14,165,233,0.6)]"
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                      transition={{ duration: 1.2, ease: "easeOut" }}
                    />
                 </div>
                 
                 <div className="flex items-center gap-4 w-full">
                    <button 
                      onClick={() => setAudioUrl(null)}
                      className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-slate-400 hover:bg-white/10 hover:text-white transition-all active:scale-90"
                    >
                      <RefreshCcw size={20} />
                    </button>
                    <button 
                      onClick={() => audioBlob && onComplete(audioBlob)}
                      className="flex-1 h-14 px-8 rounded-2xl bg-white text-black font-black text-xs uppercase tracking-widest flex items-center justify-center gap-3 hover:bg-sky-400 transition-all active:scale-95 shadow-[0_20px_40px_-12px_rgba(255,255,255,0.2)]"
                    >
                      <Check size={20} strokeWidth={3} />
                      Verify Capture
                    </button>
                 </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
      
      <div className="flex items-start gap-4 p-6 bg-sky-500/5 border border-sky-500/10 rounded-[2rem] relative overflow-hidden">
         <div className="absolute top-0 right-0 w-32 h-32 bg-sky-500/5 rounded-full blur-3xl pointer-events-none" />
         <Volume2 className="text-sky-500/60 shrink-0 mt-0.5" size={18} />
         <p className="text-[11px] text-slate-400 leading-relaxed font-medium">
           <span className="text-sky-400/80 font-black uppercase tracking-widest mr-2 underline decoration-sky-500/20 underline-offset-4">Security Protocol:</span>
           Manual recording verification is required for this module. Speak clearly and maintain professional posture for AI analysis.
         </p>
      </div>
    </div>
  );
};
