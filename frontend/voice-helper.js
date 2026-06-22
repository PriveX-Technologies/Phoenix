export function createSpeechRecognition(onResult, onState) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  recognition.maxAlternatives = 1;

  recognition.onstart = () => onState('listening');
  recognition.onspeechstart = () => onState('hearing');
  recognition.onspeechend = () => onState('processing');
  recognition.onend = () => onState('idle');
  recognition.onerror = e => onState('error:' + e.error);
  recognition.onresult = event => {
    const transcript = event.results[0][0].transcript.trim();
    onResult(transcript);
  };

  return recognition;
}
