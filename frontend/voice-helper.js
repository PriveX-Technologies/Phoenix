export function createSpeechRecognition(onResult, onState) {
  console.log("voice-helper loaded");

  const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

  console.log("SpeechRecognition =", SpeechRecognition);

  if (!SpeechRecognition) {
    console.log("NO SPEECH API");
    return null;
  }

  const recognition = new SpeechRecognition();

  console.log("Created recognition:", recognition);

  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = "en-US";

  return recognition;
}