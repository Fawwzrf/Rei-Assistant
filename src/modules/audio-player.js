/**
 * Audio Player Module
 * Plays TTS audio responses and provides amplitude data for lip-sync.
 */

class AudioPlayer {
  constructor() {
    this.audioContext = null;
    this.analyser = null;
    this.sourceNode = null;
    this.isPlaying = false;
    this.queue = [];
    this.onAmplitude = null; // callback(amplitude: 0-1)
    this.onPlayEnd = null;
    this.onPlayStart = null; // callback(text)
    this._animFrame = null;
  }

  /**
   * Initialize AudioContext and AnalyserNode.
   */
  init() {
    if (this.audioContext) return;

    this.audioContext = new AudioContext();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    this.analyser.smoothingTimeConstant = 0.5;
    this.analyser.connect(this.audioContext.destination);
  }

  /**
   * Queue audio and text for sequential playback.
   */
  enqueue(base64Audio, textContent) {
    this.queue.push({ bg64: base64Audio, text: textContent });
    if (!this.isPlaying) {
      this._playNext();
    }
  }

  /**
   * Play the next item in the queue.
   */
  async _playNext() {
    if (this.queue.length === 0) {
      this.isPlaying = false;
      this._stopAmplitudeTracking();
      if (this.onPlayEnd) this.onPlayEnd();
      return;
    }

    this.isPlaying = true;
    const item = this.queue.shift();

    // Trigger onPlayStart so text is appended exactly when audio starts
    if (this.onPlayStart && item.text) {
      this.onPlayStart(item.text);
    }

    if (!item.bg64) {
      // If no audio (tts failed), just skip to next
      this._playNext();
      return;
    }

    this.init();
    this._stopCurrentNode();

    try {
      // Decode base64 to ArrayBuffer
      const binaryString = atob(item.bg64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Decode WAV to AudioBuffer
      const audioBuffer = await this.audioContext.decodeAudioData(
        bytes.buffer.slice(0)
      );

      // Create source and connect to analyser
      this.sourceNode = this.audioContext.createBufferSource();
      this.sourceNode.buffer = audioBuffer;
      this.sourceNode.connect(this.analyser);

      this.sourceNode.onended = () => {
        this._stopCurrentNode();
        this._playNext(); // Proceed to next sentence
      };

      // Start playback
      this.sourceNode.start(0);

      // Start tracking amplitude for lip-sync
      this._startAmplitudeTracking();
    } catch (e) {
      console.error('[AudioPlayer] Playback error:', e);
      this._playNext();
    }
  }

  /**
   * Stop current audio node without terminating the whole queue state
   */
  _stopCurrentNode() {
    if (this.sourceNode) {
      try {
        this.sourceNode.onended = null;
        this.sourceNode.stop();
      } catch (e) {
        // Already stopped
      }
      this.sourceNode = null;
    }
  }

  /**
   * Stop completely and clear queue.
   */
  stop() {
    this.queue = [];
    this._stopCurrentNode();
    this.isPlaying = false;
    this._stopAmplitudeTracking();
  }

  /**
   * Start tracking audio amplitude for lip-sync.
   */
  _startAmplitudeTracking() {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

    const track = () => {
      if (!this.isPlaying) return;

      this.analyser.getByteFrequencyData(dataArray);

      // Calculate average amplitude (focus on voice frequencies: 85-255 Hz ≈ bins 1-10)
      let sum = 0;
      const voiceBins = Math.min(20, dataArray.length);
      for (let i = 1; i <= voiceBins; i++) {
        sum += dataArray[i];
      }
      const amplitude = (sum / voiceBins) / 255;

      // Emit amplitude with slight scaling for more visible lip movement
      if (this.onAmplitude) {
        this.onAmplitude(Math.min(1, amplitude * 1.8));
      }

      this._animFrame = requestAnimationFrame(track);
    };

    track();
  }

  /**
   * Stop amplitude tracking.
   */
  _stopAmplitudeTracking() {
    if (this._animFrame) {
      cancelAnimationFrame(this._animFrame);
      this._animFrame = null;
    }

    // Reset amplitude to 0
    if (this.onAmplitude) {
      this.onAmplitude(0);
    }
  }

  /**
   * Cleanup.
   */
  destroy() {
    this.stop();
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

export default AudioPlayer;
