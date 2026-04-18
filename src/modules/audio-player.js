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
    this.onAmplitude = null; // callback(amplitude: 0-1)
    this.onPlayEnd = null;
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
   * Play WAV audio from base64 string.
   */
  async play(base64Audio) {
    if (!base64Audio) return;

    this.init();

    // Stop any current playback
    this.stop();

    try {
      // Decode base64 to ArrayBuffer
      const binaryString = atob(base64Audio);
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
        this.isPlaying = false;
        this._stopAmplitudeTracking();
        if (this.onPlayEnd) this.onPlayEnd();
      };

      // Start playback
      this.sourceNode.start(0);
      this.isPlaying = true;

      // Start tracking amplitude for lip-sync
      this._startAmplitudeTracking();
    } catch (e) {
      console.error('[AudioPlayer] Playback error:', e);
      this.isPlaying = false;
    }
  }

  /**
   * Stop current playback.
   */
  stop() {
    if (this.sourceNode) {
      try {
        this.sourceNode.stop();
      } catch (e) {
        // Already stopped
      }
      this.sourceNode = null;
    }
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
