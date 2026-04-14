// Parse OpenAI response + call mock vendors (GenAIPro, RunPod, Runway, Suno, Creatomate).
// OpenAI response is on $input; pipeline fields come from the "Pipeline config" Set node (no credentials in Code sandbox).

async function httpJson(ctx, method, url, body) {
  const opt = {
    method,
    url,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined && body !== null) {
    opt.body = JSON.stringify(body);
  }
  return await ctx.helpers.httpRequest(opt);
}

const cfg = $('Pipeline config').first().json;
const topic = cfg.topic;
// Default: Docker bridge gateway to host (n8n in Docker cannot use 127.0.0.1 for mock on host).
const base = String(cfg.vendor_base_url || 'http://172.17.0.1:8080').replace(/\/+$/, '');
const maxScenes = Number(cfg.max_scenes) || 5;

const oa = $input.first().json;
if (oa.error) {
  throw new Error(`OpenAI error: ${JSON.stringify(oa.error)}`);
}

const jsonText = oa.choices[0].message.content;
const script = JSON.parse(jsonText);

const tts = await httpJson(this, 'POST', `${base}/v1/genaipro/tts`, {
  text: script.full_script,
  voice_id: 'documentary',
  format: 'mp3',
});
const voiceUrl = tts.audio_url;

const scenes = (script.scenes || []).slice(0, maxScenes);
const sceneResults = [];

for (const scene of scenes) {
  const rp = await httpJson(this, 'POST', `${base}/v1/runpod/comfy`, {
    input: { workflow: { prompt: scene.visual_prompt } },
  });
  const rpData = await httpJson(this, 'GET', `${base}/v1/runpod/comfy/${rp.id}`);
  const imageUrl = rpData.output.images[0].url;

  const rw = await httpJson(this, 'POST', `${base}/v1/runway/video`, {
    image_url: imageUrl,
    prompt: `cinematic motion, ${scene.visual_prompt}`,
    duration_sec: Math.min(30, Math.round(Number(scene.approx_duration_sec) || 5)),
  });
  const rwDone = await httpJson(this, 'GET', `${base}/v1/runway/video/${rw.task_id}`);

  sceneResults.push({
    scene_id: scene.scene_id,
    image_url: imageUrl,
    video_url: rwDone.video_url,
  });
}

const suno = await httpJson(this, 'POST', `${base}/v1/suno/generate`, {
  prompt: `dark documentary ambient music for: ${script.title}`,
  instrumental: true,
  n_variants: 4,
});

const cm = await httpJson(this, 'POST', `${base}/v1/creatomate/renders`, {
  template_id: 'pipeline_v1',
  modifications: {
    SceneVideos: sceneResults.map((s) => s.video_url),
    VoiceUrl: voiceUrl,
    MusicUrl: suno.tracks[0].audio_url,
  },
});
const final = await httpJson(this, 'GET', `${base}/v1/creatomate/renders/${cm.render_id}`);

return [
  {
    json: {
      title: script.title,
      topic,
      vendor_base_url: base,
      voice_url: voiceUrl,
      suno_tracks: suno.tracks,
      scene_results: sceneResults,
      final_mp4_url: final.url,
      creatomate_render_id: final.render_id,
      manifest: {
        script,
        scene_results: sceneResults,
        voice_url: voiceUrl,
        music_urls: suno.tracks.map((t) => t.audio_url),
        final_video: final.url,
      },
    },
  },
];
