import React, { useState, useEffect, useRef } from 'react';
import YouTube from "react-youtube";
import type { YouTubeProps } from "react-youtube";
import { motion, AnimatePresence } from 'framer-motion';
import type { ContentSession, Question, ResponseType, QuestionFormat } from "../types";
import { cn, getDirectDriveUrl } from '../lib/utils';
import { Loader2, Play, Pause, RotateCcw, Volume2, CheckCircle2 } from 'lucide-react';

interface VideoSessionProps {
  videoUrl: string;
  questions: Question[];
  onQuestionAnswered: (question: Question, answer: any) => void;
  onComplete: () => void;
}

type QuestionStep = 'pre' | 'asking' | 'post' | 'feedback';

export const VideoSession: React.FC<VideoSessionProps> = ({ videoUrl, questions, onQuestionAnswered, onComplete }) => {
  const [player, setPlayer] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeQuestion, setActiveQuestion] = useState<Question | null>(null);
  const [questionStep, setQuestionStep] = useState<QuestionStep>('asking');
  const [answeredIds, setAnsweredIds] = useState<Set<number>>(new Set());
  const [selectedOptionId, setSelectedOptionId] = useState<number | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const timerRef = useRef<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Helper to play audio and return promise
  const playAudio = (url: string): Promise<void> => {
    return new Promise((resolve) => {
      console.log("VideoSession playing audio:", url);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      
      const directUrl = getDirectDriveUrl(url);
      console.log("VideoSession refined direct URL:", directUrl);
      const audio = new Audio();

      const isDrive = directUrl.includes('google.com');
      if (!isDrive) {
        audio.crossOrigin = "anonymous";
      }
      
      audio.src = directUrl;
      audio.preload = "auto";
      audioRef.current = audio;
      
      // Debug listeners
      audio.onloadstart = () => console.log("VideoSession audio load start for:", directUrl);
      audio.onplay = () => {
        console.log("VideoSession audio started playing successfully");
        setIsPlayingAudio(true);
      };
      
      const handleEnd = () => {
        console.log("VideoSession audio ended successfully");
        setIsPlayingAudio(false);
        resolve();
      };
      
      audio.onended = handleEnd;
      audio.onerror = (e: any) => {
        const err = audio.error;
        console.warn("VideoSession audio load error details:", {
          code: err?.code,
          message: err?.message,
          event: e
        });

        // Retry logic for Google domain swap and confirm=t bypass - only 1 retry
        if (directUrl.includes('google.com') && !directUrl.includes('retried=true')) {
           const baseUrl = directUrl.includes('docs.google.com') 
             ? directUrl.replace('docs.google.com', 'drive.google.com')
             : directUrl.replace('drive.google.com', 'docs.google.com');
           
           const connector = baseUrl.includes('?') ? '&' : '?';
           const altUrl = `${baseUrl}${baseUrl.includes('confirm=') ? '' : connector + 'confirm=t'}${baseUrl.includes('?') ? '&' : '?'}retried=true`;
           console.log("VideoSession retrying with alternative configuration:", altUrl);
           audio.src = altUrl;
           audio.load();
           audio.play().catch(err => console.warn("Retry failed:", err));
           return;
        }

        setIsPlayingAudio(false);
        // If error, resolve after a bit so user doesn't get stuck
        setTimeout(resolve, 3000); 
      };
      
      audio.play().catch((err) => {
        console.warn("VideoSession audio playback blocked:", err);
        // If blocked, we resolve to show the question (which now has a manual replay button)
        setIsPlayingAudio(false);
        setTimeout(resolve, 1000);
      });
    });
  };

  // Robust extraction for various YouTube URL formats
  const getYouTubeId = (url: string) => {
    const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
    const match = url.match(regExp);
    return (match && match[2].length === 11) ? match[2] : url;
  };

  const videoId = getYouTubeId(videoUrl);

  useEffect(() => {
    if (player) {
      timerRef.current = window.setInterval(() => {
        try {
          const time = player.getCurrentTime();
          const pState = player.getPlayerState();
          setCurrentTime(time);
          
          // FORCE PAUSE: If there's an active question, the video MUST be paused
          if (activeQuestion && pState === 1) { // 1 is Playing
            player.pauseVideo();
          }

          // Find if any question should be triggered at this time
          const triggerableQuestion = questions.find(q => {
            if (q.timestamp_start === null || answeredIds.has(q.id)) return false;
            const diff = time - q.timestamp_start;
            return diff >= 0 && diff < 1.5; 
          });

          if (triggerableQuestion && !activeQuestion) {
            player.pauseVideo();
            setActiveQuestion(triggerableQuestion);
            setQuestionStep('pre');
            
            // We NO LONGER auto-play pre-audio here.
            // The UI will show a "Start Listening" button in the 'pre' step.
          }
        } catch (e) {
          // Player not ready
        }
      }, 400); 
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [player, questions, answeredIds, activeQuestion]);

  const handleAnswer = async (answer: any) => {
    if (activeQuestion) {
      onQuestionAnswered(activeQuestion, answer);
      setAnsweredIds(prev => new Set(prev).add(activeQuestion.id));
      
      setQuestionStep('post');
      
      const postAudioUrl = activeQuestion.processed_post_url || activeQuestion.postAudio;
      if (postAudioUrl) {
        // Start playing the audio, but we don't await it to close automatically anymore
        playAudio(postAudioUrl);
      }
    }
  };

  const handleContinue = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setIsPlayingAudio(false);
    
    setActiveQuestion(null);
    setQuestionStep('asking');
    setSelectedOptionId(null);
    // Give a tiny delay before resuming to avoid potential race conditions
    setTimeout(() => player?.playVideo?.(), 100);
  };

  const onReady: YouTubeProps['onReady'] = (event) => {
    setPlayer(event.target);
  };

  const onStateChange: YouTubeProps['onStateChange'] = (event) => {
    // 0 is the ended state in YouTube IFrame API
    if (event.data === 0) {
      onComplete();
    }
  };

  const opts: YouTubeProps['opts'] = {
    height: '100%',
    width: '100%',
    playerVars: {
      autoplay: 0,
      controls: 1, 
      modestbranding: 1,
      rel: 0,
      iv_load_policy: 3,
      fs: 1,
      origin: window.location.origin
    },
  };

  return (
    <div className="relative w-full aspect-video bg-slate-900 rounded-3xl overflow-hidden shadow-2xl border border-slate-800 group">
      <YouTube
        videoId={videoId}
        opts={opts}
        onReady={onReady}
        onStateChange={onStateChange}
        className="w-full h-full"
        iframeClassName="w-full h-full"
      />
      
      {/* Subtle Video Progress Bar (Overlaying at the very bottom) */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-slate-800 z-10 pointer-events-none">
        <motion.div 
          className="h-full bg-sky-500 shadow-[0_0_8px_rgba(14,165,233,0.6)]"
          style={{ width: `${(currentTime / (player?.getDuration() || 1)) * 100}%` }}
        />
      </div>

      <AnimatePresence>
        {activeQuestion && (
          <motion.div
            initial={{ opacity: 0, scale: 1.1 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="absolute inset-0 bg-slate-950/98 backdrop-blur-xl z-20 flex flex-col items-center justify-center p-8 text-center"
          >
            <div className="max-w-[400px] w-full flex flex-col items-center">
               <motion.div
                 initial={{ y: 10, opacity: 0 }}
                 animate={{ y: 0, opacity: 1 }}
                 className="flex items-center gap-2 mb-6"
               >
                 <div className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" />
                 <span className="text-sky-400 text-[10px] font-bold uppercase tracking-[0.2em]">
                   {questionStep === 'pre' ? 'Introduction' : 
                    questionStep === 'post' ? 'Explanation' : 
                    'Active Challenge'}
                 </span>
               </motion.div>

               {questionStep === 'post' ? (
                 <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center"
                 >
                    <motion.div 
                      initial={{ scale: 0.5, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6 text-emerald-500"
                    >
                      <CheckCircle2 size={40} />
                    </motion.div>
                    <h3 className="text-xl font-medium text-white mb-4">Well Done!</h3>
                    <div className="max-h-[180px] overflow-y-auto mb-8 w-full custom-scrollbar">
                      <p className="text-slate-300 text-sm italic leading-relaxed text-center whitespace-pre-wrap">
                        {activeQuestion.explanation || "Correct! Let's listen to the explanation before moving on."}
                      </p>
                    </div>

                    <div className="flex flex-col gap-4 w-full">
                      {(activeQuestion.processed_post_url || activeQuestion.postAudio) && (
                        <button 
                          onClick={() => playAudio(activeQuestion.processed_post_url || activeQuestion.postAudio!)}
                          className="flex items-center justify-center gap-3 w-full px-6 py-4 bg-sky-500/10 border border-sky-500/20 rounded-2xl text-sky-400 hover:bg-sky-500/20 transition-all"
                        >
                          <Volume2 size={16} className={cn(isPlayingAudio ? "animate-pulse" : "")} />
                          <span className="text-[10px] uppercase tracking-widest font-black">
                            {isPlayingAudio ? 'Playing Explanation' : 'Replay Explanation'}
                          </span>
                        </button>
                      )}

                      <button
                        onClick={handleContinue}
                        className="w-full py-4 bg-white text-black rounded-2xl font-black text-[10px] uppercase tracking-[0.3em] active:scale-95 shadow-2xl transition-all"
                      >
                        Continue Lesson
                      </button>
                    </div>
                 </motion.div>
               ) : questionStep === 'pre' ? (
                 <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center"
                 >
                    <div className="w-16 h-16 rounded-full bg-sky-500/10 flex items-center justify-center mb-6 text-sky-500">
                      <Volume2 size={40} className="animate-bounce" />
                    </div>
                    <h3 className="text-xl font-medium text-white mb-8">Guided Context</h3>
                    <div className="flex flex-col gap-4 w-full px-4">
                      {!isPlayingAudio && (
                        <button 
                          onClick={() => {
                            const preAudioUrl = activeQuestion.processed_pre_url || activeQuestion.preAudio;
                            if (preAudioUrl) playAudio(preAudioUrl).then(() => setQuestionStep('asking'));
                          }}
                          className="flex items-center justify-center gap-3 w-full px-6 py-4 bg-sky-500 text-black rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-xl cursor-pointer"
                        >
                          <Play size={16} fill="currentColor" />
                          Start Listening
                        </button>
                      )}
                      <button 
                        onClick={() => setQuestionStep('asking')}
                        className="flex items-center justify-center gap-3 w-full px-6 py-4 bg-slate-900 border border-slate-800 text-slate-400 rounded-2xl font-bold text-[10px] uppercase tracking-widest opacity-60 cursor-pointer"
                      >
                        Skip Audio
                      </button>
                    </div>
                 </motion.div>
               ) : (
                 <>
                   <motion.h3 
                     initial={{ y: 10, opacity: 0 }}
                     animate={{ y: 0, opacity: 1 }}
                     transition={{ delay: 0.1 }}
                     className="text-lg font-light leading-snug mb-10 text-white"
                   >
                     {activeQuestion.text}
                   </motion.h3>

                   <div className="grid gap-3 w-full">
                     {activeQuestion.response_type === 'text' ? (
                       <div className="space-y-4">
                         <textarea
                           className="w-full h-32 p-4 bg-slate-900 border border-slate-800 rounded-2xl text-sm text-white resize-none focus:border-sky-500 outline-none"
                           placeholder="Type your response here..."
                           id="short-answer-input"
                         />
                         <button
                           onClick={() => {
                             const val = (document.getElementById('short-answer-input') as HTMLTextAreaElement)?.value;
                             if (val?.trim()) handleAnswer({ text_answer: val });
                           }}
                           className="w-full py-4 bg-white text-black rounded-2xl font-bold text-xs uppercase tracking-widest active:scale-95 shadow-xl"
                         >
                           Submit Answer
                         </button>
                       </div>
                     ) : (
                       <div className="space-y-4 w-full">
                         <div className="grid gap-3 w-full">
                           {activeQuestion.options.map((option, idx) => (
                             <motion.button
                               key={option.id}
                               initial={{ x: -10, opacity: 0 }}
                               animate={{ x: 0, opacity: 1 }}
                               transition={{ delay: 0.2 + idx * 0.05 }}
                               onClick={() => setSelectedOptionId(option.id)}
                               className={cn(
                                 "w-full p-4 rounded-2xl border border-slate-800 bg-slate-900/40 text-left text-[13px] transition-all active:scale-95 group flex items-center justify-between",
                                 selectedOptionId === option.id ? "border-sky-500 bg-sky-500/10" : "hover:bg-slate-800 hover:border-slate-700"
                               )}
                             >
                               <span className={cn(
                                 "font-normal leading-tight pr-4",
                                 selectedOptionId === option.id ? "text-sky-400" : "text-slate-200"
                               )}>{option.text}</span>
                               <div className={cn(
                                 "w-5 h-5 rounded-full border flex items-center justify-center shrink-0 transition-all duration-300",
                                 selectedOptionId === option.id ? "border-sky-500 bg-sky-500" : "border-slate-700 group-hover:border-sky-500"
                               )}>
                                 {selectedOptionId === option.id && <div className="w-1.5 h-1.5 rounded-full bg-white shadow-sm" />}
                               </div>
                             </motion.button>
                           ))}
                         </div>
                         <motion.button
                           initial={{ opacity: 0, y: 10 }}
                           animate={{ 
                             opacity: selectedOptionId ? 1 : 0.5, 
                             y: 0 
                           }}
                           onClick={() => {
                             if (selectedOptionId) {
                               handleAnswer({ selected_option_id: selectedOptionId });
                               setSelectedOptionId(null);
                             }
                           }}
                           disabled={!selectedOptionId}
                           className="w-full py-4 bg-white text-black rounded-2xl font-black text-[10px] uppercase tracking-[0.3em] active:scale-95 shadow-2xl transition-all"
                         >
                           Submit Answer
                         </motion.button>
                       </div>
                     )}
                   </div>
                 </>
               )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Manual UI overlay for play/pause if needed */}
      {!activeQuestion && player && (
        <div className="absolute bottom-6 left-6 z-10 flex items-center gap-3">
          <button 
            onClick={() => player.getPlayerState() === 1 ? player.pauseVideo() : player.playVideo()}
            className="w-12 h-12 flex items-center justify-center rounded-full bg-white/10 backdrop-blur-xl border border-white/20 hover:bg-white/20 transition-all"
          >
            {player.getPlayerState() === 1 ? <Pause size={20} /> : <Play size={20} className="ml-1" />}
          </button>
          <div className="px-4 py-2 bg-black/40 backdrop-blur-xl border border-white/10 rounded-full text-[10px] font-mono tracking-tighter uppercase text-white/60">
             Lesson Progress: {Math.floor((currentTime / player.getDuration()) * 100 || 0)}%
          </div>
        </div>
      )}
    </div>
  );
};
