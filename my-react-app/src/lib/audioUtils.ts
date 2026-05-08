/**
 * Plays base64 encoded 16-bit PCM audio at a specific sample rate.
 */
export async function playPCMAudio(base64: string, sampleRate: number = 24000): Promise<void> {
  try {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // PCM 16-bit
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) {
      console.error("AudioContext not supported");
      return;
    }
    
    const audioContext = new AudioContextClass();
    const floatData = new Float32Array(bytes.length / 2);
    const dataView = new DataView(bytes.buffer);
    
    for (let i = 0; i < floatData.length; i++) {
      // 16-bit signed PCM to float [-1, 1]
      // Gemini TTS returns little-endian PCM
      const pcm = dataView.getInt16(i * 2, true);
      floatData[i] = pcm / 32768;
    }
    
    const buffer = audioContext.createBuffer(1, floatData.length, sampleRate);
    buffer.copyToChannel(floatData, 0);
    
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    
    // Volume analysis
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    analyser.connect(audioContext.destination);
    
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const updateVolume = () => {
      if (audioContext.state === 'closed') return;
      analyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      const average = sum / dataArray.length;
      
      // Dispatch a custom event or a callback if provided
      window.dispatchEvent(new CustomEvent('avatar-volume', { detail: average / 128 }));
      
      requestAnimationFrame(updateVolume);
    };
    updateVolume();
    
    return new Promise<void>((resolve) => {
      source.onended = () => {
        audioContext.close();
        resolve();
      };
      source.start();
    });
  } catch (error) {
    console.error("Error playing audio:", error);
    throw error;
  }
}
