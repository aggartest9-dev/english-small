import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { Play, Volume2, SkipForward, Loader2 } from 'lucide-react';
import { getAI } from '../lib/gemini';
import { playPCMAudio } from '../lib/audioUtils';
import { Modality } from '@google/genai';
import { cn, getDirectDriveUrl } from '../lib/utils';

interface AIAvatarVideoProps {
  content: string;
  title: string;
  onComplete: () => void;
  estimatedSeconds?: number | null;
  preAudio?: string | null;
  processedUrl?: string | null;
  isImportant?: boolean;
}

export const AIAvatarVideo: React.FC<AIAvatarVideoProps> = ({ content, title, onComplete, estimatedSeconds, preAudio, processedUrl, isImportant }) => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [hasStarted, setHasStarted] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(0);
  const audioFinishedRef = useRef(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const handleVolume = (e: any) => setVolume(e.detail);
    window.addEventListener('avatar-volume', handleVolume);
    return () => window.removeEventListener('avatar-volume', handleVolume);
  }, []);

  useEffect(() => {
    // We removed auto-start narration to comply with browser autoplay policies and user request.
    // The user must now click "Play Narration" to begin.
  }, [content, preAudio, processedUrl]);

  const speak = async () => {
    if (isLoading) return;
    setIsLoading(true);
    setHasStarted(true);
    
    if (preAudio || processedUrl) {
      const audioUrl = getDirectDriveUrl(processedUrl || preAudio!);
      console.log("AIAvatar playing pre-recorded audio:", audioUrl);
      
      const audio = new Audio();
      
      const isDrive = audioUrl.includes('google.com');
      // CRITICAL: Google Drive does NOT support CORS headers for direct media access (uc?id=)
      // Including crossOrigin="anonymous" will cause the request to fail if it redirects.
      // We only use visualizer for non-Drive links.
      if (!isDrive) {
        audio.crossOrigin = "anonymous";
      }
      
      if (isDrive) {
        // We've found that setting explicit types for Drive redirects can sometimes cause MEDIA_ERR_SRC_NOT_SUPPORTED 
        // if the redirect response doesn't strictly match. Browsers are better at sniffing.
      }
      
      audio.src = audioUrl;
      audio.preload = "auto";
      audioPlayerRef.current = audio;

      // Debugging listeners
      audio.onstalled = () => console.warn("AIAvatar audio playback stalled");
      audio.onwaiting = () => console.log("AIAvatar audio waiting for data...");
      audio.oncanplaythrough = () => console.log("AIAvatar audio reached canplaythrough state");
      audio.onloadstart = () => console.log("AIAvatar audio starting to load source:", audioUrl);

      // Helper for simple playback when analyzer isn't used
      const setupSimplePlayback = (a: HTMLAudioElement) => {
        a.onplay = () => {
          setIsSpeaking(true);
          setIsLoading(false);
          const updateProgress = () => {
            if (!a.paused) {
              setProgress((a.currentTime / (a.duration || 1)) * 100);
              requestAnimationFrame(updateProgress);
            }
          };
          updateProgress();
        };
      };

      // Simple analyzer for visuals - ONLY for non-Drive links to avoid CORS issues
      if (!isDrive) {
        try {
          const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
          if (audioCtx.state === 'suspended') {
            audioCtx.resume();
          }
          const source = audioCtx.createMediaElementSource(audio);
          const analyzer = audioCtx.createAnalyser();
          analyzer.fftSize = 256;
          source.connect(analyzer);
          analyzer.connect(audioCtx.destination);

          const bufferLength = analyzer.frequencyBinCount;
          const dataArray = new Uint8Array(bufferLength);

          const updateVolume = () => {
            if (!audio.paused) {
              analyzer.getByteFrequencyData(dataArray);
              let sum = 0;
              for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
              }
              const average = sum / bufferLength / 255;
              setVolume(average);
              setProgress((audio.currentTime / (audio.duration || 1)) * 100);
              requestAnimationFrame(updateVolume);
            }
          };

          audio.onplay = () => {
            setIsSpeaking(true);
            setIsLoading(false);
            updateVolume();
          };
        } catch (analyserError) {
          console.warn("Visualizer failed initialization:", analyserError);
          setupSimplePlayback(audio);
        }
      } else {
        setupSimplePlayback(audio);
      }
      
      audio.onended = () => {
        setIsSpeaking(false);
        setVolume(0);
        audioFinishedRef.current = true;
      };

      audio.onerror = (e: any) => {
        const err = audio.error;
        console.error("Audio playback error details:", {
          code: err?.code,
          message: err?.message,
          event: e
        });
        
        // Retry logic for Google domain swap and confirm=t bypass - only 1 retry
        if (audioUrl.includes('google.com') && !audioUrl.includes('retried=true')) {
           const baseUrl = audioUrl.includes('docs.google.com') 
             ? audioUrl.replace('docs.google.com', 'drive.google.com')
             : audioUrl.replace('drive.google.com', 'docs.google.com');
           
           const connector = baseUrl.includes('?') ? '&' : '?';
           const altUrl = `${baseUrl}${baseUrl.includes('confirm=') ? '' : connector + 'confirm=t'}${baseUrl.includes('?') ? '&' : '?'}retried=true`;
           
           console.log("Retrying with alternative Google configuration:", altUrl);
           audio.src = altUrl;
           audio.load();
           audio.play().catch(err => console.warn("Retry failed:", err));
           return;
        }

        setIsLoading(false);
        setHasStarted(false); // Reset to show manual Play button on error
        audioFinishedRef.current = true;
      };

      // Ensure playback starts - browsers block autoplay without interaction
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        playPromise.then(() => {
          console.log("Audio started successfully");
        }).catch(e => {
          console.warn("Autoplay blocked or failed:", e);
          setIsLoading(false);
          setHasStarted(false); // This will show the manual play button
        });
      }
      return;
    }
    
    try {
      const ai = getAI();
      // Minimal prompt for maximum speed, focusing on clear teacher-like delivery
      const response = await ai.models.generateContent({
        model: "gemini-3.1-flash-tts-preview",
        contents: [{ parts: [{ text: `${content}` }] }],
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: {
              prebuiltVoiceConfig: { voiceName: 'Kore' },
            },
          },
        },
      });

      const base64Audio = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      
      if (base64Audio) {
        setIsLoading(false);
        setIsSpeaking(true);
        try {
          await playPCMAudio(base64Audio);
        } catch (playError) {
          console.error("PCM Play error:", playError);
        }
        setIsSpeaking(false);
        setVolume(0);
        audioFinishedRef.current = true;
      }
    } catch (error) {
      console.error("Narration error:", error);
      setIsLoading(false);
      setHasStarted(true);
      audioFinishedRef.current = true;
    }
  };

  useEffect(() => {
    let interval: any;
    if (isSpeaking && estimatedSeconds) {
      const step = 100 / (estimatedSeconds * 10);
      interval = setInterval(() => {
        setProgress(prev => Math.min(prev + step, 100));
      }, 100);
    }
    return () => clearInterval(interval);
  }, [isSpeaking, estimatedSeconds]);

  return (
    <div className="flex-1 flex flex-col items-center justify-center space-y-12 max-w-5xl mx-auto p-12 h-full relative overflow-hidden">
      {/* REACTIVE SONIC BACKGROUND */}
      <div className={cn(
        "absolute inset-0 -z-10 transition-all duration-1000",
        isImportant 
          ? "bg-[radial-gradient(ellipse_at_center,rgba(15,23,42,1)_0%,rgba(0,0,0,1)_100%)]" 
          : "bg-[radial-gradient(ellipse_at_top,rgba(15,23,42,1)_0%,rgba(0,0,0,1)_100%)]"
      )}>
        {/* Proper Background for Important Blocks (Intro/Outro) */}
        {isImportant && (
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-slate-950" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(56,189,248,0.15),transparent_50%),radial-gradient(circle_at_80%_70%,rgba(14,165,233,0.15),transparent_50%)]" />
            <motion.div 
               animate={{ 
                 opacity: [0.1, 0.2, 0.1],
                 scale: [1, 1.05, 1]
               }}
               transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
               className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/clean-gray-paper.png')] opacity-20 contrast-150 invert shadow-inner"
            />
          </div>
        )}

        <AnimatePresence>
          {isSpeaking && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: isImportant ? 0.3 : 0.15 }}
              exit={{ opacity: 0 }}
              className={cn(
                "absolute inset-0 transition-all duration-500",
                isImportant 
                  ? "bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.6)_0%,transparent_70%)]" 
                  : "bg-[radial-gradient(circle_at_center,rgba(56,189,248,0.3)_0%,transparent_70%)]"
              )}
              style={{ 
                scale: 1 + volume * (isImportant ? 1.0 : 0.4),
              }}
            />
          )}
        </AnimatePresence>
        
        {/* Particle Overlay for Important Blocks */}
        {isImportant && isSpeaking && (
          <div className="absolute inset-0 overflow-hidden pointer-events-none">
            {[...Array(20)].map((_, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: '100%' }}
                animate={{ 
                  opacity: [0, 0.5, 0],
                  y: '-10%',
                  x: `${Math.random() * 100}%`
                }}
                transition={{ 
                  duration: 2 + Math.random() * 3,
                  repeat: Infinity,
                  delay: Math.random() * 5
                }}
                className="absolute bottom-0 w-px h-20 bg-gradient-to-t from-transparent via-sky-500/20 to-transparent"
              />
            ))}
          </div>
        )}
      </div>

      {/* CENTRAL SONIC CORE */}
      <div className="relative flex flex-col items-center justify-center pt-8">
        <div className="absolute -z-10 w-64 h-64 bg-sky-500/5 rounded-full blur-3xl" />
        
        {/* Dynamic Visualizer Ring */}
        <motion.div 
          animate={{ rotate: 360 }}
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute w-48 h-48 border border-white/5 rounded-full"
        />

        {/* The Audio Orb */}
        <div className="relative w-32 h-32 flex items-center justify-center">
          <AnimatePresence mode="wait">
            {isSpeaking ? (
              <motion.div 
                key="speaking"
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ 
                  scale: 1 + volume * 0.4,
                  opacity: 1,
                  backgroundColor: `rgba(14, 165, 233, ${0.1 + volume * 0.2})`
                }}
                exit={{ scale: 0.8, opacity: 0 }}
                className="w-full h-full rounded-full border-2 border-sky-400/30 flex items-center justify-center backdrop-blur-sm shadow-[0_0_50px_rgba(14,165,233,0.2)]"
              >
                <div className="flex items-center gap-1.5">
                  {[...Array(5)].map((_, i) => (
                    <motion.div 
                      key={i}
                      animate={{ height: [`${20 + i*10}%`, `${60 + volume*80}%`, `${20 + i*10}%`] }}
                      transition={{ repeat: Infinity, duration: 0.3 + i*0.05 }}
                      className="w-1.5 bg-sky-400 rounded-full"
                    />
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="w-20 h-20 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center shadow-2xl"
              >
                <div className="relative">
                  <Volume2 size={32} className="text-slate-600" />
                  {hasStarted && <div className="absolute -top-1 -right-1 w-3 h-3 bg-sky-500 rounded-full animate-pulse" />}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        
        {/* Real-time Frequency Spectrum */}
        <div className="h-6 flex items-end gap-1 mt-8 opacity-30">
          {[...Array(32)].map((_, i) => (
            <motion.div 
              key={i}
              animate={{ 
                height: isSpeaking ? `${15 + (volume * 100 * Math.random())}%` : '2px',
              }}
              className="w-0.5 bg-sky-500 rounded-full"
            />
          ))}
        </div>
      </div>

      {/* CONTENT STAGE */}
      <motion.div 
        layout
        className="w-full bg-slate-950/40 border border-white/5 rounded-[3.5rem] p-16 md:p-24 shadow-2xl relative overflow-hidden backdrop-blur-xl"
      >
        <div className="flex flex-col items-center text-center">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-3 mb-12"
          >
            <div className={`w-2 h-2 rounded-full ${isSpeaking ? 'bg-sky-500 animate-pulse' : 'bg-slate-700'}`} />
            <span className="text-[10px] tracking-[0.5em] uppercase font-black text-slate-500">
              {isSpeaking ? 'Narrator Active' : 'Instructional Phase'}
            </span>
          </motion.div>

          <AnimatePresence mode="wait">
            <motion.div 
              key={content}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="max-w-4xl"
            >
              <h3 className="text-4xl md:text-5xl lg:text-6xl font-extralight leading-tight text-white tracking-tight">
                {content || "Analyzing curriculum..."}
              </h3>
            </motion.div>
          </AnimatePresence>

          {/* Prompt for next action */}
          <AnimatePresence>
            {!isSpeaking && hasStarted && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-20 flex items-center gap-4 text-sky-400"
              >
                <div className="w-16 h-px bg-sky-500/30" />
                <span className="text-[10px] font-black uppercase tracking-[0.4em]">Review complete. Proceed when ready.</span>
                <div className="w-16 h-px bg-sky-500/30" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* CONTROLS */}
      <div className="flex flex-col items-center gap-12 w-full">
        {!hasStarted ? (
          <button 
            onClick={speak}
            disabled={isLoading}
            className="group relative px-20 py-8 bg-white text-black rounded-3xl font-black text-sm uppercase tracking-[0.5em] hover:bg-sky-400 transition-all active:scale-95 shadow-[0_40px_100px_rgba(0,0,0,0.7)] flex items-center gap-4 overflow-hidden"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-sky-400/0 via-sky-400/10 to-sky-400/0 -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            {isLoading ? <Loader2 className="animate-spin" size={24} /> : <Volume2 size={24} />}
            Play Narration
          </button>
        ) : (
          <div className="flex flex-col items-center gap-12 w-full max-w-sm">
            {/* Minimal Progress Bar */}
            <div className="w-full space-y-4">
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-sky-500 shadow-[0_0_25px_rgba(14,165,233,0.8)]"
                  animate={{ width: `${progress}%` }}
                />
              </div>
            </div>
            
            <button 
              onClick={onComplete}
              className="group px-16 py-7 bg-slate-900/50 backdrop-blur-md text-white rounded-3xl font-black text-[10px] uppercase tracking-[0.5em] hover:bg-white hover:text-black transition-all active:scale-95 flex items-center gap-4 border border-white/5 shadow-2xl"
            >
              <SkipForward size={22} className="group-hover:translate-x-1 transition-transform" />
              Continue to Practice
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
