/**
 * Audio Recorder Module
 * Captures microphone audio for Speech-to-Text processing.
 */

class AudioRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.stream = null;
    this.isRecording = false;
    this.onAudioReady = null;
  }

  /**
   * Request microphone access and initialize.
   */
  async init() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      console.log('[Audio] Microphone access granted');
      return true;
    } catch (e) {
      console.error('[Audio] Microphone access denied:', e);
      return false;
    }
  }

  /**
   * Start recording audio.
   */
  startRecording() {
    if (!this.stream || this.isRecording) return;

    this.audioChunks = [];
    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType: this._getSupportedMimeType(),
    });

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.onstop = () => {
      this._processRecording();
    };

    this.mediaRecorder.start(100); // Collect data every 100ms
    this.isRecording = true;
    console.log('[Audio] Recording started');
  }

  /**
   * Stop recording and process audio.
   */
  stopRecording() {
    if (!this.mediaRecorder || !this.isRecording) return;

    this.mediaRecorder.stop();
    this.isRecording = false;
    console.log('[Audio] Recording stopped');
  }

  /**
   * Process recorded audio and convert to base64 PCM.
   */
  async _processRecording() {
    const blob = new Blob(this.audioChunks, { type: 'audio/webm' });

    try {
      // Decode to raw PCM using AudioContext
      const arrayBuffer = await blob.arrayBuffer();
      const audioContext = new AudioContext({ sampleRate: 16000 });
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

      // Get mono channel data
      const channelData = audioBuffer.getChannelData(0);

      // Convert float32 to int16
      const int16Data = new Int16Array(channelData.length);
      for (let i = 0; i < channelData.length; i++) {
        const s = Math.max(-1, Math.min(1, channelData[i]));
        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      // Convert to base64
      const uint8Array = new Uint8Array(int16Data.buffer);
      let binary = '';
      for (let i = 0; i < uint8Array.length; i++) {
        binary += String.fromCharCode(uint8Array[i]);
      }
      const base64 = btoa(binary);

      await audioContext.close();

      if (this.onAudioReady) {
        this.onAudioReady(base64);
      }
    } catch (e) {
      console.error('[Audio] Processing error:', e);
    }
  }

  /**
   * Get supported MIME type.
   */
  _getSupportedMimeType() {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ];
    return types.find((type) => MediaRecorder.isTypeSupported(type)) || '';
  }

  /**
   * Release microphone.
   */
  destroy() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.isRecording = false;
  }
}

export default AudioRecorder;
