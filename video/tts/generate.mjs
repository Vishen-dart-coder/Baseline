// Voiceover: Kokoro-82M, full-precision (fp32) ONNX, American female voice, fully offline.
// Setup (see ../README.md): `npm i kokoro-js@1.2.1` here, and place the model under
// ./models/onnx-community/Kokoro-82M-v1.0-ONNX/{config.json,tokenizer.json,tokenizer_config.json,onnx/model.onnx}
//   node generate.mjs [voice=af_heart]   -> ../vo/00.wav ... 08.wav
import { KokoroTTS } from "kokoro-js";
import { env } from "@huggingface/transformers";
import { readFileSync } from "node:fs";

env.localModelPath = new URL("./models/", import.meta.url).pathname;
env.allowRemoteModels = false;

const voice = process.argv[2] || "af_heart";
if (!voice.startsWith("af_")) throw new Error("Use an American female voice (af_*)");
const lines = JSON.parse(readFileSync(new URL("./script.json", import.meta.url)));
const tts = await KokoroTTS.from_pretrained("onnx-community/Kokoro-82M-v1.0-ONNX", { dtype: "fp32", device: "cpu" });
for (const [i, text] of lines.entries()) {
  const audio = await tts.generate(text, { voice, speed: 0.92 });
  await audio.save(new URL(`../vo/${String(i).padStart(2, "0")}.wav`, import.meta.url).pathname);
  console.log(i, (audio.audio.length / audio.sampling_rate).toFixed(2) + "s", text);
}
